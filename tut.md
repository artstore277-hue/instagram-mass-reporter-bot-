```markdown
# 📘 Instagram Report Bot — Tutorial

A complete step-by-step guide to install, configure, and run the **Instagram Report Bot**.

> ⚠️ **Disclaimer**
> This project is provided strictly for **educational and research purposes only**. Automating actions on Instagram violates their Terms of Service. Do not misuse this tool for harassment, spam, or unauthorized mass reporting. The author is **not responsible** for any misuse, account bans, or legal consequences. 
```
---

## 📋 Table of Contents

1. [Requirements](#-requirements)
2. [Installation](#-installation)
3. [Telegram Bot Setup](#-telegram-bot-setup)
4. [Configuration](#-configuration)
5. [Proxy Setup](#-proxy-setup)
6. [Running the Bot](#-running-the-bot)
7. [Docker Deployment](#-docker-deployment)
8. [Bot Usage Flow](#-bot-usage-flow)
9. [Menu Reference](#-menu-reference)
10. [Admin Panel](#-admin-panel)
11. [Referral System](#-referral-system)
12. [Project Structure](#-project-structure)
13. [Troubleshooting](#-troubleshooting)
14. [Ethical & Legal Notice](#-ethical--legal-notice)

---

## 🧰 Requirements
```
Before you begin, ensure you have:

- **Python 3.14 or higher**
- **Google Chrome** (latest stable)
- **Telegram account** (to create a bot)
- **Instagram accounts** (for reporting — you must own them)
- **SOCKS5 proxies** (strongly recommended)
- A **VPS or local machine** with internet access
```

# Check your Python version:

```bash
python --version
```

---

 ## ⚙️ Installation

# Step 1 — Clone or create the project

```bash
git clone <your-repo-url>
cd ig-report-bot
```

`Or manually create the folder ig-report-bot and place all project files inside.`

 # Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

# The requirements.txt should contain:

```text
python-telegram-bot>=21.0
selenium>=4.18.0
webdriver-manager>=4.0.0
python-dotenv>=1.0.0
pyyaml>=6.0.1
requests[socks]>=2.31.0
PySocks>=1.7.1
httpx[socks]>=0.27.0
httpx-socks[asyncio]>=0.9.0
```

# Step 3 — Install Chrome (Linux only)

`For Windows / macOS, download Chrome from google.com/chrome.`

`For Linux (Debian/Ubuntu):`

```bash
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt update
sudo apt install -y google-chrome-stable
```

`webdriver-manager will handle chromedriver automatically.`

---

# 🤖 Telegram Bot Setup

`Step 1 — Create your bot`

```swt

1. Open Telegram and search for @BotFather
2. Send /newbot and follow the prompts
3. Copy the HTTP API Token (looks like 123456789:ABCdef...)

Step 2 — Get your Telegram user ID

Search for @userinfobot on Telegram and start it. It will reply with your numeric user ID — you'll need this for the admin list.

Step 3 — Create the .env file

In the project root, create .env:

```

```text
BOT_TOKEN=your_telegram_bot_token_here
```

# Step 4 — Set admin IDs

` ~ Edit config.yml and put your Telegram user ID under bot.admin_ids:`

```yaml
bot:
  admin_ids:
    - 123456789
```

---

# 🔧 Configuration

` ~ Open config.yml and edit the following sections.`

# Bot Section

```yaml
bot:
  name: "Instagram Report"
  author: "Crypto Lord Himself 🧑‍💻"
  token: "${BOT_TOKEN}"
  contact: "your_admin_username"
  max_reports: 200
  admin_ids: [YOUR_TELEGRAM_ID]
```

` ~ Replace your_admin_username with your Telegram username (without the @). Users will contact you for premium.`

# Force Join Section

`~ Requires users to join your channel and group before using the bot.`

```yaml
force_join:
  enabled: true
  channel: "@your_channel"
  group: "@your_group"
  channel_url: "https://t.me/your_channel"
  group_url: "https://t.me/your_group"
```

` ~Important: Your bot must be an admin in both the channel and the group, otherwise membership checks will fail.`

# To disable force join:

```yaml
force_join:
  enabled: false
```

# Referral Section

```yaml
referral:
  enabled: true
  points_per_ref: 100
  points_per_report: 300
  bonus_at_count: 3
  bonus_points: 300
```

```Setting Meaning

points_per_ref Points per new user referred
points_per_report Points per successful report
bonus_at_count Number of refs needed for bonus
bonus_points Bonus points awarded
```
# Selenium Section

```yaml
selenium:
  headless: true
  window_size: "1920,1080"
  cookie_dir: "cookies"
  extension_dir: "chrome_extensions"
```

` ~Set headless: false if you want to see the browser during testing (recommended for first-time setup).`

# Reporting Section

```yaml
reporting:
  max_reports: 200
  request_delay_min: 1.5
  request_delay_max: 3.0
  retry_delay: 5
  max_retries: 3
```

` ~ Increasing request_delay_min and request_delay_max makes actions safer but slower.`

# 🌐 Proxy Setup

` Proxies are highly recommended to avoid Instagram rate limits and IP bans.`

# Step 1 — Get SOCKS5 proxies

`Buy from any residential proxy provider. Format example:`

```text
socks5://username:password@ip:port
```

# Step 2 — Add to proxies.txt

`Open proxies.txt and add one proxy per line:`

```text
socks5://user1:pass1@192.168.1.10:1080
socks5://user2:pass2@192.168.1.11:1080
192.168.1.12:1080
user3:pass3@192.168.1.13:1080
```

# Accepted formats:

`· socks5://user:pass@host:port
· socks5://host:port
· host:port
· user:pass@host:port
`

# Step 3 — Enable in config.yml

```yaml
proxies:
  enabled: true
  list_file: "proxies.txt"
  rotate: "least_used"
  max_fails: 3
  cooldown: 600
  auto_prune: true
  revalidate_every: 1800
```

  # Option Meaning

```tip
rotate least_used, round_robin, or random
max_fails Failures before cooldown
cooldown Cooldown seconds after max fails
auto_prune Remove dead proxies from pool
revalidate_every Seconds between automatic re-checks

How Proxy Validation Works

On startup and every revalidate_every seconds:

1. Loads all proxies from proxies.txt
2. Tests each with httpx (HTTP through SOCKS5)
3. Falls back to python_socks (raw socket)
4. Falls back to PySocks (socket check)
5. Marks proxies alive or dead
6. Dead proxies are permanently removed from the active pool

---
```
# ▶️ Running the Bot

` ~From the project folder:`

```bash
python main.py
```

# Expected output:

```
[boot] Instagram Report booting
revalidating all proxies...
✔ proxy socks5://1.2.3.4:1080
✔ proxy socks5://5.6.7.8:1080
proxy refresh done: 2 alive, 0 dead
```

# The bot is now online. Open Telegram, find your bot, and send /start.

---

# 🐳 Docker Deployment

` ~. Build and start`

```bash
docker compose up -d --build
```

`View logs`

```bash
docker compose logs -f ig-report-bot
```

`Restart`

```bash
docker compose restart ig-report-bot
```

`Stop everything`

```bash
docker compose down
```

`Stop and wipe volumes`

```bash
docker compose down -v
```

---

# 🕹️ Bot Usage Flow

`First-time setup`

```usage

1. Send /start to the bot
2. Bot checks if you've joined the force-join channel & group
3. If not, you'll see two buttons: 📢 Join Channel and 👥 Join Group
4. After joining, tap ✅ I Have Joined
5. Bot checks your premium status
6. If not premium, contact the admin

After premium activation

1. Send /start again → main menu appears
2. Tap 👥 My Accounts → ➕ Add Instagram
3. Send username:password (message is auto-deleted)
4. Bot logs in, saves cookies, and confirms
5. Repeat to add more Instagram accounts
6. Tap ↩️ Back to return to menu

# Reporting

Custom Report:

1. Tap 🎛 Custom Report
2. Choose target type: Profile, Post, Reel, Story, or Random Mix
3. Choose reason from the list (or Random Reason)
4. Send the URL to report
5. Send the amount (1 – 200)
6. Bot distributes reports across all your Instagram accounts
7. Watch the live progress bar with spinner
8. Final summary shows: success, failed, points earned

Quick Report:

1. Tap ⚡ Quick Report
2. Paste multiple URLs (one per line)
3. Send amount per URL
4. Bot processes queue automatically with random reasons/types

---
```

---

# 🛠️ Troubleshooting

```issue
Issue Solution
ModuleNotFoundError Run pip install -r requirements.txt again
Chrome crashes Increase shm_size in docker-compose.yml to 2gb
Chrome not found Install Chrome or set CHROME_BIN environment variable
Bot silent Verify BOT_TOKEN in .env
Login challenge Use residential SOCKS5 proxies, not datacenter
All proxies dead Check format in proxies.txt — one per line
Session expired Delete the matching file in cookies/
Reports failing constantly Slow down request_delay_min/max in config.yml
Force join fails Make sure bot is admin in channel and group
Cannot login Check Instagram 2FA is disabled or use app password

Debug mode

Set headless: false in config.yml to watch the browser. Then run:

```
```bash
python main.py
```

# You'll see Chrome open and interact live — useful for identifying where XPaths fail.

---

# ⚖️ Ethical & Legal Notice

` ~· This project is provided strictly for educational and research purposes.`
` ~· Automating reports on Instagram violates their Terms of Service.`
` ~· Misuse may result in:`
  `· Permanent account bans`
  `· IP blocks`
  `· Legal action from Meta or affected parties`
` ~· Do not use it to harass, stalk, spam, or target innocent users.`
` ~· Do not sell or distribute this tool as a service.`
` ~· The author assumes no liability for consequences arising from its use.`

# By running this software, you accept full responsibility for your actions.
---

#. Made by Crypto Lord Himself 🧑‍💻

