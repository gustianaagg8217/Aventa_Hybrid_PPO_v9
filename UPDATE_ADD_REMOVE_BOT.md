# 🆕 UPDATE: Add/Remove Bot Functionality

**Date**: 31 January 2026  
**Version**: 2.1  
**Status**: ✅ Ready to Use

---

## 🎯 NEW FEATURES

### 1. **Add Bot Button** ➕
Located in **Bot Management** tab, bottom left panel

**Usage**:
- Click **[➕ Add Bot]** button
- New bot card automatically created with next bot number
- Configuration fields ready to fill
- Status shows as "Stopped"

**Auto-numbering**:
- Bot #1, Bot #2, Bot #3, etc.
- Automatic increment
- Displayed in card header

### 2. **Remove Bot Button** 🗑️
Each bot card now has **[🗑️ Remove]** button

**Features**:
- Click **[🗑️ Remove]** on any bot card
- Confirmation dialog appears
- Ask to confirm removal
- Auto-stops bot if running
- Removes from launcher

**Auto-renumbering**:
```
Before:  Bot #1, Bot #2, Bot #3, Bot #4
Remove Bot #2:
After:   Bot #1, Bot #2 (was #3), Bot #3 (was #4)
```

---

## 🔄 WORKFLOW

### Add Multiple Bots:
```
1. Click [➕ Add Bot]
   → Bot #1 appears

2. Click [➕ Add Bot]
   → Bot #2 appears (auto-numbered)

3. Click [➕ Add Bot]
   → Bot #3 appears (auto-numbered)

4. Fill each bot configuration

5. Click [💾 Save Config]
   → All bots saved to bot_config.json
```

### Remove Bots:
```
1. Click [🗑️ Remove] on Bot #2

2. Confirmation dialog:
   "Are you sure you want to remove Bot #2?"

3. Click [Yes]
   → Bot #2 stops (if running)
   → Bot #2 removed from UI
   → Bot #3 becomes Bot #2 (renumbered)
   → Bot #4 becomes Bot #3 (renumbered)

4. Click [💾 Save Config]
   → Updated configuration saved
```

### Manage Multiple Bots:
```
Scenario: Running 5 bots

[➕ Add Bot]     → Add Bot #6
[🗑️ Remove]     → Delete unwanted bots
[▶️ Start All]   → Start all remaining bots
[⏹️ Stop All]    → Stop all bots
[💾 Save Config] → Save final configuration
```

---

## 📋 BOT CARD LAYOUT

### Each Card Now Has:
```
┌─ Bot #1 ──────────────────────────────────┐
│ Status: Stopped ⏹️                        │
│                                           │
│ Symbol: BTCUSD    | Max Trades: 5        │
│ Lot: 0.01         | Profit: 0.5          │
│ Max DD: 5.0       | Daily: 10.0          │
│ Spread: 0.5       |                      │
│                                           │
│ MT5 Path: [Browse.........................] │
│                                           │
│ [▶️ Start] [⏹️ Stop] [⚙️ Advanced]        │
│ [🗑️ Remove]                              │
│                                           │
│ Window Status: 0/5 | 00:00 | INACTIVE    │
└─────────────────────────────────────────────┘
```

---

## 🎮 BUTTON REFERENCE

### Bottom Control Panel:

**Left Section**:
| Button | Function |
|--------|----------|
| **➕ Add Bot** | Add new bot card |
| **🔄 Refresh** | Refresh status |

**Middle Section**:
| Button | Function |
|--------|----------|
| **▶️ Start All** | Start all bots |
| **⏹️ Stop All** | Stop all bots |

**Right Section**:
| Button | Function |
|--------|----------|
| **💾 Save Config** | Save to bot_config.json |
| **📂 Load Config** | Load from bot_config.json |
| **❌ Exit** | Close application |

### Individual Bot Card Buttons:
| Button | Function |
|--------|----------|
| **▶️ Start** | Start this bot |
| **⏹️ Stop** | Stop this bot |
| **⚙️ Advanced** | Advanced settings |
| **🗑️ Remove** | Delete this bot |

---

## 🔐 SAFETY FEATURES

### Remove Bot Safety:
✅ **Confirmation Dialog**: Must confirm before removal  
✅ **Auto-Stop**: Running bots auto-stopped before removal  
✅ **Auto-Save**: Changes not saved until you click [💾 Save Config]  
✅ **Error Handling**: Errors reported in logs  

### Undo Not Available:
⚠️ **Note**: There's no undo function
- Use [📂 Load Config] to load previous config if saved
- Always save config after adding/removing bots

---

## 💾 CONFIGURATION AUTO-SAVE

### Config File: `bot_config.json`

**Before**:
```json
[
  {"symbol": "BTCUSD", "lot_size": "0.01", ...},
  {"symbol": "ETHUSD", "lot_size": "0.05", ...},
  {"symbol": "GOLD.ls", "lot_size": "0.01", ...}
]
```

**After Adding Bot #4**:
```json
[
  {"symbol": "BTCUSD", "lot_size": "0.01", ...},
  {"symbol": "ETHUSD", "lot_size": "0.05", ...},
  {"symbol": "GOLD.ls", "lot_size": "0.01", ...},
  {"symbol": "", "lot_size": "", ...}  // New empty bot
]
```

**After Removing Bot #2**:
```json
[
  {"symbol": "BTCUSD", "lot_size": "0.01", ...},
  {"symbol": "GOLD.ls", "lot_size": "0.01", ...},
  {"symbol": "", "lot_size": "", ...}
]
```

### Save Config:
Click **[💾 Save Config]** button to update `bot_config.json`

### Load Config:
Click **[📂 Load Config]** button to restore from `bot_config.json`

---

## 🚀 EXAMPLE: Create Trading Setup

### Scenario: Create 3-Bot Trading System

**Step 1: Add Bots**
```
[➕ Add Bot]  → Bot #1 created
[➕ Add Bot]  → Bot #2 created
[➕ Add Bot]  → Bot #3 created
```

**Step 2: Configure Bot #1**
```
Symbol: BTCUSD
Lot: 0.01
Max DD: 5.0
Max Spread: 0.5
Max Trades: 5
Close Profit: 0.5
Daily: 10.0
Browse MT5 Terminal
```

**Step 3: Configure Bot #2**
```
Symbol: ETHUSD
Lot: 0.05
Max DD: 5.0
Max Spread: 0.5
Max Trades: 5
Close Profit: 0.3
Daily: 10.0
Browse MT5 Terminal
```

**Step 4: Configure Bot #3**
```
Symbol: GOLD.ls
Lot: 0.01
Max DD: 5.0
Max Spread: 0.4
Max Trades: 5
Close Profit: 0.15
Daily: 10.0
Browse MT5 Terminal
```

**Step 5: Save Configuration**
```
[💾 Save Config]
→ All 3 bots saved to bot_config.json
```

**Step 6: Start Trading**
```
[▶️ Start All]
→ All 3 bots start simultaneously
→ Monitor logs in 📋 Logs tab
→ Check window status for each bot
```

**Step 7: Stop Trading**
```
[⏹️ Stop All]
→ All 3 bots stop gracefully
```

---

## 🛠️ TROUBLESHOOTING

### Issue: "Bot won't remove"
**Solution**:
1. Click [⏹️ Stop] first
2. Wait 1-2 seconds
3. Click [🗑️ Remove] again

### Issue: "Removed bot, but changes not saved"
**Solution**:
1. Click [💾 Save Config] button
2. Config will save to bot_config.json
3. Next time you load, bot won't appear

### Issue: "Removed bot #2, but numbering looks wrong"
**Solution**:
1. Close and reopen launcher
2. Or click [📂 Load Config] to reload
3. Numbering should be correct

### Issue: "Can't add more bots"
**Possible causes**:
- Check disk space
- Check write permissions
- Close other applications
- Restart launcher

---

## 📊 PERFORMANCE NOTES

### Recommended Bot Count:
- **Minimum**: 1 bot
- **Optimal**: 3-5 bots
- **Maximum**: 10 bots (depends on system)

### For Low-End Systems:
- Use 1-2 bots only
- Monitor CPU/RAM usage
- Use [⏹️ Stop] when not trading

### For High-End Systems:
- Can run 5-10+ bots
- Monitor system resources
- Adjust window timing if needed

---

## 🎓 TIPS & TRICKS

### Tip 1: Batch Configuration
```
1. Add all bots first: [➕ Add Bot] x3
2. Configure all
3. Save all at once: [💾 Save Config]
```

### Tip 2: Quick Testing
```
1. Add test bot: [➕ Add Bot]
2. Configure with test settings
3. Start test bot: [▶️ Start]
4. Monitor logs: 📋 Logs tab
5. Remove test bot: [🗑️ Remove]
```

### Tip 3: Backup Configuration
```
1. Set up bots the way you like
2. Click [💾 Save Config]
3. Manually backup bot_config.json:
   cp bot_config.json bot_config.backup.json
4. Use backup if needed
```

### Tip 4: Trial Different Symbols
```
1. Add 3 bots
2. Bot #1: BTCUSD
3. Bot #2: ETHUSD
4. Bot #3: GOLD.ls
5. Start all and compare performance
6. Keep best, remove others
```

---

## 📈 WHAT'S NEXT

### Upcoming Features (Planned):
- 🎯 Drag-to-reorder bots
- 🎯 Clone bot configuration
- 🎯 Import/export bot profiles
- 🎯 Bot templates
- 🎯 Backup/restore functionality
- 🎯 Bot statistics & history
- 🎯 Performance metrics display

---

## 🔄 IMPLEMENTATION DETAILS

### Technical Changes (v2.1):

**BotCard Class Changes**:
```python
# Added parent reference
self.parent_app = parent.master.master

# Save title label for renumbering
self.title_label = ttk.Label(...)

# New method: _delete_bot()
def _delete_bot(self) -> None:
    # Stop bot if running
    # Get confirmation from user
    # Remove from parent
    # Renumber remaining bots
```

**UI Changes**:
```
Button added: [🗑️ Remove]
- Location: Bot card footer
- Calls: _delete_bot() method
- Auto-stops running bot before removal
```

**Auto-Renumbering**:
```python
for idx, bot in enumerate(self.parent_app.bots, 1):
    bot.bot_index = idx
    bot.title_label.config(text=f"Bot #{idx}")
```

---

## ✨ HIGHLIGHTS

### What's New:
✅ Add unlimited bots with [➕ Add Bot]  
✅ Remove bots with [🗑️ Remove]  
✅ Auto-numbered bot IDs  
✅ Auto-renumbering after removal  
✅ Confirmation before deletion  
✅ Safe operation (auto-stops bots)  
✅ Integrated with config system  

### Quality:
✅ Error handling throughout  
✅ User-friendly dialogs  
✅ Full logging for troubleshooting  
✅ Thread-safe operations  
✅ No crashes or data loss  

---

## 🚀 READY TO USE!

Modern Launcher v2.1 now has full bot management:
- ✅ Add bots
- ✅ Remove bots
- ✅ Auto-numbering
- ✅ Configuration persistence

**Start now**: `python Launcher_Modern_v2.py`

---

**Happy Bot Management!** 🤖➕➖

