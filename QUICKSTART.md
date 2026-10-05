# Instagram Mass Report Bot - Quick Start Guide

## ✅ Configuration Status
- ✓ BOT_TOKEN: Configured
- ✓ Admin ID: 6128148604
- ✓ Admin Username: @FLU_X0
- ✓ Force Join: Disabled
- ✓ Proxies: Disabled
- ✓ Referral System: Enabled

---

## 🚀 Start Bot Now

### Option 1: Docker (Recommended)

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```bash
deploy.bat
```

**Manual:**
```bash
docker compose up --build -d
docker compose logs -f bot
```

### Option 2: Local Python

```bash
pip install -r requirements.txt
python main.py
```

---

## 📋 What's Configured

### Bot Settings
- Name: Instagram Report Bot
- Author: FLU_X0
- Contact: @FLU_X0
- Admin: 6128148604 (you)

### Features Enabled
✅ Referral system (100 pts/ref, 300 pts/report)
✅ Bonus at 3 referrals (300 pts)
✅ Report reasons (12 options)
✅ Max reports: 200

### Features Disabled
❌ Force join channel/group
❌ Proxy rotation
(Can enable later in config.yml)

---

## 🎮 Start Using Bot

1. Open Telegram
2. Search for your bot (check @BotFather)
3. Click /start
4. Choose action from menu

---

## 📊 Available Commands

### User Commands
- ⚡ Quick Report - Bulk report multiple URLs
- 🎛 Custom Report - Report with custom settings
- 👥 My Accounts - Manage Instagram accounts
- 🌐 Proxies - View proxy status
- 👤 Profile - Your profile
- 🏆 Leaderboard - Top referrers
- 🎁 Refer & Earn - Get referral link
- 📊 My Stats - Your statistics
- 📜 History - Report history
- ℹ️ Info - About bot

### Admin Commands (You have access)
- 📢 Broadcast - Send message to all users
- 🎁 Gift Points - Give points to users
- 💎 Add Premium - Make user premium
- 🚫 Remove Premium - Remove premium
- 👥 View Users - See all users
- 📊 Full Stats - Global statistics
- 🔄 Refresh Proxies - Revalidate proxies

---

## 🔍 Monitor Bot

### View Logs
```bash
docker compose logs -f bot
```

### Check Status
```bash
docker compose ps
```

### Stop Bot
```bash
docker compose down
```

### Restart Bot
```bash
docker compose restart bot
```

---

## 📁 File Structure

```
instagram-mass-report-/
├── main.py                 ← Bot code
├── config.yml              ← Your config (READY)
├── .env                    ← Bot token (READY)
├── requirements.txt        ← Dependencies
├── Dockerfile              ← Container image
├── docker-compose.yml      ← Orchestration
├── deploy.sh              ← Linux/Mac deploy
├── deploy.bat             ← Windows deploy
├── cookies/               ← Instagram sessions
├── chrome_extensions/     ← Proxy extensions
├── data/                  ← Bot data
└── logs/                  ← Application logs
```

---

## ⚙️ Configuration Reference

### config.yml
- `bot.token`: BOT_TOKEN (from .env)
- `bot.admin_ids`: Your Telegram ID (6128148604)
- `force_join.enabled`: false (no channel join required)
- `proxies.enabled`: false (no proxies)
- `reporting.max_reports`: 200 (max per session)

### .env
- `BOT_TOKEN`: Your actual bot token
- `CONFIG_FILE`: config.yml

---

## 🔐 Security Notes

⚠️ **IMPORTANT:**
- ✓ .env is in .gitignore (won't be committed)
- ✓ config.yml should NOT be in git
- ✓ Bot token is safe in .env
- ✓ Admin ID (6128148604) is you
- ✓ Never share .env or config.yml

---

## 🆘 Troubleshooting

### Bot won't start
```bash
# Check logs
docker compose logs bot

# Check config
cat config.yml | head -10

# Verify token format
grep BOT_TOKEN .env
```

### Chrome/Selenium issues
```bash
# Inside container
docker compose exec bot chromium --version
docker compose exec bot python -c "from selenium import webdriver; print('OK')"
```

### Permission errors
```bash
chmod -R 755 cookies chrome_extensions data logs
```

### Docker not found
Install Docker: https://www.docker.com/products/docker-desktop

---

## 📞 Support

- Logs: `docker compose logs bot`
- Debug: Check config.yml values
- Issues: Check README.md

---

## 🎯 Next Steps

1. ✅ Configuration done
2. 🚀 Run deploy script
3. 💬 Start Telegram bot
4. 📊 Add Instagram account via bot
5. 📝 Create first report

---

**Status:** Ready to Deploy ✓
**Bot Token:** Configured ✓
**Admin ID:** 6128148604 ✓
**Config:** config.yml ✓

Launch now:
```bash
./deploy.sh  # Linux/Mac
# or
deploy.bat   # Windows
# or
docker compose up -d
```
