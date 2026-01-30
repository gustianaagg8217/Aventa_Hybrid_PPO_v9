#!/usr/bin/env python3
# ppo_trainer.py
"""
Trainer PPO yang menyimpan model ke `PPO_agent.zip`.

Fitur utama:
- Env trading sederhana, aksi: 0=Hold, 1=Buy (Long), 2=Sell (Short)
- Observasi: N harga Close terakhir (default N=4)
- Reward: arah posisi * perubahan harga, plus biaya spread & komisi saat buka/flip
- Flag --reverse untuk membalik aksi Buy<->Sell selama training
- EvalCallback & CheckpointCallback
- Logger SB3 (stdout, csv, tensorboard)

Contoh pakai:
    pip install -r requirements_training.txt
    python ppo_trainer.py --csv /path/data.csv --timesteps 300000 --window 4 --reverse
"""

import argparse
import os
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from stable_baselines3.common.logger import configure


class SimpleTradingEnv(gym.Env):
    """
    Environment single-asset minimalis untuk PPO.

    - Observation: last N close prices (raw), shape=(N,)
    - Actions: 0=Hold, 1=Buy (long), 2=Sell (short)
    - Position: -1 short, 0 flat, 1 long (maks 1 unit)
    - Reward: position * price_change + biaya saat open/flip
    - reverse=True akan memetakan aksi 1<->2 saat step()
    """
    metadata = {"render_modes": []}

    def __init__(
        self,
        close_prices: np.ndarray,
        window: int = 4,
        spread: float = 0.0,
        commission: float = 0.0,
        reverse: bool = False,
    ):
        super().__init__()
        assert close_prices.ndim == 1 and len(close_prices) > window + 2, \
            "Need 1D close prices longer than window."
        self.close = close_prices.astype(np.float32)
        self.window = int(window)
        self.spread = float(spread)
        self.commission = float(commission)
        self.reverse = bool(reverse)

        self.action_space = spaces.Discrete(3)  # 0 hold, 1 buy, 2 sell
        self.observation_space = spaces.Box(
            low=0, high=np.finfo(np.float32).max, shape=(self.window,), dtype=np.float32
        )

        self.reset(seed=None, options=None)

    def _obs(self):
        return self.close[self.idx - self.window : self.idx].astype(np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.idx = self.window
        self.position = 0   # -1 short, 0 flat, 1 long
        self.entry_price = 0.0
        self.total_reward = 0.0
        return self._obs(), {}

    def step(self, action: int):
        # Reverse mapping jika diaktifkan: 1<->2; 0 tetap
        if self.reverse:
            action = 2 if action == 1 else (1 if action == 2 else 0)

        prev_price = float(self.close[self.idx - 1])
        self.idx += 1
        done = self.idx >= len(self.close)
        curr_price = float(self.close[self.idx - 1])
        price_change = curr_price - prev_price

        reward = 0.0

        # Trading dan biaya
        if action == 1:  # Buy/Long
            if self.position == 0:
                self.position = 1
                self.entry_price = curr_price + self.spread
                reward -= self.commission
            elif self.position == -1:
                # tutup short
                reward += (self.entry_price - (curr_price + self.spread))
                reward -= self.commission
                # buka long
                self.position = 1
                self.entry_price = curr_price + self.spread
                reward -= self.commission

        elif action == 2:  # Sell/Short
            if self.position == 0:
                self.position = -1
                self.entry_price = curr_price - self.spread
                reward -= self.commission
            elif self.position == 1:
                # tutup long
                reward += ((curr_price - self.spread) - self.entry_price)
                reward -= self.commission
                # buka short
                self.position = -1
                self.entry_price = curr_price - self.spread
                reward -= self.commission

        # Hold: tidak ada biaya tambahan

        # Shaped reward: unrealized PnL dari perubahan harga berjalan
        if self.position == 1:
            reward += price_change
        elif self.position == -1:
            reward -= price_change

        self.total_reward += reward

        obs = self._obs()
        info = {
            "idx": self.idx,
            "position": self.position,
            "entry_price": self.entry_price,
            "total_reward": self.total_reward,
        }
        return obs, float(reward), done, False, info

    def close_position(self):
        if self.position == 0:
            return 0.0
        curr_price = float(self.close[self.idx - 1])
        pnl = 0.0
        if self.position == 1:
            pnl = (curr_price - self.spread) - self.entry_price
        elif self.position == -1:
            pnl = self.entry_price - (curr_price + self.spread)
        self.position = 0
        self.entry_price = 0.0
        return pnl


def load_close_prices(csv_path: str, price_column: str = "Close") -> np.ndarray:
    """
    Memuat kolom harga Close dari CSV. Fleksibel terhadap beberapa variasi nama.
    Jika tidak ditemukan, fallback ke kolom numerik terakhir.
    """
    df = pd.read_csv(csv_path)
    # Kandidat umum termasuk header dataset yang sering dipakai
    candidates = [
        price_column,
        "Close", "close", "close_price", "ClosePrice", "CLOSE",
        "Adj Close", "adj_close", "AdjClose",
    ]
    col = None
    for c in candidates:
        if c in df.columns:
            col = c
            break
    if col is None:
        numeric_cols = [c for c in df.columns if np.issubdtype(df[c].dtype, np.number)]
        if not numeric_cols:
            raise ValueError(
                "Tidak menemukan kolom numerik untuk harga. Pastikan CSV memiliki kolom 'Close'."
            )
        col = numeric_cols[-1]
    series = df[col].dropna().values
    return series.astype(np.float32)


def main():
    parser = argparse.ArgumentParser(
        description="Train PPO dan ekspor PPO_agent.zip untuk live trading."
    )
    parser.add_argument("--csv", type=str, required=True,
                        help="Path ke CSV dengan minimal kolom 'Close'.")
    parser.add_argument("--window", type=int, default=4,
                        help="Panjang window observasi (default 4).")
    parser.add_argument("--spread", type=float, default=0.0,
                        help="Biaya spread saat membuka posisi.")
    parser.add_argument("--commission", type=float, default=0.0,
                        help="Komisi flat saat open/flip (per sisi).")
    parser.add_argument("--train_fraction", type=float, default=0.9,
                        help="Fraksi data untuk training (sisanya eval).")
    parser.add_argument("--timesteps", type=int, default=200_000,
                        help="Jumlah total training timesteps.")
    parser.add_argument("--policy", type=str, default="MlpPolicy",
                        help="Arsitektur policy untuk SB3 PPO.")
    parser.add_argument("--seed", type=int, default=42, help="Seed.")
    parser.add_argument("--log_dir", type=str, default="ppo_logs",
                        help="Folder log dan checkpoints.")
    parser.add_argument("--checkpoint_every", type=int, default=50_000,
                        help="Frekuensi checkpoint (tiap N step).")
    parser.add_argument("--learning_rate", type=float, default=3e-4,
                        help="Learning rate PPO.")
    parser.add_argument("--batch_size", type=int, default=2048,
                        help="Batch size PPO.")
    parser.add_argument("--ent_coef", type=float, default=0.0,
                        help="Entropy coef.")
    parser.add_argument("--gamma", type=float, default=0.99,
                        help="Discount factor.")
    parser.add_argument("--clip_range", type=float, default=0.2,
                        help="PPO clip range.")
    parser.add_argument("--n_steps", type=int, default=2048,
                        help="Rollout length.")
    parser.add_argument("--vf_coef", type=float, default=0.5,
                        help="Value function coef.")
    parser.add_argument("--gae_lambda", type=float, default=0.95,
                        help="GAE lambda.")
    parser.add_argument("--max_grad_norm", type=float, default=0.5,
                        help="Max grad norm.")
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Aktifkan reverse trading saat training (flip Buy<->Sell)."
    )
    parser.add_argument("--output", type=str, default="PPO_agent.zip",
                        help="Nama file output model PPO (default: PPO_agent.zip)")

    args = parser.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    new_logger = configure(args.log_dir, ["stdout", "csv", "tensorboard"])

    if args.reverse:
        print("[INFO] Reverse Trading ENABLED: environment flips actions 1<->2 during training.")

    close_prices = load_close_prices(args.csv)
    n_total = len(close_prices)
    n_train = int(n_total * args.train_fraction)
    train_prices = close_prices[:n_train]
    eval_prices = close_prices[n_train - max(args.window, 32) :]  # overlap agar window valid

    def make_train_env():
        return SimpleTradingEnv(
            train_prices,
            window=args.window,
            spread=args.spread,
            commission=args.commission,
            reverse=args.reverse,
        )

    def make_eval_env():
        return SimpleTradingEnv(
            eval_prices,
            window=args.window,
            spread=args.spread,
            commission=args.commission,
            reverse=args.reverse,
        )

    env = DummyVecEnv([make_train_env])
    eval_env = DummyVecEnv([make_eval_env])

    model = PPO(
        args.policy,
        env,
        verbose=1,
        seed=args.seed,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        ent_coef=args.ent_coef,
        gamma=args.gamma,
        clip_range=args.clip_range,
        n_steps=args.n_steps,
        vf_coef=args.vf_coef,
        gae_lambda=args.gae_lambda,
        max_grad_norm=args.max_grad_norm,
    )
    model.set_logger(new_logger)

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=os.path.join(args.log_dir, "best_model"),
        log_path=os.path.join(args.log_dir, "eval"),
        eval_freq=max(10_000, args.checkpoint_every // 2),
        deterministic=True,
        render=False,
    )
    checkpoint_callback = CheckpointCallback(
        save_freq=args.checkpoint_every,
        save_path=os.path.join(args.log_dir, "checkpoints"),
        name_prefix="ppo_checkpoint",
        save_replay_buffer=False,
        save_vecnormalize=False,
    )

    model.learn(
        total_timesteps=args.timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=True,
    )

    # Prompt user for output filename before saving
    output_name = input(f"Masukkan nama file output model PPO (.zip) [default: {args.output}]: ").strip()
    if not output_name:
        output_name = args.output
    if not output_name.lower().endswith(".zip"):
        output_name += ".zip"

    model.save(output_name)
    print(f"[DONE] Saved trained model to: {output_name}")
    print("Gunakan di live bot dengan arg: --ppo_model_path", output_name)


if __name__ == "__main__":
    main()
