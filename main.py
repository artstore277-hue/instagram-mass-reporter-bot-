import os
import re
import time
import json
import random
import pickle
import shutil
import asyncio
import logging
import io
from datetime import datetime
from collections import defaultdict

import yaml
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BotCommand,
    ChatMember,
    LinkPreviewOptions,
)
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import httpx
from httpx_socks import AsyncProxyTransport
from python_socks.async_.asyncio import Proxy as SocksProxy
import socks
import socket

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

with open("config.yml", "r", encoding="utf-8-sig") as _f:
    _raw = _f.read()
for _k, _v in os.environ.items():
    _raw = _raw.replace(f"${{{_k}}}", _v)
CFG = yaml.safe_load(_raw)

TOKEN = CFG["bot"]["token"]
BRAND = CFG["bot"]["name"]
OWNER = CFG["bot"]["author"]
CONTACT = CFG["bot"].get("contact", "admin")
ADMIN_IDS = [int(x) for x in CFG["bot"].get("admin_ids", [])]

FORCE_JOIN_ENABLED = CFG.get("force_join", {}).get("enabled", False)
FORCE_CHANNEL = CFG["force_join"].get("channel", "")
FORCE_GROUP = CFG["force_join"].get("group", "")
FORCE_CHANNEL_URL = CFG["force_join"].get("channel_url", "")
FORCE_GROUP_URL = CFG["force_join"].get("group_url", "")

REFERRAL_ENABLED = CFG.get("referral", {}).get("enabled", True)
POINTS_PER_REF = CFG.get("referral", {}).get("points_per_ref", 100)
POINTS_PER_REPORT = CFG.get("referral", {}).get("points_per_report", 300)
BONUS_REF_COUNT = CFG.get("referral", {}).get("bonus_at_count", 3)
BONUS_REF_POINTS = CFG.get("referral", {}).get("bonus_points", 300)

HEADLESS = CFG["selenium"]["headless"]
WINDOW = CFG["selenium"]["window_size"]
IWAIT = CFG["selenium"]["implicit_wait"]
PLOAD = CFG["selenium"]["page_load_timeout"]
UA = CFG["selenium"]["user_agent"]
SOPTS = CFG["selenium"]["options"]

COOKIE_DIR = CFG["selenium"].get("cookie_dir", "cookies")
EXT_DIR = CFG["selenium"].get("extension_dir", "chrome_extensions")
os.makedirs(COOKIE_DIR, exist_ok=True)
os.makedirs(EXT_DIR, exist_ok=True)

IG_HOME = CFG["instagram"]["base_url"]
IG_LOGIN = CFG["instagram"]["login_url"]

D_MIN = CFG["reporting"]["request_delay_min"]
D_MAX = CFG["reporting"]["request_delay_max"]
RETRY = CFG["reporting"]["retry_delay"]
RETRIES = CFG["reporting"]["max_retries"]
REASONS = CFG["reporting"]["reasons"]
CAP = CFG["reporting"]["max_reports"]

PCFG = CFG.get("proxies", {})
PROXY_ENABLED = PCFG.get("enabled", False)
PROXY_LIST_FILE = PCFG.get("list_file", "proxies.txt")
PROXY_STATE_FILE = PCFG.get("state_file", "igx_proxy_state.json")
PROXY_CHECK_URL = PCFG.get("check_url", "https://api.ipify.org?format=json")
PROXY_CHECK_TIMEOUT = PCFG.get("check_timeout", 15)
PROXY_ROTATE = PCFG.get("rotate", "least_used")
PROXY_MAX_FAILS = PCFG.get("max_fails", 3)
PROXY_COOLDOWN = PCFG.get("cooldown", 600)
PROXY_AUTO_PRUNE = PCFG.get("auto_prune", True)
PROXY_REVALIDATE_EVERY = PCFG.get("revalidate_every", 1800)
PROXY_MAX_CHECK_CONCURRENT = PCFG.get("max_check_concurrent", 20)

ROT_MODE = CFG.get("rotation", {}).get("mode", "round_robin")
ACCOUNT_MAX_FAILS = CFG.get("rotation", {}).get("max_fails", 5)

TYPE_MAP = {
    "profile": ("👤", "Profile"),
    "post": ("🖼", "Post"),
    "reel": ("🎞", "Reel"),
    "story": ("📖", "Story"),
}

logging.basicConfig(
    level=getattr(logging, CFG["logging"]["level"], logging.INFO),
    format=CFG["logging"]["format"],
    datefmt=CFG["logging"]["date_format"],
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"{CFG['logging']['file_prefix']}_{datetime.now():%Y%m%d}.log"
        ),
    ],
)
log = logging.getLogger("igx")

DB_FILE = "igx_db.json"
USERS_FILE = "igx_users.json"
SESS_FILE = "igx_sess.json"
PRESET_FILE = "igx_presets.json"
ACCOUNT_FILE = "igx_account_state.json"
PROXY_STATE_FILE_FULL = "igx_proxy_state.json"

DB = {"stats": {}, "history": []}
USERS = {}
SESS = {}
PRESETS = defaultdict(dict)
ACCOUNT_STATE = {}
PROXY_STATE = {}


def safe_name(s):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", str(s))[:64]


def cookie_path(uid, u):
    return os.path.join(COOKIE_DIR, f"{safe_name(uid)}__{safe_name(u)}.pkl")


def persist_json(path, obj):
    try:
        with open(path, "w") as f:
            json.dump(obj, f, indent=2)
    except Exception as e:
        log.warning(f"persist {path} fail: {e}")


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def db_load():
    global DB, USERS, SESS, PRESETS, ACCOUNT_STATE, PROXY_STATE
    DB = load_json(DB_FILE, {"stats": {}, "history": []})
    USERS = load_json(USERS_FILE, {})
    SESS = load_json(SESS_FILE, {})
    PRESETS = defaultdict(dict, load_json(PRESET_FILE, {}))
    ACCOUNT_STATE = load_json(ACCOUNT_FILE, {})
    PROXY_STATE = load_json(PROXY_STATE_FILE_FULL, {})


def db_save():
    persist_json(DB_FILE, {"stats": DB["stats"], "history": DB["history"][-1000:]})
    persist_json(USERS_FILE, USERS)
    persist_json(SESS_FILE, SESS)
    persist_json(PRESET_FILE, dict(PRESETS))
    persist_json(ACCOUNT_FILE, ACCOUNT_STATE)
    persist_json(PROXY_STATE_FILE_FULL, PROXY_STATE)


def ensure_user(tg_user):
    uid = str(tg_user.id)
    if uid not in USERS:
        USERS[uid] = {
            "username": tg_user.username or "",
            "first_name": tg_user.first_name or "",
            "joined_at": time.time(),
            "premium": False,
            "premium_until": 0,
            "points": 0,
            "referred_by": None,
            "referrals": [],
            "verified_join": False,
            "total_reports": 0,
            "success_reports": 0,
            "ig_accounts": {},
            "last_seen": time.time(),
        }
    else:
        USERS[uid]["username"] = tg_user.username or USERS[uid].get("username", "")
        USERS[uid]["first_name"] = tg_user.first_name or USERS[uid].get("first_name", "")
        USERS[uid]["last_seen"] = time.time()
    return USERS[uid]


def is_admin(uid):
    return int(uid) in ADMIN_IDS


def is_premium(uid):
    u = USERS.get(str(uid))
    if not u or not u.get("premium"):
        return False
    if u.get("premium_until", 0) and u["premium_until"] < time.time():
        u["premium"] = False
        return False
    return True


def add_points(uid, amount, reason=""):
    u = USERS.get(str(uid))
    if not u:
        return
    u["points"] = u.get("points", 0) + amount
    log.info(f"user {uid} +{amount} pts ({reason}) → {u['points']}")


def bar(pct, w=24):
    f = int(pct * w / 100)
    return "▓" * f + "░" * (w - f)


SPIN = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]


def head(t):
    return (
        f"╭───────────────────────────╮\n"
        f"│  {t.center(23)}  │\n"
        f"╰───────────────────────────╯"
    )


class Proxy:
    def __init__(self, raw):
        self.raw = raw.strip()
        self.scheme = "socks5"
        self.host = ""
        self.port = ""
        self.user = ""
        self.password = ""
        self._parse()

    def _parse(self):
        s = self.raw
        if "://" in s:
            self.scheme, s = s.split("://", 1)
        self.scheme = self.scheme.lower()
        if self.scheme not in ("socks5", "socks5h", "socks4", "http", "https"):
            self.scheme = "socks5"
        if "@" in s:
            creds, host = s.rsplit("@", 1)
            if ":" in creds:
                self.user, self.password = creds.split(":", 1)
            else:
                self.user = creds
        else:
            host = s
        if ":" in host:
            self.host, self.port = host.rsplit(":", 1)
        else:
            self.host = host
        self.port = str(self.port).strip()

    def is_valid(self):
        return bool(self.host and self.port and self.port.isdigit())

    def key(self):
        return f"{self.scheme}://{self.host}:{self.port}"

    def requests_url(self):
        s = "socks5h" if self.scheme.startswith("socks") else "http"
        if self.user and self.password:
            return f"{s}://{self.user}:{self.password}@{self.host}:{self.port}"
        return f"{s}://{self.host}:{self.port}"

    def __repr__(self):
        return self.key()


async def verify_proxy_python_socks(proxy, timeout=10):
    try:
        socks_proxy = SocksProxy.from_url(proxy.requests_url())
        sock = await asyncio.wait_for(
            socks_proxy.connect(dest_host="api.ipify.org", dest_port=80),
            timeout=timeout,
        )
        sock.close()
        return True
    except Exception as e:
        log.debug(f"python_socks check failed for {proxy.key()}: {e}")
        return False


async def verify_proxy_httpx(proxy, timeout=PROXY_CHECK_TIMEOUT):
    try:
        transport = AsyncProxyTransport.from_url(proxy.requests_url())
        async with httpx.AsyncClient(transport=transport, timeout=timeout) as client:
            resp = await client.get(PROXY_CHECK_URL)
            if resp.status_code == 200:
                return True
    except Exception as e:
        log.debug(f"httpx check failed for {proxy.key()}: {e}")
    return False


def socket_check(proxy, timeout=10):
    try:
        s = socks.socksocket()
        s.set_proxy(
            socks.SOCKS5 if proxy.scheme.startswith("socks") else socks.HTTP,
            proxy.host,
            int(proxy.port),
            True,
            proxy.user or None,
            proxy.password or None,
        )
        s.settimeout(timeout)
        s.connect(("1.1.1.1", 80))
        s.close()
        return True
    except Exception as e:
        log.debug(f"socket check fail {proxy.key()}: {e}")
        return False


class ProxyManager:
    def __init__(self):
        self.active = []
        self.dead = []
        self.index = 0
        self.last_revalidate = 0
        self.lock = asyncio.Lock()

    def load_from_file(self):
        if not os.path.exists(PROXY_LIST_FILE):
            log.warning(f"proxy file missing: {PROXY_LIST_FILE}")
            return []
        out = []
        with open(PROXY_LIST_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                p = Proxy(line)
                if p.is_valid():
                    out.append(p)
                else:
                    log.warning(f"invalid proxy line: {line[:60]}")
        return out

    def prune_dead(self):
        pruned = [
            p
            for p in self.active
            if p.key() in PROXY_STATE and not PROXY_STATE[p.key()].get("dead", False)
        ]
        removed = len(self.active) - len(pruned)
        self.active = pruned
        return removed

    def persist_dead(self, proxy):
        key = proxy.key()
        PROXY_STATE.setdefault(key, {})
        PROXY_STATE[key]["dead"] = True
        PROXY_STATE[key]["died_at"] = time.time()
        persist_json(PROXY_STATE_FILE_FULL, PROXY_STATE)

    def persist_active(self, proxy, latency=None):
        key = proxy.key()
        s = PROXY_STATE.setdefault(key, {})
        s["dead"] = False
        s["fails"] = 0
        s["last_verified"] = time.time()
        if latency is not None:
            s["latency"] = latency
        s["banned_until"] = 0

    def persist_fail(self, proxy):
        key = proxy.key()
        s = PROXY_STATE.setdefault(key, {})
        s["fails"] = s.get("fails", 0) + 1
        if s["fails"] >= PROXY_MAX_FAILS:
            s["banned_until"] = time.time() + PROXY_COOLDOWN
            s["fails"] = 0

    async def refresh_all(self, force=False):
        async with self.lock:
            if not force and time.time() - self.last_revalidate < PROXY_REVALIDATE_EVERY:
                return
            log.info("revalidating all proxies...")
            raw = self.load_from_file()
            if not raw:
                self.active = []
                return
            sem = asyncio.Semaphore(PROXY_MAX_CHECK_CONCURRENT)

            async def check(p):
                async with sem:
                    if await verify_proxy_httpx(p):
                        return p, True, None
                    if await verify_proxy_python_socks(p):
                        return p, True, None
                    if socket_check(p):
                        return p, True, None
                    return p, False, None

            results = await asyncio.gather(*[check(p) for p in raw])
            alive, dead = [], []
            for proxy, ok, latency in results:
                if ok:
                    alive.append(proxy)
                    self.persist_active(proxy, latency)
                    log.info(f"✔ proxy {proxy.key()}")
                else:
                    dead.append(proxy)
                    self.persist_dead(proxy)
                    log.warning(f"✘ dead proxy {proxy.key()}")
            self.active = alive
            self.dead = dead
            self.last_revalidate = time.time()
            log.info(f"proxy refresh done: {len(alive)} alive, {len(dead)} dead")
            persist_json(PROXY_STATE_FILE_FULL, PROXY_STATE)

    def available(self):
        now = time.time()
        return [
            p
            for p in self.active
            if PROXY_STATE.get(p.key(), {}).get("banned_until", 0) <= now
        ]

    def get(self):
        if not self.active:
            return None
        avail = self.available()
        if not avail:
            return None
        if PROXY_ROTATE == "random":
            return random.choice(avail)
        if PROXY_ROTATE == "least_used":
            return min(
                avail,
                key=lambda p: PROXY_STATE.get(p.key(), {}).get("last_used", 0),
            )
        self.index = self.index % len(avail)
        chosen = avail[self.index]
        self.index += 1
        return chosen

    def mark_ok(self, proxy):
        if proxy is None:
            return
        s = PROXY_STATE.setdefault(proxy.key(), {})
        s["last_used"] = time.time()
        s["last_success"] = time.time()
        s["fails"] = 0

    def mark_fail(self, proxy):
        if proxy is None:
            return
        self.persist_fail(proxy)

    def stats(self):
        out = []
        for p in self.active:
            s = PROXY_STATE.get(p.key(), {})
            cd = max(int(s.get("banned_until", 0) - time.time()), 0)
            out.append(
                {
                    "key": p.key(),
                    "latency": s.get("latency", 0),
                    "fails": s.get("fails", 0),
                    "cooldown": cd,
                }
            )
        return out

    def __len__(self):
        return len(self.active)


PM = ProxyManager()


def build_chrome_extension(proxy):
    ext_id = f"igx_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    path = os.path.join(EXT_DIR, ext_id)
    os.makedirs(path, exist_ok=True)
    manifest = {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "IG Proxy Auth",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking",
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "22.0.0",
    }
    with open(os.path.join(path, "manifest.json"), "w") as f:
        json.dump(manifest, f)
    bg = (
        "var config = {\n"
        "  mode: 'fixed_servers',\n"
        "  rules: {\n"
        "    singleProxy: {\n"
        f"      scheme: '{proxy.scheme}',\n"
        f"      host: '{proxy.host}',\n"
        f"      port: parseInt({proxy.port})\n"
        "    },\n"
        "    bypassList: ['localhost']\n"
        "  }\n"
        "};\n"
        "chrome.proxy.settings.set({value: config, scope: 'regular'}, function() {});\n"
        "function callbackFn(details) {\n"
        "  return {\n"
        "    authCredentials: {\n"
        f"      username: '{proxy.user}',\n"
        f"      password: '{proxy.password}'\n"
        "    }\n"
        "  };\n"
        "}\n"
        "chrome.webRequest.onAuthRequired.addListener(\n"
        "  callbackFn,\n"
        "  {urls: ['<all_urls>']},\n"
        "  ['blocking']\n"
        ");\n"
    )
    with open(os.path.join(path, "background.js"), "w") as f:
        f.write(bg)
    return path


def cleanup_extension(path):
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def build_driver(proxy=None):
    o = Options()
    if HEADLESS:
        o.add_argument("--headless=new")
    o.add_argument(f"--window-size={WINDOW}")
    for opt in SOPTS:
        o.add_argument(opt)
    o.add_experimental_option("excludeSwitches", ["enable-automation"])
    o.add_experimental_option("useAutomationExtension", False)
    o.add_argument(f"user-agent={UA}")
    o.add_argument("--disable-gpu")
    o.add_argument("--log-level=3")
    ext_path = None
    if proxy and proxy.scheme.startswith("socks"):
        ext_path = build_chrome_extension(proxy)
        o.add_argument(f"--load-extension={ext_path}")
    elif proxy:
        auth = ""
        if proxy.user and proxy.password:
            auth = f"{proxy.user}:{proxy.password}@"
        o.add_argument(f"--proxy-server={proxy.scheme}://{auth}{proxy.host}:{proxy.port}")
        o.add_argument("--ignore-certificate-errors")
    d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)
    d.implicitly_wait(IWAIT)
    d.set_page_load_timeout(PLOAD)
    d._igx_ext = ext_path
    return d


def close_driver(d):
    try:
        d.quit()
    except Exception:
        pass
    ext = getattr(d, "_igx_ext", None)
    if ext:
        cleanup_extension(ext)


def pause(a=D_MIN, b=D_MAX):
    time.sleep(random.uniform(a, b))


def click(d, by, val, t=10, r=2):
    for i in range(r):
        try:
            el = WebDriverWait(d, t).until(EC.element_to_be_clickable((by, val)))
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(random.uniform(0.3, 0.8))
            try:
                el.click()
            except WebDriverException:
                d.execute_script("arguments[0].click();", el)
            return True
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            if i == r - 1:
                return False
            time.sleep(0.4)
    return False


def click_any(d, sels, t=8):
    for by, val in sels:
        try:
            els = WebDriverWait(d, t).until(
                EC.presence_of_all_elements_located((by, val))
            )
            for el in els:
                try:
                    if el.is_displayed():
                        d.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});", el
                        )
                        time.sleep(random.uniform(0.3, 0.7))
                        try:
                            el.click()
                        except WebDriverException:
                            d.execute_script("arguments[0].click();", el)
                        return True
                except Exception:
                    continue
        except (TimeoutException, NoSuchElementException):
            continue
    return False


def ck_save(d, uid, u):
    with open(cookie_path(uid, u), "wb") as f:
        pickle.dump(d.get_cookies(), f)


def ck_load(d, uid, u):
    try:
        with open(cookie_path(uid, u), "rb") as f:
            cs = pickle.load(f)
        d.get(IG_HOME)
        for c in cs:
            c.pop("sameSite", None)
            c.pop("expiry", None)
            try:
                d.add_cookie(c)
            except Exception:
                pass
        d.refresh()
        return True
    except FileNotFoundError:
        return False


def ck_alive(d):
    try:
        d.get(IG_HOME)
        pause(1.2, 2.0)
        u = d.current_url.lower()
        if "accounts/login" in u or "challenge" in u:
            return False
        src = d.page_source.lower()
        if "log in" in src and "sign up" in src and "explore" not in src:
            return False
        return True
    except Exception:
        return False


def do_login(d, u, p):
    for i in range(RETRIES):
        try:
            d.get(IG_LOGIN)
            pause(2.0, 3.2)
            w = WebDriverWait(d, 20)
            uf = w.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
            )
            uf.clear()
            uf.send_keys(u)
            pf = d.find_element(By.CSS_SELECTOR, "input[name='password']")
            pf.clear()
            pf.send_keys(p)
            pause(0.5, 1.1)
            d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            pause(4.0, 6.0)
            if "challenge" in d.current_url.lower():
                log.warning("login challenge")
                return False
            if "accounts/login" in d.current_url.lower():
                continue
            return True
        except Exception as e:
            log.warning(f"login {i+1}: {e}")
            time.sleep(RETRY)
    return False


def uname(url):
    try:
        for x in url.rstrip("/").split("/"):
            if x and x not in (
                "www.instagram.com",
                "instagram.com",
                "https:",
                "http:",
                "p",
                "reel",
                "reels",
                "stories",
                "tv",
            ):
                return x.split("?")[0][:40]
    except Exception:
        pass
    return "unknown"


def do_report(d, ttype, url, rkey):
    d.get(url)
    pause(2.0, 3.4)
    if "challenge" in d.current_url.lower():
        raise Exception("challenge")
    if "accounts/login" in d.current_url.lower():
        raise Exception("expired")
    if ttype in ("post", "reel"):
        msel = [
            (By.CSS_SELECTOR, "svg[aria-label='More options']"),
            (By.XPATH, "//*[local-name()='svg'][@aria-label='More options']"),
        ]
    elif ttype == "story":
        msel = [(By.CSS_SELECTOR, "svg[aria-label='More options']")]
    else:
        msel = [
            (By.CSS_SELECTOR, "svg[aria-label='Options']"),
            (By.CSS_SELECTOR, "svg[aria-label='More options']"),
        ]
    if not click_any(d, msel):
        raise Exception("menu_missing")
    pause()
    rsel = [
        (By.XPATH, "//*[text()='Report']"),
        (By.XPATH, "//*[contains(text(),'Report')]"),
    ]
    if not click_any(d, rsel):
        raise Exception("report_missing")
    pause()
    txt = REASONS.get(rkey, "Something else")
    asel = [
        (By.XPATH, f"//*[text()='{txt}']"),
        (By.XPATH, f"//*[contains(text(),'{txt}')]"),
    ]
    if not click_any(d, asel):
        raise Exception("reason_missing")
    pause()
    for by, val in [
        (By.XPATH, "//*[text()='Submit']"),
        (By.XPATH, "//*[text()='Next']"),
        (By.XPATH, "//*[text()='Done']"),
    ]:
        if click(d, by, val, t=5):
            break
    pause(0.7, 1.3)
    return True


async def check_force_join(bot, uid):
    if not FORCE_JOIN_ENABLED:
        return True
    try:
        if FORCE_CHANNEL:
            try:
                m = await bot.get_chat_member(FORCE_CHANNEL, uid)
                if m.status not in (
                    ChatMemberStatus.MEMBER,
                    ChatMemberStatus.ADMINISTRATOR,
                    ChatMemberStatus.OWNER,
                ):
                    return False
            except Exception as e:
                log.warning(f"channel check err: {e}")
                return False
        if FORCE_GROUP:
            try:
                m = await bot.get_chat_member(FORCE_GROUP, uid)
                if m.status not in (
                    ChatMemberStatus.MEMBER,
                    ChatMemberStatus.ADMINISTRATOR,
                    ChatMemberStatus.OWNER,
                ):
                    return False
            except Exception as e:
                log.warning(f"group check err: {e}")
                return False
        return True
    except Exception as e:
        log.warning(f"force join check fail: {e}")
        return False


def main_menu_kb(uid):
    admin_btn = []
    if is_admin(uid):
        admin_btn = [[KeyboardButton("🛡 Admin Panel")]]
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("⚡ Quick Report"), KeyboardButton("🎛 Custom Report")],
            [KeyboardButton("👥 My Accounts"), KeyboardButton("🌐 Proxies")],
            [KeyboardButton("👤 Profile"), KeyboardButton("🏆 Leaderboard")],
            [KeyboardButton("🎁 Refer & Earn"), KeyboardButton("📊 My Stats")],
            [KeyboardButton("📜 History"), KeyboardButton("ℹ️ Info")],
        ] + admin_btn,
        resize_keyboard=True,
        input_field_placeholder="Choose an action...",
    )


def type_menu_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("👤 Profile"), KeyboardButton("🖼 Post")],
            [KeyboardButton("🎞 Reel"), KeyboardButton("📖 Story")],
            [KeyboardButton("🎲 Random Mix")],
            [KeyboardButton("↩️ Back")],
        ],
        resize_keyboard=True,
    )


def reason_menu_kb():
    items = list(REASONS.items())
    rows = []
    for i in range(0, len(items), 2):
        row = [KeyboardButton(f"{i+1}. {items[i][1]}")]
        if i + 1 < len(items):
            row.append(KeyboardButton(f"{i+2}. {items[i+1][1]}"))
        rows.append(row)
    rows.append([KeyboardButton("🎲 Random Reason")])
    rows.append([KeyboardButton("↩️ Back")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def cancel_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("↩️ Back")]],
        resize_keyboard=True,
    )


def force_join_inline():
    rows = []
    if FORCE_CHANNEL_URL:
        rows.append([InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL_URL)])
    if FORCE_GROUP_URL:
        rows.append([InlineKeyboardButton("👥 Join Group", url=FORCE_GROUP_URL)])
    rows.append([InlineKeyboardButton("✅ I Have Joined", callback_data="check_join")])
    return InlineKeyboardMarkup(rows)


def premium_inline():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("💎 Contact Admin", url=f"https://t.me/{CONTACT}")]]
    )


def profile_caption(uid):
    u = USERS.get(str(uid), {})
    refs = u.get("referrals", [])
    return (
        f"<pre>{head('MY PROFILE')}</pre>\n"
        f"<b>Name</b> · {u.get('first_name','')}\n"
        f"<b>Username</b> · @{u.get('username','—')}\n"
        f"<b>Premium</b> · {'💎 Yes' if is_premium(uid) else '✖ No'}\n"
        f"<b>Points</b> · {u.get('points',0):,}\n"
        f"<b>Referrals</b> · {len(refs)}\n"
        f"<b>Total Reports</b> · {u.get('total_reports',0)}\n"
        f"<b>Successful</b> · ✅ {u.get('success_reports',0)}\n\n"
        f"<i>{OWNER}</i>"
    )


def leaderboard_caption():
    top = sorted(
        [(uid, u) for uid, u in USERS.items() if u.get("referrals")],
        key=lambda x: len(x[1].get("referrals", [])),
        reverse=True,
    )[:5]
    if not top:
        body = "<i>No referrals yet.</i>"
    else:
        lines = []
        medals = ["🥇", "🥈", "🥉", "🏅", "🎖"]
        for i, (uid, u) in enumerate(top):
            lines.append(
                f"{medals[i]} <b>{u.get('first_name','?')[:18]}</b> · "
                f"{len(u.get('referrals',[]))} refs · {u.get('points',0):,} pts"
            )
        body = "\n".join(lines)
    return (
        f"<pre>{head('LEADERBOARD TOP 5')}</pre>\n"
        f"{body}\n\n"
        f"<i>{OWNER}</i>"
    )


def refer_caption(uid, bot_username):
    u = USERS.get(str(uid), {})
    refs = u.get("referrals", [])
    link = f"https://t.me/{bot_username}?start=ref_{uid}"
    return (
        f"<pre>{head('REFER & EARN')}</pre>\n"
        f"<b>Your Link</b>\n<code>{link}</code>\n\n"
        f"<b>Commission</b>\n"
        f"• {POINTS_PER_REF} pts per new user\n"
        f"• {BONUS_REF_POINTS} bonus at {BONUS_REF_COUNT} referrals\n"
        f"• {POINTS_PER_REPORT} pts per successful report\n\n"
        f"<b>Total Referrals</b> · {len(refs)}\n"
        f"<b>Points Earned</b> · {u.get('points',0):,}\n\n"
        f"<i>Share to earn more · {OWNER}</i>"
    )


def info_caption():
    return (
        f"<pre>{head('ABOUT')}</pre>\n"
        f"<b>{BRAND}</b>\n"
        f"Instagram automation console.\n\n"
        f"⚠️ <b>Educational use only.</b>\n"
        f"Do not misuse for harassment or mass reporting.\n\n"
        f"<b>Points System</b>\n"
        f"• {POINTS_PER_REF} per referral\n"
        f"• {BONUS_REF_POINTS} bonus at {BONUS_REF_COUNT} refs\n"
        f"• {POINTS_PER_REPORT} per success\n\n"
        f"<b>Owner</b> · {OWNER}"
    )


def admin_caption():
    total_users = len(USERS)
    premium_users = sum(1 for u in USERS.values() if u.get("premium"))
    logged_users = sum(1 for u in USERS.values() if u.get("ig_accounts"))
    total_success = sum(u.get("success_reports", 0) for u in USERS.values())
    return (
        f"<pre>{head('ADMIN PANEL')}</pre>\n"
        f"<b>Total Users</b> · {total_users:,}\n"
        f"<b>Premium</b> · {premium_users:,}\n"
        f"<b>Logged IG</b> · {logged_users:,}\n"
        f"<b>Success Reports</b> · {total_success:,}\n"
        f"<b>Proxies</b> · {len(PM)} active\n\n"
        f"<i>Choose an admin action below</i>"
    )


def admin_menu_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📢 Broadcast"), KeyboardButton("🎁 Gift Points")],
            [KeyboardButton("💎 Add Premium"), KeyboardButton("🚫 Remove Premium")],
            [KeyboardButton("👥 View Users"), KeyboardButton("📊 Full Stats")],
            [KeyboardButton("🔄 Refresh Proxies")],
            [KeyboardButton("↩️ Back")],
        ],
        resize_keyboard=True,
    )


def gift_points_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("👤 To One User"), KeyboardButton("🌍 To Everyone")],
            [KeyboardButton("↩️ Back")],
        ],
        resize_keyboard=True,
    )


async def send_main(update, ctx, caption=None):
    uid = update.effective_user.id
    text = caption or f"<pre>{head('MAIN MENU')}</pre>\nChoose your action below."
    kb = main_menu_kb(uid)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_caption(
                caption=text, parse_mode=ParseMode.HTML
            )
            return
        except Exception:
            pass
    if update.message:
        if os.path.exists("image.jpg"):
            await update.message.reply_photo(
                photo="image.jpg",
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        else:
            await update.message.reply_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )
    else:
        await update.effective_chat.send_message(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )


async def edit_or_reply(update, ctx, text, kb=None):
    if update.callback_query:
        try:
            await update.callback_query.edit_message_caption(
                caption=text, parse_mode=ParseMode.HTML, reply_markup=kb
            )
            return
        except Exception:
            try:
                await update.callback_query.edit_message_text(
                    text=text, parse_mode=ParseMode.HTML, reply_markup=kb
                )
                return
            except Exception:
                pass
    if update.message:
        if os.path.exists("image.jpg"):
            await update.message.reply_photo(
                photo="image.jpg",
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        else:
            await update.message.reply_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )


async def guard(update, ctx):
    uid = update.effective_user.id
    ensure_user(update.effective_user)
    if is_admin(uid):
        return True
    if FORCE_JOIN_ENABLED:
        ok = await check_force_join(ctx.bot, uid)
        USERS[str(uid)]["verified_join"] = ok
        if not ok:
            await edit_or_reply(
                update,
                ctx,
                f"<pre>{head('JOIN REQUIRED')}</pre>\n"
                f"Please join our channel and group to continue.",
                force_join_inline(),
            )
            return False
    if not is_premium(uid):
        await edit_or_reply(
            update,
            ctx,
            f"<pre>{head('PREMIUM ONLY')}</pre>\n"
            f"This bot is for <b>premium users</b>.\n"
            f"Contact admin to activate your access.",
            premium_inline(),
        )
        return False
    return True


async def cmd_start(update, ctx):
    tg_user = update.effective_user
    uid = tg_user.id
    ensure_user(tg_user)

    args = ctx.args
    if args and args[0].startswith("ref_"):
        ref_id = args[0][4:]
        if ref_id.isdigit() and ref_id != str(uid):
            me = USERS[str(uid)]
            if not me.get("referred_by"):
                ref_user = USERS.get(ref_id)
                if ref_user is not None:
                    me["referred_by"] = ref_id
                    ref_user.setdefault("referrals", []).append(str(uid))
                    add_points(ref_id, POINTS_PER_REF, f"referral {uid}")
                    if len(ref_user["referrals"]) == BONUS_REF_COUNT:
                        add_points(ref_id, BONUS_REF_POINTS, "bonus 3ref")
                    db_save()
                    try:
                        await ctx.bot.send_message(
                            int(ref_id),
                            f"🎉 New referral joined!\n"
                            f"<b>+{POINTS_PER_REF} points</b> credited.",
                            parse_mode=ParseMode.HTML,
                        )
                    except Exception:
                        pass

    if not await guard(update, ctx):
        return

    await send_main(update, ctx)


async def on_callback(update, ctx):
    q = update.callback_query
    try:
        await q.answer()
    except Exception:
        pass
    uid = update.effective_user.id

    if q.data == "check_join":
        ensure_user(update.effective_user)
        ok = await check_force_join(ctx.bot, uid)
        USERS[str(uid)]["verified_join"] = ok
        db_save()
        if ok:
            if not is_premium(uid) and not is_admin(uid):
                await q.edit_message_caption(
                    caption=f"<pre>{head('PREMIUM ONLY')}</pre>\n"
                    f"Contact admin to activate access.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=premium_inline(),
                )
                return
            await q.edit_message_caption(
                caption=f"<pre>{head('VERIFIED')}</pre>\n✅ You are verified.",
                parse_mode=ParseMode.HTML,
            )
            await ctx.bot.send_message(
                uid,
                f"<pre>{head('MAIN MENU')}</pre>\nChoose your action:",
                parse_mode=ParseMode.HTML,
                reply_markup=main_menu_kb(uid),
            )
        else:
            await q.edit_message_caption(
                caption="❌ You haven't joined yet. Please join and try again.",
                parse_mode=ParseMode.HTML,
                reply_markup=force_join_inline(),
            )


async def handle_text(update, ctx):
    tg_user = update.effective_user
    uid = tg_user.id
    text = (update.message.text or "").strip()
    ensure_user(tg_user)
    step = ctx.user_data.get("step")

    if text == "/cancel" or text == "↩️ Back":
        ctx.user_data.clear()
        if not await guard(update, ctx):
            return
        if is_admin(uid) and step in (
            "admin_broadcast",
            "admin_gift_one_id",
            "admin_gift_one_amt",
            "admin_gift_all",
            "admin_addprem",
            "admin_delprem",
        ):
            await edit_or_reply(
                update,
                ctx,
                admin_caption(),
                admin_menu_kb(),
            )
            return
        await send_main(update, ctx)
        return

    if text == "/start":
        await cmd_start(update, ctx)
        return

    if not await guard(update, ctx):
        return

    if text == "⚡ Quick Report":
        ctx.user_data["step"] = "quick_add"
        ctx.user_data["quick_queue"] = []
        await edit_or_reply(
            update,
            ctx,
            f"<pre>{head('QUICK REPORT')}</pre>\n"
            f"Send one URL per line. Type will randomize.\n"
            f"Tap <b>↩️ Back</b> to cancel.",
            cancel_kb(),
        )
        return

    if text == "🎛 Custom Report":
        ctx.user_data["step"] = "custom_type"
        await edit_or_reply(
            update,
            ctx,
            f"<pre>{head('CUSTOM REPORT')}</pre>\nSelect target type:",
            type_menu_kb(),
        )
        return

    if text == "👥 My Accounts":
        ig = USERS[str(uid)].get("ig_accounts", {})
        if not ig:
            lines = [f"<pre>{head('MY ACCOUNTS')}</pre>", "<i>No accounts yet.</i>"]
        else:
            lines = [f"<pre>{head('MY ACCOUNTS')}</pre>"]
            for u in ig.keys():
                lines.append(f"◈ <code>{u[:3]}***{u[-3:]}</code>")
        rows = [
            [KeyboardButton("➕ Add Instagram"), KeyboardButton("🗑 Remove One")],
            [KeyboardButton("🚪 Logout All"), KeyboardButton("↩️ Back")],
        ]
        await edit_or_reply(
            update,
            ctx,
            "\n".join(lines),
            ReplyKeyboardMarkup(rows, resize_keyboard=True),
        )
        return

    if text == "➕ Add Instagram":
        ctx.user_data["step"] = "add_ig"
        await edit_or_reply(
            update,
            ctx,
            f"<pre>{head('ADD ACCOUNT')}</pre>\n"
            f"Send <code>username:password</code>\n"
            f"<i>Message auto-deleted.</i>",
            cancel_kb(),
        )
        return

    if text == "🗑 Remove One":
        ig = USERS[str(uid)].get("ig_accounts", {})
        if not ig:
            await edit_or_reply(update, ctx, "No accounts to remove.", main_menu_kb(uid))
            return
        rows = [[KeyboardButton(f"🗑 {u[:3]}***{u[-3:]}")] for u in ig.keys()]
        rows.append([KeyboardButton("↩️ Back")])
        ctx.user_data["step"] = "remove_ig"
        await edit_or_reply(
            update,
            ctx,
            "Select account to remove:",
            ReplyKeyboardMarkup(rows, resize_keyboard=True),
        )
        return

    if text.startswith("🗑 ") and step == "remove_ig":
        target = text.replace("🗑 ", "").strip()
        ig = USERS[str(uid)].get("ig_accounts", {})
        for u in list(ig.keys()):
            if f"{u[:3]}***{u[-3:]}" == target:
                ig.pop(u, None)
                try:
                    os.remove(cookie_path(uid, u))
                except Exception:
                    pass
                break
        db_save()
        ctx.user_data.clear()
        await edit_or_reply(update, ctx, "✔ Account removed.", main_menu_kb(uid))
        return

    if text == "🚪 Logout All":
        ig = USERS[str(uid)].get("ig_accounts", {})
        for u in list(ig.keys()):
            try:
                os.remove(cookie_path(uid, u))
            except Exception:
                pass
        USERS[str(uid)]["ig_accounts"] = {}
        db_save()
        await edit_or_reply(update, ctx, "✔ Logged out all accounts.", main_menu_kb(uid))
        return

    if text == "🌐 Proxies":
        stats = PM.stats()
        if not stats:
            lines = [f"<pre>{head('PROXIES')}</pre>", "No active proxies."]
        else:
            lines = [f"<pre>{head('PROXIES')}</pre>"]
            for p in stats[:8]:
                cd = f" ⏸{p['cooldown']}s" if p["cooldown"] else ""
                lines.append(f"◈ <code>{p['key'][:30]}</code>\n   ⚡{p['latency']}s ✘{p['fails']}{cd}")
        await edit_or_reply(
            update, ctx, "\n".join(lines), main_menu_kb(uid)
        )
        return

    if text == "👤 Profile":
        await edit_or_reply(
            update, ctx, profile_caption(uid), main_menu_kb(uid)
        )
        return

    if text == "🏆 Leaderboard":
        await edit_or_reply(
            update, ctx, leaderboard_caption(), main_menu_kb(uid)
        )
        return

    if text == "🎁 Refer & Earn":
        me = await ctx.bot.get_me()
        await edit_or_reply(
            update,
            ctx,
            refer_caption(uid, me.username),
            main_menu_kb(uid),
        )
        return

    if text == "📊 My Stats":
        u = USERS[str(uid)]
        refs = len(u.get("referrals", []))
        await edit_or_reply(
            update,
            ctx,
            f"<pre>{head('MY STATS')}</pre>\n"
            f"<b>Points</b> · {u.get('points',0):,}\n"
            f"<b>Referrals</b> · {refs}\n"
            f"<b>Reports</b> · {u.get('total_reports',0)}\n"
            f"<b>Success</b> · ✅ {u.get('success_reports',0)}\n"
            f"<b>Accounts</b> · {len(u.get('ig_accounts', {}))}",
            main_menu_kb(uid),
        )
        return

    if text == "📜 History":
        hist = [h for h in DB["history"] if h.get("uid") == uid][-8:]
        if not hist:
            await edit_or_reply(update, ctx, "No history yet.", main_menu_kb(uid))
            return
        lines = [f"<pre>{head('RECENT REPORTS')}</pre>"]
        for h in reversed(hist):
            lines.append(
                f"• <code>{h.get('target','?')[:22]}</code>\n"
                f"   ×{h.get('amount',0)} · ✔{h.get('success',0)} ✘{h.get('failed',0)}"
            )
        await edit_or_reply(update, ctx, "\n".join(lines), main_menu_kb(uid))
        return

    if text == "ℹ️ Info":
        await edit_or_reply(update, ctx, info_caption(), main_menu_kb(uid))
        return

    if text == "🛡 Admin Panel" and is_admin(uid):
        await edit_or_reply(
            update, ctx, admin_caption(), admin_menu_kb()
        )
        return

    if is_admin(uid):
        if text == "📢 Broadcast":
            ctx.user_data["step"] = "admin_broadcast"
            await edit_or_reply(
                update,
                ctx,
                f"<pre>{head('BROADCAST')}</pre>\nSend the message to broadcast:",
                cancel_kb(),
            )
            return
        if text == "🎁 Gift Points":
            ctx.user_data["step"] = "admin_gift_menu"
            await edit_or_reply(
                update, ctx, "Choose gift mode:", gift_points_kb()
            )
            return
        if text == "👤 To One User":
            ctx.user_data["step"] = "admin_gift_one_id"
            await edit_or_reply(
                update, ctx, "Send the user ID:", cancel_kb()
            )
            return
        if text == "🌍 To Everyone":
            ctx.user_data["step"] = "admin_gift_all"
            await edit_or_reply(
                update, ctx, "Send amount for everyone:", cancel_kb()
            )
            return
        if text == "💎 Add Premium":
            ctx.user_data["step"] = "admin_addprem"
            await edit_or_reply(
                update, ctx, "Send user ID to add premium:", cancel_kb()
            )
            return
        if text == "🚫 Remove Premium":
            ctx.user_data["step"] = "admin_delprem"
            await edit_or_reply(
                update, ctx, "Send user ID to remove premium:", cancel_kb()
            )
            return
        if text == "👥 View Users":
            lines = [f"<pre>{head('USERS')}</pre>"]
            sorted_users = sorted(USERS.items(), key=lambda x: x[1].get("joined_at", 0), reverse=True)[:20]
            for uid_, u in sorted_users:
                pm = "💎" if u.get("premium") else "•"
                ig = len(u.get("ig_accounts", {}))
                lines.append(
                    f"{pm} <code>{uid_}</code> {u.get('first_name','?')[:14]}\n"
                    f"   refs:{len(u.get('referrals',[]))} ig:{ig} pts:{u.get('points',0)}"
                )
            await edit_or_reply(update, ctx, "\n".join(lines), admin_menu_kb())
            return
        if text == "📊 Full Stats":
            total_users = len(USERS)
            premium_users = sum(1 for u in USERS.values() if u.get("premium"))
            logged = sum(1 for u in USERS.values() if u.get("ig_accounts"))
            total_success = sum(u.get("success_reports", 0) for u in USERS.values())
            total_refs = sum(len(u.get("referrals", [])) for u in USERS.values())
            total_pts = sum(u.get("points", 0) for u in USERS.values())
            await edit_or_reply(
                update,
                ctx,
                f"<pre>{head('FULL STATS')}</pre>\n"
                f"Users · {total_users}\n"
                f"Premium · {premium_users}\n"
                f"Logged IG · {logged}\n"
                f"Success Reports · {total_success}\n"
                f"Total Refs · {total_refs}\n"
                f"Points Circulating · {total_pts:,}",
                admin_menu_kb(),
            )
            return
        if text == "🔄 Refresh Proxies":
            await edit_or_reply(update, ctx, "⏳ Refreshing proxies...")
            await PM.refresh_all(force=True)
            await edit_or_reply(
                update,
                ctx,
                f"✔ Done. {len(PM)} proxies active.",
                admin_menu_kb(),
            )
            return

    if step == "admin_broadcast":
        success = 0
        for uid_ in list(USERS.keys()):
            try:
                await ctx.bot.send_message(int(uid_), text, parse_mode=ParseMode.HTML)
                success += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
        ctx.user_data.clear()
        await edit_or_reply(
            update,
            ctx,
            f"✔ Broadcast sent to {success} users.",
            admin_menu_kb(),
        )
        return

    if step == "admin_gift_one_id":
        if not text.isdigit():
            await edit_or_reply(update, ctx, "Send a valid ID.")
            return
        ctx.user_data["gift_target"] = text
        ctx.user_data["step"] = "admin_gift_one_amt"
        await edit_or_reply(update, ctx, "Send points amount:", cancel_kb())
        return

    if step == "admin_gift_one_amt":
        if not text.isdigit():
            await edit_or_reply(update, ctx, "Send a number.")
            return
        amt = int(text)
        target = ctx.user_data.get("gift_target")
        add_points(target, amt, f"admin gift by {uid}")
        db_save()
        try:
            await ctx.bot.send_message(
                int(target),
                f"🎁 You received <b>{amt:,} points</b> from admin.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        ctx.user_data.clear()
        await edit_or_reply(
            update,
            ctx,
            f"✔ Gave {amt:,} pts to <code>{target}</code>.",
            admin_menu_kb(),
        )
        return

    if step == "admin_gift_all":
        if not text.isdigit():
            await edit_or_reply(update, ctx, "Send a number.")
            return
        amt = int(text)
        for uid_ in USERS.keys():
            add_points(uid_, amt, f"admin gift-all")
        db_save()
        ctx.user_data.clear()
        await edit_or_reply(
            update,
            ctx,
            f"✔ Gave {amt:,} pts to everyone ({len(USERS)} users).",
            admin_menu_kb(),
        )
        return

    if step == "admin_addprem":
        if not text.isdigit():
            await edit_or_reply(update, ctx, "Send a valid user ID.")
            return
        if text not in USERS:
            await edit_or_reply(update, ctx, "User not found.")
            return
        USERS[text]["premium"] = True
        USERS[text]["premium_until"] = 0
        db_save()
        try:
            await ctx.bot.send_message(
                int(text), "💎 Your premium has been activated!"
            )
        except Exception:
            pass
        ctx.user_data.clear()
        await edit_or_reply(
            update, ctx, f"✔ Premium added to <code>{text}</code>.", admin_menu_kb()
        )
        return

    if step == "admin_delprem":
        if not text.isdigit():
            await edit_or_reply(update, ctx, "Send a valid user ID.")
            return
        if text not in USERS:
            await edit_or_reply(update, ctx, "User not found.")
            return
        USERS[text]["premium"] = False
        db_save()
        ctx.user_data.clear()
        await edit_or_reply(
            update, ctx, f"✔ Premium removed from <code>{text}</code>.", admin_menu_kb()
        )
        return

    if step == "add_ig":
        try:
            await update.message.delete()
        except Exception:
            pass
        if ":" not in text:
            await update.message.reply_text(
                "❌ Format: <code>username:password</code>", parse_mode=ParseMode.HTML
            )
            return
        u, p = text.split(":", 1)
        u, p = u.strip(), p.strip()
        if not u or not p:
            await update.message.reply_text("Empty credentials.")
            return
        ig = USERS[str(uid)].setdefault("ig_accounts", {})
        if u in ig:
            await update.message.reply_text("⚠ Account already added.")
            return
        m = await update.message.reply_text("⏳ Verifying proxies...")
        if PROXY_ENABLED:
            await PM.refresh_all(force=False)
            if not PM.available():
                await m.edit_text("❌ No working proxies.")
                return
        proxy = PM.get() if PROXY_ENABLED else None
        await m.edit_text("⏳ Logging in Instagram...")
        d = None
        ok = False
        try:
            d = await asyncio.to_thread(build_driver, proxy)
            ok = await asyncio.to_thread(do_login, d, u, p)
            if ok:
                await asyncio.to_thread(ck_save, d, uid, u)
        except Exception as e:
            log.exception(f"add_ig err: {e}")
        finally:
            if d:
                await asyncio.to_thread(close_driver, d)
        if proxy:
            PM.mark_ok(proxy) if ok else PM.mark_fail(proxy)
        if ok:
            ig[u] = p
            db_save()
            ctx.user_data.clear()
            await m.edit_text(
                f"<pre>{head('ACCOUNT ADDED')}</pre>\n"
                f"<b>Total accounts</b> · {len(ig)}\n\n"
                f"Add more or return to menu.",
                parse_mode=ParseMode.HTML,
                reply_markup=main_menu_kb(uid),
            )
        else:
            await m.edit_text(
                "❌ Login failed. Try again.",
                reply_markup=main_menu_kb(uid),
            )
        return

    if step == "quick_add":
        parts = [x.strip() for x in text.splitlines() if x.strip().startswith("http")]
        if not parts:
            await update.message.reply_text("Send valid URLs.")
            return
        ctx.user_data["quick_queue"].extend(parts)
        await update.message.reply_text(
            f"✔ {len(ctx.user_data['quick_queue'])} URLs queued.\n"
            f"Send more or type amount (1 – {CAP}) to start."
        )
        return

    if step == "custom_type":
        mapping = {
            "👤 Profile": "profile",
            "🖼 Post": "post",
            "🎞 Reel": "reel",
            "📖 Story": "story",
            "🎲 Random Mix": "random",
        }
        tt = mapping.get(text)
        if not tt:
            await update.message.reply_text("Pick from the menu.")
            return
        ctx.user_data["target_type"] = tt
        ctx.user_data["step"] = "custom_reason"
        await edit_or_reply(
            update,
            ctx,
            f"<pre>{head('CHOOSE REASON')}</pre>\nTarget · {TYPE_MAP.get(tt, ('','',''))[1] if tt != 'random' else 'Random Mix'}",
            reason_menu_kb(),
        )
        return

    if step == "custom_reason":
        if text == "🎲 Random Reason":
            ctx.user_data["reason_key"] = "random"
        else:
            m = re.match(r"^(\d+)\.", text)
            if not m:
                await update.message.reply_text("Pick a valid reason.")
                return
            ctx.user_data["reason_key"] = m.group(1)
        ctx.user_data["step"] = "custom_url"
        await edit_or_reply(
            update,
            ctx,
            f"<pre>{head('TARGET URL')}</pre>\nSend URL:",
            cancel_kb(),
        )
        return

    if step == "custom_url":
        if not text.startswith("http"):
            await update.message.reply_text("Send valid URL.")
            return
        ctx.user_data["url"] = text
        ctx.user_data["step"] = "custom_amount"
        await edit_or_reply(
            update,
            ctx,
            f"<pre>{head('AMOUNT')}</pre>\nSend amount (1 – {CAP}):",
            cancel_kb(),
        )
        return

    if step == "custom_amount":
        if not text.isdigit():
            await update.message.reply_text("Send a number.")
            return
        amt = int(text)
        if amt < 1 or amt > CAP:
            await update.message.reply_text(f"Between 1 and {CAP}.")
            return
        tt = ctx.user_data.get("target_type", "profile")
        rk = ctx.user_data.get("reason_key", "1")
        url = ctx.user_data.get("url")
        ctx.user_data.clear()
        msg = await update.message.reply_text("⏳ Starting...")
        await run_batch(msg, update, ctx, tt, url, rk, amt)
        return

    if step == "quick_add" and text.isdigit():
        amt = int(text)
        if amt < 1 or amt > CAP:
            await update.message.reply_text(f"Between 1 and {CAP}.")
            return
        qlist = ctx.user_data.get("quick_queue", [])
        msg = await update.message.reply_text("⏳ Starting queue...")
        for url in qlist:
            await run_batch(msg, update, ctx, "random", url, "random", amt)
        ctx.user_data.clear()
        return

    if not is_admin(uid):
        return

    await edit_or_reply(update, ctx, "Unknown action. Use the menu.", main_menu_kb(uid))


def pick_reason(rk):
    return random.choice(list(REASONS.keys())) if rk == "random" else rk


def pick_type(tt):
    return random.choice(["profile", "post", "reel"]) if tt == "random" else tt


async def run_batch(message, update, ctx, ttype, url, rkey, amount):
    uid = str(update.effective_user.id)
    ig = USERS[uid].get("ig_accounts", {})

    if not ig:
        await message.edit_text(
            "❌ No Instagram account. Add one from 👥 My Accounts.",
            parse_mode=ParseMode.HTML,
        )
        return

    if PROXY_ENABLED:
        await PM.refresh_all(force=False)
        if not PM.available():
            await message.edit_text("❌ No working proxies available.")
            return

    accounts = list(ig.items())
    if not accounts:
        await message.edit_text("❌ No accounts available.")
        return

    per = max(1, amount // len(accounts))
    tasks = [(u, p, per) for u, p in accounts]
    rem = amount - per * len(accounts)
    for i in range(rem):
        tasks[i % len(tasks)] = (tasks[i % len(tasks)][0], tasks[i % len(tasks)][1], tasks[i % len(tasks)][2] + 1)

    state = {"cur": 0, "ok": 0, "fail": 0, "last": "", "acc_used": 0, "proxy_used": 0}
    stop = asyncio.Event()
    t0 = time.time()

    async def animator():
        last = ""
        i = 0
        while not stop.is_set():
            pct = int(state["cur"] / amount * 100) if amount else 0
            el = int(time.time() - t0)
            rate = round(state["cur"] / max(el, 1) * 60, 1)
            f = SPIN[i % len(SPIN)]
            body = (
                f"<pre>{head('PROCESSING')}</pre>\n"
                f"{f}  {bar(pct)}  {pct}%\n\n"
                f"<b>▸ {state['cur']} / {amount}</b>\n"
                f"✔ {state['ok']}   ✘ {state['fail']}   ⚡ {rate}/m\n"
                f"👥 {state['acc_used']}   🌐 {state['proxy_used']}   ⧗ {el}s"
            )
            if body != last:
                try:
                    await message.edit_text(body, parse_mode=ParseMode.HTML)
                    last = body
                except Exception:
                    pass
            i += 1
            await asyncio.sleep(0.8)

    async def process_account(igu, igp, quota):
        proxy = PM.get() if PROXY_ENABLED else None
        if PROXY_ENABLED and proxy is None:
            log.warning("no proxy, skip")
            return
        try:
            d = await asyncio.to_thread(build_driver, proxy)
        except Exception as e:
            log.warning(f"driver err: {e}")
            return

        state["acc_used"] += 1
        if proxy:
            state["proxy_used"] += 1

        try:
            loaded = await asyncio.to_thread(ck_load, d, uid, igu)
            if not loaded or not await asyncio.to_thread(ck_alive, d):
                ok = await asyncio.to_thread(do_login, d, igu, igp)
                if not ok:
                    log.warning(f"reauth fail {igu[:3]}***")
                    if proxy:
                        PM.mark_fail(proxy)
                    return
                await asyncio.to_thread(ck_save, d, uid, igu)
        except Exception as e:
            log.warning(f"session err: {e}")

        for i in range(quota):
            if stop.is_set():
                break
            use_type = pick_type(ttype)
            use_reason = pick_reason(rkey)
            try:
                await asyncio.to_thread(do_report, d, use_type, url, use_reason)
                state["ok"] += 1
                USERS[uid]["success_reports"] = USERS[uid].get("success_reports", 0) + 1
                add_points(uid, POINTS_PER_REPORT, "success report")
                if proxy:
                    PM.mark_ok(proxy)
                log.info(f"[{uid}] {igu[:3]}*** {state['cur']+1}/{amount} ok [{use_type}/{use_reason}]")
            except Exception as e:
                state["fail"] += 1
                state["last"] = f"{igu[:3]}***: {str(e)[:60]}"
                if proxy:
                    PM.mark_fail(proxy)
                log.warning(f"[{uid}] {igu[:3]}*** fail: {e}")
                if "challenge" in str(e).lower() or "expired" in str(e).lower():
                    try:
                        await asyncio.to_thread(ck_save, d, uid, igu)
                    except Exception:
                        pass
                    break
            state["cur"] += 1
            await asyncio.sleep(random.uniform(D_MIN, D_MAX))

        try:
            d.quit()
        except Exception:
            pass
        ext = getattr(d, "_igx_ext", None)
        if ext:
            cleanup_extension(ext)

    at = asyncio.create_task(animator())
    wts = [asyncio.create_task(process_account(u, p, q)) for u, p, q in tasks]
    await asyncio.gather(*wts)
    stop.set()
    await at

    el = int(time.time() - t0)
    USERS[uid]["total_reports"] = USERS[uid].get("total_reports", 0) + amount
    DB["history"].append(
        {
            "uid": uid,
            "target": uname(url),
            "type": ttype,
            "reason": rkey,
            "amount": amount,
            "success": state["ok"],
            "failed": state["fail"],
            "ts": datetime.now().isoformat(),
            "elapsed": el,
        }
    )
    if PROXY_AUTO_PRUNE:
        PM.prune_dead()
    db_save()

    pct = round(state["ok"] / max(amount, 1) * 100, 1)
    result = (
        f"<pre>{head('COMPLETED')}</pre>\n"
        f"<code>{bar(pct)} {pct}%</code>\n\n"
        f"Attempted · {amount}\n"
        f"✔ {state['ok']}   ✘ {state['fail']}\n"
        f"👥 {state['acc_used']} accounts   🌐 {state['proxy_used']} proxies\n"
        f"⧗ {el}s\n"
        f"<b>+{state['ok'] * POINTS_PER_REPORT} points</b>\n\n"
        f"<i>{OWNER}</i>"
    )
    if state.get("last"):
        result += f"\n\n<code>Last: {state['last']}</code>"
    try:
        await message.edit_text(
            result, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb(int(uid))
        )
    except Exception as e:
        log.warning(f"final edit: {e}")


async def periodic_revalidate():
    while True:
        try:
            await asyncio.sleep(PROXY_REVALIDATE_EVERY)
            if PROXY_ENABLED:
                await PM.refresh_all(force=True)
        except Exception as e:
            log.warning(f"revalidate loop err: {e}")


async def on_startup(app):
    log.info(f"{BRAND} booting")
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Open main menu"),
            BotCommand("cancel", "Cancel current action"),
        ]
    )
    if PROXY_ENABLED:
        await PM.refresh_all(force=True)
    asyncio.create_task(periodic_revalidate())


def build():
    app = Application.builder().token(TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app


if __name__ == "__main__":
    db_load()
    build().run_polling(drop_pending_updates=True)
