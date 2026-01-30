import subprocess

def ask(prompt, default=None, type_=str):
    val = input(f"{prompt} [{default}]: ").strip()
    if not val:
        return default
    try:
        return type_(val)
    except Exception:
        print(f"Invalid input, using default: {default}")
        return default

def main():
    print("=== PPO Trainer Launcher ===")
    csv = ask("Path ke CSV data", "data.csv", str)
    window = ask("Window observasi", 4, int)
    spread = ask("Spread", 0.0, float)
    commission = ask("Komisi", 0.0, float)
    train_fraction = ask("Fraksi data training", 0.9, float)
    timesteps = ask("Total timesteps", 200_000, int)
    policy = ask("Policy (MlpPolicy/CnnPolicy)", "MlpPolicy", str)
    seed = ask("Seed", 42, int)
    log_dir = ask("Folder log", "ppo_logs", str)
    checkpoint_every = ask("Checkpoint setiap N step", 50_000, int)
    learning_rate = ask("Learning rate", 3e-4, float)
    batch_size = ask("Batch size", 2048, int)
    ent_coef = ask("Entropy coef", 0.0, float)
    gamma = ask("Gamma", 0.99, float)
    clip_range = ask("Clip range", 0.2, float)
    n_steps = ask("Rollout length", 2048, int)
    vf_coef = ask("Value function coef", 0.5, float)
    gae_lambda = ask("GAE lambda", 0.95, float)
    max_grad_norm = ask("Max grad norm", 0.5, float)
    reverse = ask("Reverse trading? (y/n)", "n", str).lower() == "y"
    output = ask("Nama file output model", "PPO_agent.zip", str)

    cmd = [
        "python", "3_ppo_trainer_bisa_reverse.py",
        "--csv", csv,
        "--window", str(window),
        "--spread", str(spread),
        "--commission", str(commission),
        "--train_fraction", str(train_fraction),
        "--timesteps", str(timesteps),
        "--policy", policy,
        "--seed", str(seed),
        "--log_dir", log_dir,
        "--checkpoint_every", str(checkpoint_every),
        "--learning_rate", str(learning_rate),
        "--batch_size", str(batch_size),
        "--ent_coef", str(ent_coef),
        "--gamma", str(gamma),
        "--clip_range", str(clip_range),
        "--n_steps", str(n_steps),
        "--vf_coef", str(vf_coef),
        "--gae_lambda", str(gae_lambda),
        "--max_grad_norm", str(max_grad_norm),
        "--output", output,
    ]
    if reverse:
        cmd.append("--reverse")

    print("\nMenjalankan trainer dengan argumen:")
    print(" ".join(cmd))
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
