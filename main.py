# -*- coding: utf-8 -*-
"""
main.py — DarkBD File Hosting Bot (FINAL ELITE FIXED VERSION)
==============================================================
"""

import os
import sys
import telebot
import subprocess
import uuid
import zipfile
import shutil
import tempfile
import glob
import time
import re
import sqlite3
import logging
import threading
import atexit
import requests
import psutil
from telebot import types
from datetime import datetime, timedelta

# =============================================================================
# STEP 1: LOAD ENV VARIABLES
# =============================================================================
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _PROJECT_ROOT)

try:
    import vars as _elite_vars
    print("✅ Loaded CipherElite vars.py")
except ImportError:
    print("⚠️ vars.py not found, will try .env directly")

_ENV_PATHS = [
    os.path.join(_PROJECT_ROOT, '.env'),
    os.path.join(os.getcwd(), '.env'),
    os.path.join(_PROJECT_ROOT, 'config', '.env'),
]
_ENV_LOADED = False
for _env_path in _ENV_PATHS:
    if os.path.isfile(_env_path):
        try:
            with open(_env_path, 'r', encoding='utf-8') as _f:
                for _line in _f:
                    _line = _line.strip()
                    if not _line or _line.startswith('#') or '=' not in _line:
                        continue
                    _k, _v = _line.split('=', 1)
                    _k = _k.strip()
                    _v = _v.strip().strip('"').strip("'")
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v
            print(f"✅ Loaded .env from: {_env_path}")
            _ENV_LOADED = True
            break
        except Exception as _e:
            print(f"⚠️ Failed to load {_env_path}: {_e}")

# =============================================================================
# STEP 2: VERIFY TOKEN
# =============================================================================
_TOKEN_CHECK = (
    os.environ.get('HOST_BOT_TOKEN', '').strip()
    or os.environ.get('BOT_TOKEN', '').strip()
    or ''
)

if not _TOKEN_CHECK:
    raise SystemExit("❌ BOT TOKEN IS MISSING! Please check your .env file.")

print(f"✅ Token found: {_TOKEN_CHECK[:10]}...{_TOKEN_CHECK[-4:]}")

# =============================================================================
# CONFIGURATION
# =============================================================================
TOKEN = _TOKEN_CHECK
OWNER_ID = int(os.environ.get('HOST_OWNER_ID', os.environ.get('OWNER_ID', '5076047031')))
ADMIN_ID = int(os.environ.get('HOST_ADMIN_ID', str(OWNER_ID)))
YOUR_USERNAME = os.environ.get('HOST_CONTACT', '@mrdarkvipx')
UPDATE_CHANNEL = os.environ.get('HOST_CHANNEL', 'https://t.me/numbervirtualfast')

PERSISTENT_DIR = os.environ.get(
    'HOSTING_PERSISTENT_DIR',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(PERSISTENT_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(PERSISTENT_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')
BACKUP_DIR = os.path.join(PERSISTENT_DIR, 'backups')
SAFETY_DIR = os.path.join(PERSISTENT_DIR, 'pre_restore_backup')
LOG_FILE = os.path.join(IROTECH_DIR, 'hosting_bot.log')

for _d in (PERSISTENT_DIR, UPLOAD_BOTS_DIR, IROTECH_DIR, BACKUP_DIR, SAFETY_DIR):
    os.makedirs(_d, exist_ok=True)

FREE_USER_LIMIT = 3
SUBSCRIBED_USER_LIMIT = 15
ADMIN_LIMIT = 999
OWNER_LIMIT = float('inf')

AUTO_BACKUP_ENABLED = os.environ.get('AUTO_BACKUP_ENABLED', '1') == '1'
AUTO_BACKUP_INTERVAL_HOURS = int(os.environ.get('AUTO_BACKUP_INTERVAL_HOURS', '6'))
AUTO_BACKUP_KEEP = int(os.environ.get('AUTO_BACKUP_KEEP', '10'))

AUTO_RESTART_ENABLED = os.environ.get('AUTO_RESTART_ENABLED', '1') == '1'
AUTO_RESTART_MAX_RETRIES = int(os.environ.get('AUTO_RESTART_MAX_RETRIES', '5'))
AUTO_RESTART_COOLDOWN = int(os.environ.get('AUTO_RESTART_COOLDOWN', '60'))

AUTO_INSTALL_DEPS = os.environ.get('AUTO_INSTALL_DEPS', '1') == '1'
PIP_INSTALL_TIMEOUT = int(os.environ.get('PIP_INSTALL_TIMEOUT', '120'))
NPM_INSTALL_TIMEOUT = int(os.environ.get('NPM_INSTALL_TIMEOUT', '120'))

PORT_RANGE_START = int(os.environ.get('PORT_RANGE_START', '10000'))
PORT_RANGE_END = int(os.environ.get('PORT_RANGE_END', '20000'))

LOG_MAX_SIZE_MB = int(os.environ.get('LOG_MAX_SIZE_MB', '5'))
LOG_MAX_FILES = int(os.environ.get('LOG_MAX_FILES', '3'))

SCRIPT_EXTS = {'.py', '.js'}
ARCHIVE_EXTS = {'.zip', '.tar.gz', '.tgz', '.tar'}
CONFIG_EXTS = {
    '.env', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.txt', '.xml', '.properties', '.sh', '.bash', '.bat', '.cmd',
    '.csv', '.md', '.sql', '.pem', '.key', '.crt', '.cer', '.log',
    '.lock', '.gitignore', '.npmrc', '.babelrc', '.eslintrc',
}

SAFE_ENV_KEYS = {
    'PATH', 'HOME', 'USER', 'USERNAME', 'LOGNAME', 'LANG', 'LC_ALL', 'LC_CTYPE', 'LANGUAGE',
    'TZ', 'TMPDIR', 'TMP', 'TEMP', 'SHELL', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONIOENCODING', 
    'PYTHONUNBUFFERED', 'PYTHONDONTWRITEBYTECODE', 'NODE_PATH', 'NODE_ENV', 'TERM', 'COLORTERM',
    'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'COMSPEC', 'PATHEXT', 'APPDATA', 'LOCALAPPDATA', 
    'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMDATA', 'ALLUSERSPROFILE', 'PUBLIC', 'COMPUTERNAME', 
    'HOSTNAME', 'OS', 'PROCESSOR_ARCHITECTURE', 'BOT_TOKEN', 'OWNER_ID', 'ADMIN_IDS', 'PORT',
    'SQLITE_DB_PATH', 'SQLITE_DB_NAME', 'DB_PATH', 'DB_NAME',
}

# =============================================================================
# LOGGING
# =============================================================================
class RotatingFileHandler(logging.Handler):
    def __init__(self, filepath, max_size_bytes, max_files):
        super().__init__()
        self.filepath = filepath
        self.max_size = max_size_bytes
        self.max_files = max_files

    def _check_rotation(self):
        try:
            if os.path.exists(self.filepath) and os.path.getsize(self.filepath) > self.max_size:
                for i in range(self.max_files - 1, 0, -1):
                    old = f"{self.filepath}.{i}"
                    new = f"{self.filepath}.{i + 1}"
                    if os.path.exists(old):
                        if os.path.exists(new):
                            os.remove(new)
                        os.rename(old, new)
                if os.path.exists(self.filepath):
                    os.rename(self.filepath, f"{self.filepath}.1")
        except Exception:
            pass

    def emit(self, record):
        try:
            self._check_rotation()
            msg = self.format(record) + '\n'
            with open(self.filepath, 'a', encoding='utf-8', errors='ignore') as f:
                f.write(msg)
        except Exception:
            pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(LOG_FILE, LOG_MAX_SIZE_MB * 1024 * 1024, LOG_MAX_FILES),
        logging.StreamHandler(sys.stdout),
    ],
    force=True,
)
logging.getLogger("TeleBot").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger("HostingBot")

# =============================================================================
# BOT INIT & STATE
# =============================================================================
bot = telebot.TeleBot(TOKEN)
bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False
BOT_START_TIME = datetime.now()
RESTORE_STATE = {}
DB_LOCK = threading.Lock()
ENV_EDIT_STATE = {}
USED_PORTS = {}
SCRIPTS_LOCK = threading.Lock()
_polling_thread = None
_polling_stop = threading.Event()

COMMAND_BUTTONS_LAYOUT_USER = [
    ["📢 Updates Channel"],
    ["📤 Upload File", "📂 Check Files"],
    ["⚡ Bot Speed"],
    ["📞 Contact Owner"]
]

ADMIN_COMMAND_BUTTONS_LAYOUT = [
    ["📢 Updates Channel"],
    ["📤 Upload File", "📂 Check Files"],
    ["⚡ Bot Speed", "📊 Statistics"],
    ["💳 Subscriptions", "📢 Broadcast"],
    ["🔒 Lock Bot", "🟢 Running All Code"],
    ["👑 Admin Panel", "📞 Contact Owner"]
]

# =============================================================================
# DATABASE
# =============================================================================
def _new_file_id():
    return uuid.uuid4().hex[:12]

def init_db():
    logger.info(f"Initializing database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_users (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')

        c.execute("PRAGMA table_info(user_files)")
        cols = [row[1] for row in c.fetchall()]
        if not cols:
            c.execute('''CREATE TABLE user_files (
                user_id INTEGER, file_id TEXT, file_name TEXT, file_type TEXT,
                port INTEGER DEFAULT 0, auto_restart INTEGER DEFAULT 0, restart_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, file_id))''')
        elif 'file_id' not in cols:
            c.execute('ALTER TABLE user_files RENAME TO user_files_legacy')
            c.execute('''CREATE TABLE user_files (
                user_id INTEGER, file_id TEXT, file_name TEXT, file_type TEXT,
                port INTEGER DEFAULT 0, auto_restart INTEGER DEFAULT 0, restart_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, file_id))''')
            legacy = c.execute("SELECT user_id, file_name, file_type FROM user_files_legacy").fetchall()
            for uid, fname, ftype in legacy:
                c.execute('INSERT INTO user_files (user_id, file_id, file_name, file_type) VALUES (?, ?, ?, ?)',
                    (uid, _new_file_id(), fname, ftype))
            c.execute('DROP TABLE user_files_legacy')
        else:
            for col in ['port', 'auto_restart', 'restart_count']:
                if col not in cols:
                    c.execute(f'ALTER TABLE user_files ADD COLUMN {col} INTEGER DEFAULT 0')

        c.execute('''CREATE TABLE IF NOT EXISTS script_env (
            user_id INTEGER, file_id TEXT, key TEXT, value TEXT, PRIMARY KEY (user_id, file_id, key))''')

        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
        if ADMIN_ID != OWNER_ID:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ DB init error: {e}", exc_info=True)

def load_data():
    logger.info("Loading data from database...")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id, expiry FROM subscriptions')
        for user_id, expiry in c.fetchall():
            try: user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
            except ValueError: pass

        c.execute('SELECT user_id, file_id, file_name, file_type, port, auto_restart, restart_count FROM user_files')
        for user_id, file_id, file_name, file_type, port, auto_restart, restart_count in c.fetchall():
            user_files.setdefault(user_id, []).append({
                'file_id': file_id, 'file_name': file_name, 'file_type': file_type,
                'port': port or 0, 'auto_restart': bool(auto_restart), 'restart_count': restart_count or 0,
            })

        c.execute('SELECT user_id FROM active_users')
        active_users.update(uid for (uid,) in c.fetchall())

        c.execute('SELECT user_id FROM admins')
        admin_ids.update(uid for (uid,) in c.fetchall())
        conn.close()
        logger.info(f"Data loaded: {len(active_users)} users, {len(admin_ids)} admins.")
    except Exception as e:
        logger.error(f"❌ Load data error: {e}", exc_info=True)

# =============================================================================
# HELPERS
# =============================================================================
def sanitize_filename(name: str) -> str:
    if not name: return ""
    name = str(name).replace('\\', '/').split('/')[-1]
    name = os.path.basename(name).replace('\x00', '')
    name = re.sub(r'[\x01-\x1f\x7f]', '', name)
    if name in ('', '.', '..'): return ""
    return name

def classify_file(filename: str):
    safe = sanitize_filename(filename)
    if not safe: return ('unknown', '')
    lower = safe.lower()
    if lower.startswith('.'): return ('config', lower)
    for ext in ('.tar.gz', '.tgz'):
        if lower.endswith(ext): return ('archive', ext)
    ext = os.path.splitext(lower)[1]
    if ext in SCRIPT_EXTS: return ('script', ext)
    if ext in ARCHIVE_EXTS: return ('archive', ext)
    if ext in CONFIG_EXTS: return ('config', ext)
    return ('unknown', ext)

def load_user_env(folder: str) -> dict:
    env = {}
    env_path = os.path.join(folder, '.env')
    if not os.path.isfile(env_path): return env
    try:
        with open(env_path, 'r', encoding='utf-8', errors='ignore') as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line: continue
                key, val = line.split('=', 1)
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
                    env[key] = val
    except Exception: pass
    return env

def load_script_env_from_db(user_id, file_id) -> dict:
    env = {}
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute('SELECT key, value FROM script_env WHERE user_id = ? AND file_id = ?', (user_id, file_id))
            for key, value in c.fetchall(): env[key] = value
            conn.close()
    except Exception: pass
    return env

def save_script_env_to_db(user_id, file_id, key, value):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO script_env (user_id, file_id, key, value) VALUES (?, ?, ?, ?)', (user_id, file_id, key, value))
            conn.commit()
        except Exception: pass
        finally: conn.close()

def delete_script_env_key(user_id, file_id, key):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM script_env WHERE user_id = ? AND file_id = ? AND key = ?', (user_id, file_id, key))
            conn.commit()
        except Exception: pass
        finally: conn.close()

def build_subprocess_env(upload_folder: str, user_id=None, file_id=None) -> dict:
    env = {}
    for k in SAFE_ENV_KEYS:
        if k in os.environ: env[k] = os.environ[k]
    env.setdefault('PYTHONUNBUFFERED', '1')
    env.setdefault('PYTHONIOENCODING', 'utf-8')
    env.setdefault('HOME', upload_folder)
    env.setdefault('PWD', upload_folder)
    env.update(load_user_env(upload_folder))
    if user_id and file_id: env.update(load_script_env_from_db(user_id, file_id))
    return env

def get_user_folder(user_id) -> str:
    folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder

def get_upload_folder(user_id, file_id) -> str:
    folder = os.path.join(get_user_folder(user_id), str(file_id))
    os.makedirs(folder, exist_ok=True)
    return folder

def find_file_record(user_id, file_id):
    for f in user_files.get(user_id, []):
        if f['file_id'] == file_id: return f
    return None

def get_user_file_limit(user_id):
    if user_id == OWNER_ID: return OWNER_LIMIT
    if user_id in admin_ids: return ADMIN_LIMIT
    if user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now(): return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT

def get_user_file_count(user_id):
    return sum(1 for f in user_files.get(user_id, []) if f['file_type'] in ('py', 'js'))

def get_uptime_str():
    delta = datetime.now() - BOT_START_TIME
    d = delta.days
    h, rem = divmod(delta.seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

def get_user_status_str(user_id):
    if user_id == OWNER_ID: return "👑 Owner"
    if user_id in admin_ids: return "🛡️ Admin"
    if user_id in user_subscriptions:
        ed = user_subscriptions[user_id].get('expiry')
        if ed and ed > datetime.now(): return "⭐ Premium"
    return "🆓 Free User"

def allocate_port() -> int:
    for port in range(PORT_RANGE_START, PORT_RANGE_END):
        if port in USED_PORTS.values(): continue
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            if result != 0: return port
        except Exception: continue
    return 0

def _cleanup_script_entry(script_key):
    info = bot_scripts.get(script_key)
    if not info: return
    lf = info.get('log_file')
    if lf is not None and hasattr(lf, 'close'):
        try:
            if not lf.closed: lf.close()
        except Exception: pass
    port = info.get('port')
    if port: USED_PORTS.pop(script_key, None)
    bot_scripts.pop(script_key, None)

def is_bot_running(script_owner_id, file_id):
    script_key = f"{script_owner_id}_{file_id}"
    info = bot_scripts.get(script_key)
    if info and info.get('process'):
        try:
            proc = psutil.Process(info['process'].pid)
            running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
            if not running: _cleanup_script_entry(script_key)
            return running
        except psutil.NoSuchProcess:
            _cleanup_script_entry(script_key)
            return False
        except Exception: return False
    return False

def kill_process_tree(process_info):
    try:
        lf = process_info.get('log_file')
        if lf is not None and hasattr(lf, 'close') and not lf.closed:
            try: lf.close()
            except Exception: pass
        process = process_info.get('process')
        if process and hasattr(process, 'pid') and process.pid:
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    try: child.terminate()
                    except Exception:
                        try: child.kill()
                        except Exception: pass
                gone, alive = psutil.wait_procs(children, timeout=1)
                for p in alive:
                    try: p.kill()
                    except Exception: pass
                try:
                    parent.terminate()
                    try: parent.wait(timeout=1)
                    except psutil.TimeoutExpired: parent.kill()
                except psutil.NoSuchProcess: pass
            except psutil.NoSuchProcess: pass
    except Exception as e: logger.error(f"Error killing process tree: {e}")

def get_process_resource_usage(script_key):
    info = bot_scripts.get(script_key)
    if not info or not info.get('process'): return None
    try:
        proc = psutil.Process(info['process'].pid)
        if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE: return None
        cpu = proc.cpu_percent(interval=0.5)
        mem_info = proc.memory_info()
        mem_mb = mem_info.rss / (1024 * 1024)
        threads = proc.num_threads()
        uptime = datetime.now() - info['start_time']
        return {
            'cpu': round(cpu, 1), 'mem_mb': round(mem_mb, 2), 'threads': threads,
            'uptime': str(uptime).split('.')[0], 'pid': proc.pid, 'status': proc.status(),
        }
    except Exception: return None

def get_last_log_lines(log_path, n=15):
    try:
        if not os.path.exists(log_path): return "(no log file)"
        size = os.path.getsize(log_path)
        if size == 0: return "(empty log)"
        with open(log_path, 'rb') as f:
            if size > 5000:
                f.seek(-5000, os.SEEK_END)
                data = f.read()
            else:
                f.seek(0)
                data = f.read()
        text = data.decode('utf-8', errors='ignore')
        return '\n'.join(text.splitlines()[-n:])
    except Exception: return "(error reading log)"

# =============================================================================
# DB OPERATIONS
# =============================================================================
def save_user_file(user_id, file_id, file_name, file_type='py', port=0, auto_restart=False):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO user_files (user_id, file_id, file_name, file_type, port, auto_restart, restart_count) VALUES (?, ?, ?, ?, ?, ?, 0)',
                (user_id, file_id, file_name, file_type, port, 1 if auto_restart else 0))
            conn.commit()
            lst = user_files.setdefault(user_id, [])
            lst[:] = [f for f in lst if f['file_id'] != file_id]
            lst.append({'file_id': file_id, 'file_name': file_name, 'file_type': file_type,
                        'port': port, 'auto_restart': auto_restart, 'restart_count': 0})
        except Exception as e: logger.error(f"save_user_file: {e}")
        finally: conn.close()

def update_file_port(user_id, file_id, port):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('UPDATE user_files SET port = ? WHERE user_id = ? AND file_id = ?', (port, user_id, file_id))
            conn.commit()
            for f in user_files.get(user_id, []):
                if f['file_id'] == file_id: f['port'] = port
        except Exception: pass
        finally: conn.close()

def update_auto_restart(user_id, file_id, enabled):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('UPDATE user_files SET auto_restart = ? WHERE user_id = ? AND file_id = ?', (1 if enabled else 0, user_id, file_id))
            conn.commit()
            for f in user_files.get(user_id, []):
                if f['file_id'] == file_id: f['auto_restart'] = enabled
        except Exception: pass
        finally: conn.close()

def update_restart_count(user_id, file_id, count):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('UPDATE user_files SET restart_count = ? WHERE user_id = ? AND file_id = ?', (count, user_id, file_id))
            conn.commit()
            for f in user_files.get(user_id, []):
                if f['file_id'] == file_id: f['restart_count'] = count
        except Exception: pass
        finally: conn.close()

def remove_user_file_db(user_id, file_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_id = ?', (user_id, file_id))
            c.execute('DELETE FROM script_env WHERE user_id = ? AND file_id = ?', (user_id, file_id))
            conn.commit()
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f['file_id'] != file_id]
                if not user_files[user_id]: del user_files[user_id]
        except Exception: pass
        finally: conn.close()

def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
        except Exception: pass
        finally: conn.close()

def save_subscription(user_id, expiry):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', (user_id, expiry.isoformat()))
            conn.commit()
            user_subscriptions[user_id] = {'expiry': expiry}
        except Exception: pass
        finally: conn.close()

def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
            conn.commit()
            user_subscriptions.pop(user_id, None)
        except Exception: pass
        finally: conn.close()

def add_admin_db(admin_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (admin_id,))
            conn.commit()
            admin_ids.add(admin_id)
        except Exception: pass
        finally: conn.close()

def remove_admin_db(admin_id):
    if admin_id == OWNER_ID: return False
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM admins WHERE user_id = ?', (admin_id,))
            conn.commit()
            admin_ids.discard(admin_id)
            return True
        except Exception: return False
        finally: conn.close()

# =============================================================================
# DEPENDENCY INSTALLATION
# =============================================================================
def install_pip_requirements(folder, chat_id, file_name):
    req_path = os.path.join(folder, 'requirements.txt')
    if not os.path.isfile(req_path): return False
    try:
        with open(req_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()
        if not content: return False

        bot.send_message(chat_id, f"📦 Installing Python dependencies for `{file_name}`...", parse_mode='Markdown')
        cmd = [sys.executable, '-m', 'pip', 'install', '--user', '-r', req_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=PIP_INSTALL_TIMEOUT, cwd=folder)
        if result.returncode == 0:
            bot.send_message(chat_id, f"✅ Dependencies installed for `{file_name}`", parse_mode='Markdown')
            return True
        else:
            stderr = result.stderr[-800:] if result.stderr else "unknown"
            bot.send_message(chat_id, f"⚠️ Dependency install failed for `{file_name}`:\n```\n{stderr}\n```", parse_mode='Markdown')
            return False
    except Exception as e:
        logger.error(f"pip install error: {e}")
        return False

def install_npm_requirements(folder, chat_id, file_name):
    pkg_path = os.path.join(folder, 'package.json')
    if not os.path.isfile(pkg_path): return False
    try:
        bot.send_message(chat_id, f"📦 Installing Node.js dependencies for `{file_name}`...", parse_mode='Markdown')
        cmd = ['npm', 'install', '--prefix', folder]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=NPM_INSTALL_TIMEOUT, cwd=folder)
        if result.returncode == 0:
            bot.send_message(chat_id, f"✅ Node.js dependencies installed for `{file_name}`", parse_mode='Markdown')
            return True
        else:
            stderr = result.stderr[-800:] if result.stderr else "unknown"
            bot.send_message(chat_id, f"⚠️ npm install failed for `{file_name}`:\n```\n{stderr}\n```", parse_mode='Markdown')
            return False
    except Exception as e:
        logger.error(f"npm install error: {e}")
        return False

# =============================================================================
# SCRIPT RUNNER & MONITOR
# =============================================================================
def run_script(script_path, script_owner_id, upload_folder, file_name, file_id, message_obj_for_reply, is_auto_restart=False):
    script_key = f"{script_owner_id}_{file_id}"
    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Script '{file_name}' not found!")
            remove_user_file_db(script_owner_id, file_id)
            return

        log_file_path = os.path.join(upload_folder, f"{os.path.splitext(file_name)[0]}.log")
        try: log_file = open(log_file_path, 'a', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"❌ Log open failed: {e}")
            return

        try:
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            user_env = build_subprocess_env(upload_folder, script_owner_id, file_id)
            process = subprocess.Popen(
                [sys.executable, script_path], cwd=upload_folder,
                stdout=log_file, stderr=log_file, stdin=subprocess.PIPE,
                startupinfo=startupinfo, creationflags=creationflags,
                encoding='utf-8', errors='ignore', env=user_env,
            )
            fi = find_file_record(script_owner_id, file_id)
            port = fi.get('port', 0) if fi else 0
            auto_restart_flag = fi.get('auto_restart', False) if fi else False

            with SCRIPTS_LOCK:
                bot_scripts[script_key] = {
                    'process': process, 'log_file': log_file, 'file_name': file_name, 'file_id': file_id,
                    'chat_id': message_obj_for_reply.chat.id, 'script_owner_id': script_owner_id,
                    'start_time': datetime.now(), 'user_folder': upload_folder, 'type': 'py', 
                    'script_key': script_key, 'port': port, 'auto_restart': auto_restart_flag,
                    'restart_count': fi.get('restart_count', 0) if fi else 0,
                }
                if port: USED_PORTS[script_key] = port

            prefix = "🔄 Auto-restarted" if is_auto_restart else "✅ Started"
            bot.reply_to(message_obj_for_reply, f"{prefix} Python script '{file_name}'! (PID: {process.pid})")
            threading.Thread(target=_monitor_process, args=(script_key, script_path, script_owner_id, upload_folder, file_name, file_id), daemon=True).start()
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, f"❌ Error: {str(e)}")
            bot_scripts.pop(script_key, None)
    except Exception as e:
        logger.error(f"run_script error: {e}")
        bot.reply_to(message_obj_for_reply, f"❌ Unexpected error: {str(e)}")

def run_js_script(script_path, script_owner_id, upload_folder, file_name, file_id, message_obj_for_reply, is_auto_restart=False):
    script_key = f"{script_owner_id}_{file_id}"
    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"❌ Script '{file_name}' not found!")
            remove_user_file_db(script_owner_id, file_id)
            return

        log_file_path = os.path.join(upload_folder, f"{os.path.splitext(file_name)[0]}.log")
        try: log_file = open(log_file_path, 'a', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"❌ Log open failed: {e}")
            return

        try:
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            user_env = build_subprocess_env(upload_folder, script_owner_id, file_id)
            process = subprocess.Popen(
                ['node', script_path], cwd=upload_folder,
                stdout=log_file, stderr=log_file, stdin=subprocess.PIPE,
                startupinfo=startupinfo, creationflags=creationflags,
                encoding='utf-8', errors='ignore', env=user_env,
            )
            fi = find_file_record(script_owner_id, file_id)
            port = fi.get('port', 0) if fi else 0
            auto_restart_flag = fi.get('auto_restart', False) if fi else False

            with SCRIPTS_LOCK:
                bot_scripts[script_key] = {
                    'process': process, 'log_file': log_file, 'file_name': file_name, 'file_id': file_id,
                    'chat_id': message_obj_for_reply.chat.id, 'script_owner_id': script_owner_id,
                    'start_time': datetime.now(), 'user_folder': upload_folder, 'type': 'js', 
                    'script_key': script_key, 'port': port, 'auto_restart': auto_restart_flag,
                    'restart_count': fi.get('restart_count', 0) if fi else 0,
                }
                if port: USED_PORTS[script_key] = port

            prefix = "🔄 Auto-restarted" if is_auto_restart else "✅ Started"
            bot.reply_to(message_obj_for_reply, f"{prefix} JS script '{file_name}'! (PID: {process.pid})")
            threading.Thread(target=_monitor_process, args=(script_key, script_path, script_owner_id, upload_folder, file_name, file_id), daemon=True).start()
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, f"❌ Error: {str(e)}")
            bot_scripts.pop(script_key, None)
    except Exception as e:
        logger.error(f"run_js_script error: {e}")
        bot.reply_to(message_obj_for_reply, f"❌ Unexpected error: {str(e)}")

def _monitor_process(script_key, script_path, script_owner_id, upload_folder, file_name, file_id):
    info = bot_scripts.get(script_key)
    if not info or not info.get('process'): return

    try: info['process'].wait()
    except Exception: pass

    log_path = os.path.join(upload_folder, f"{os.path.splitext(file_name)[0]}.log")
    last_lines = get_last_log_lines(log_path, 10)

    fi = find_file_record(script_owner_id, file_id)
    auto_restart_enabled = fi.get('auto_restart', False) if fi else False
    restart_count = fi.get('restart_count', 0) if fi else 0

    _cleanup_script_entry(script_key)

    if not AUTO_RESTART_ENABLED or not auto_restart_enabled:
        try:
            bot.send_message(info['chat_id'], f"⚠️ Script crashed!\n\n📄 `{file_name}`\n📜 Last log:\n```\n{last_lines[:1500]}\n```", parse_mode='Markdown')
        except Exception: pass
        return

    if restart_count >= AUTO_RESTART_MAX_RETRIES:
        try: bot.send_message(info['chat_id'], f"🛑 Auto-restart limit reached for `{file_name}`.", parse_mode='Markdown')
        except Exception: pass
        update_restart_count(script_owner_id, file_id, 0)
        return

    update_restart_count(script_owner_id, file_id, restart_count + 1)
    try: bot.send_message(info['chat_id'], f"🔄 Auto-restarting `{file_name}`...\nAttempt {restart_count + 1}/{AUTO_RESTART_MAX_RETRIES}", parse_mode='Markdown')
    except Exception: pass

    time.sleep(AUTO_RESTART_COOLDOWN)
    if _polling_stop.is_set(): return
    if not os.path.exists(script_path): return

    class _FakeMsg:
        class _Chat: id = info['chat_id']
        class _FromUser: id = script_owner_id
        chat = _Chat()
        from_user = _FromUser()
        message_id = 0

    if info['type'] == 'py':
        run_script(script_path, script_owner_id, upload_folder, file_name, file_id, _FakeMsg(), is_auto_restart=True)
    else:
        run_js_script(script_path, script_owner_id, upload_folder, file_name, file_id, _FakeMsg(), is_auto_restart=True)

# =============================================================================
# MENU & KEYBOARDS
# =============================================================================
def create_main_menu_inline(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton('📢 Updates Channel', url=UPDATE_CHANNEL),
        types.InlineKeyboardButton('📤 Upload File', callback_data='upload'),
        types.InlineKeyboardButton('📂 Check Files', callback_data='check_files'),
        types.InlineKeyboardButton('⚡ Bot Speed', callback_data='speed'),
        types.InlineKeyboardButton('📞 Contact Owner', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}')
    ]
    if user_id in admin_ids:
        admin_buttons = [
            types.InlineKeyboardButton('💳 Subscriptions', callback_data='subscription'),
            types.InlineKeyboardButton('📊 Statistics', callback_data='stats'),
            types.InlineKeyboardButton('🔒 Lock Bot' if not bot_locked else '🔓 Unlock Bot', callback_data='lock_bot' if not bot_locked else 'unlock_bot'),
            types.InlineKeyboardButton('📢 Broadcast', callback_data='broadcast'),
            types.InlineKeyboardButton('👑 Admin Panel', callback_data='admin_panel'),
            types.InlineKeyboardButton('🟢 Run All Scripts', callback_data='run_all_scripts')
        ]
        markup.add(buttons[0])
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[3], admin_buttons[0])
        markup.add(admin_buttons[1], admin_buttons[3])
        markup.add(admin_buttons[2], admin_buttons[5])
        markup.add(admin_buttons[4])
        markup.add(buttons[4])
    else:
        markup.add(buttons[0])
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[3])
        markup.add(buttons[4])
    return markup

def create_reply_keyboard_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout = ADMIN_COMMAND_BUTTONS_LAYOUT if user_id in admin_ids else COMMAND_BUTTONS_LAYOUT_USER
    for row_buttons_text in layout:
        markup.add(*[types.KeyboardButton(text) for text in row_buttons_text])
    return markup

def create_control_buttons(script_owner_id, file_id, file_name, is_running=True, auto_restart=False, port=0):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("🔴 Stop", callback_data=f'stop_{script_owner_id}_{file_id}'),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f'restart_{script_owner_id}_{file_id}')
        )
        markup.row(
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_id}'),
            types.InlineKeyboardButton("📜 Logs", callback_data=f'logs_{script_owner_id}_{file_id}')
        )
        markup.row(
            types.InlineKeyboardButton("📊 Resources", callback_data=f'resources_{script_owner_id}_{file_id}'),
            types.InlineKeyboardButton("⚙️ Auto-Restart: " + ("ON" if auto_restart else "OFF"), callback_data=f'autorestart_{script_owner_id}_{file_id}')
        )
        if port:
            markup.row(types.InlineKeyboardButton(f"🌐 Port: {port}", callback_data=f'portinfo_{script_owner_id}_{file_id}'))
    else:
        markup.row(
            types.InlineKeyboardButton("🟢 Start", callback_data=f'start_{script_owner_id}_{file_id}'),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_id}')
        )
        markup.row(types.InlineKeyboardButton("📜 View Logs", callback_data=f'logs_{script_owner_id}_{file_id}'))
        markup.row(
            types.InlineKeyboardButton("📊 Resources", callback_data=f'resources_{script_owner_id}_{file_id}'),
            types.InlineKeyboardButton("⚙️ Auto-Restart: " + ("ON" if auto_restart else "OFF"), callback_data=f'autorestart_{script_owner_id}_{file_id}')
        )
        markup.row(
            types.InlineKeyboardButton("🔧 Env Vars", callback_data=f'envmanage_{script_owner_id}_{file_id}'),
            types.InlineKeyboardButton("📁 List Files", callback_data=f'filelist_{script_owner_id}_{file_id}')
        )
        if port:
            markup.row(types.InlineKeyboardButton(f"🌐 Port: {port}", callback_data=f'portinfo_{script_owner_id}_{file_id}'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Files", callback_data='check_files'))
    return markup

def create_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton('➕ Add Admin', callback_data='add_admin'), types.InlineKeyboardButton('➖ Remove Admin', callback_data='remove_admin'))
    markup.row(types.InlineKeyboardButton('📋 List Admins', callback_data='list_admins'))
    markup.row(types.InlineKeyboardButton('👥 User List', callback_data='user_list'), types.InlineKeyboardButton('🟢 Running Bots', callback_data='running_bots'))
    markup.row(types.InlineKeyboardButton('📁 All Files', callback_data='all_files'), types.InlineKeyboardButton('🔍 Search User', callback_data='search_user'))
    markup.row(types.InlineKeyboardButton('🛑 Stop All Bots', callback_data='stop_all_bots'), types.InlineKeyboardButton('🧹 Clean Logs', callback_data='clean_logs'))
    markup.row(types.InlineKeyboardButton('📦 Backup Now', callback_data='backup_now'), types.InlineKeyboardButton('📥 Download DB', callback_data='download_db'))
    markup.row(types.InlineKeyboardButton('📦 Backup Info', callback_data='backup_info'), types.InlineKeyboardButton('♻️ Restore', callback_data='restore_info'))
    markup.row(types.InlineKeyboardButton('🖥️ System Info', callback_data='system_info'), types.InlineKeyboardButton('⏱️ Uptime', callback_data='uptime'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton('➕ Add Subscription', callback_data='add_subscription'), types.InlineKeyboardButton('➖ Remove Subscription', callback_data='remove_subscription'))
    markup.row(types.InlineKeyboardButton('🔍 Check Subscription', callback_data='check_subscription'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_env_management_menu(owner_id, file_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton('➕ Add Var', callback_data=f'envadd_{owner_id}_{file_id}'), types.InlineKeyboardButton('📋 List Vars', callback_data=f'envlist_{owner_id}_{file_id}'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Files', callback_data='check_files'))
    return markup

# =============================================================================
# LOGIC FUNCTIONS
# =============================================================================
def _logic_send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username

    if bot_locked and user_id not in admin_ids:
        bot.send_message(chat_id, "⚠️ Bot locked by admin.")
        return

    user_bio = "Could not fetch bio"
    photo_file_id = None
    try: user_bio = bot.get_chat(user_id).bio or "No bio"
    except Exception: pass
    try:
        p = bot.get_user_profile_photos(user_id, limit=1)
        if p.photos: photo_file_id = p.photos[0][-1].file_id
    except Exception: pass

    if user_id not in active_users:
        add_active_user(user_id)
        try:
            note = f"🎉 New user!\n👤 {user_name}\n✳️ @{user_username or 'N/A'}\n🆔 `{user_id}`\n📝 {user_bio}"
            bot.send_message(OWNER_ID, note, parse_mode='Markdown')
            if photo_file_id: bot.send_photo(OWNER_ID, photo_file_id, caption=f"Pic of {user_id}")
        except Exception: pass

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
    expiry_info = ""

    if user_id == OWNER_ID: user_status = "👑 Owner"
    elif user_id in admin_ids: user_status = "🛡️ Admin"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ Premium"
            days_left = (expiry_date - datetime.now()).days
            expiry_info = f"\n⏳ Expires in: {days_left} days"
        else:
            user_status = "🆓 Free User (Expired)"
            remove_subscription_db(user_id)
    else: user_status = "🆓 Free User"

    welcome_msg_text = (f"〽️ Welcome, {user_name}!\n\n🆔 Your User ID: `{user_id}`\n"
                        f"✳️ Username: `@{user_username or 'Not set'}`\n"
                        f"🔰 Status: {user_status}{expiry_info}\n"
                        f"📁 Scripts: {current_files} / {limit_str}\n\n"
                        f"🤖 Host & run Python (`.py`) or JS (`.js`) scripts.\n"
                        f"   Upload single scripts, `.env`, `.json`, or `.zip` archives.\n\n"
                        f"👇 Use buttons or type commands.")
    main_reply_markup = create_reply_keyboard_main_menu(user_id)
    try:
        if photo_file_id: bot.send_photo(chat_id, photo_file_id)
        bot.send_message(chat_id, welcome_msg_text, reply_markup=main_reply_markup, parse_mode='Markdown')
    except Exception:
        try: bot.send_message(chat_id, welcome_msg_text, reply_markup=main_reply_markup, parse_mode='Markdown')
        except Exception: pass

def _logic_updates_channel(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('📢 Updates Channel', url=UPDATE_CHANNEL))
    bot.reply_to(message, "Visit our Updates Channel:", reply_markup=markup)

def _logic_upload_file(message):
    user_id = message.from_user.id
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked.")
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"⚠️ Script limit ({current_files}/{limit_str}) reached.")
        return
    bot.reply_to(message,
        "📤 Send your file:\n"
        "• `script.py` / `script.js` — runs automatically\n"
        "• `archive.zip` — extracts & runs main script\n"
        "• `.env`, `.json`, `.txt`, `.yaml` etc. — saved only\n\n"
        "ℹ️ Each upload gets its own folder.", parse_mode='Markdown')

def _logic_check_files(message):
    user_id = message.from_user.id
    files = user_files.get(user_id, [])
    if not files:
        bot.reply_to(message, "📂 Your files:\n\n(No files uploaded yet)")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in sorted(files, key=lambda x: (x['file_name'].lower(), x['file_id'])):
        fid, fname, ftype = f['file_id'], f['file_name'], f['file_type']
        is_running = is_bot_running(user_id, fid)
        icon = ("🟢 Running" if is_running else "🔴 Stopped") if ftype in ('py', 'js') else "📄 Config"
        markup.add(types.InlineKeyboardButton(f"{fname}  ·  {fid[:6]} ({ftype}) - {icon}", callback_data=f'file_{user_id}_{fid}'))
    bot.reply_to(message, "📂 Your files:", reply_markup=markup)

def _logic_bot_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    start = time.time()
    wait_msg = bot.reply_to(message, "🏃 Testing speed...")
    try:
        bot.send_chat_action(chat_id, 'typing')
        rt = round((time.time() - start) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        lvl = get_user_status_str(user_id)
        bot.edit_message_text(f"⚡ Bot Speed:\n\n⏱️ API: {rt} ms\n🚦 Status: {status}\n👤 You: {lvl}\n⏳ Uptime: {get_uptime_str()}", chat_id, wait_msg.message_id)
    except Exception as e: logger.error(f"speed: {e}")

def _logic_contact_owner(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('📞 Contact Owner', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'))
    bot.reply_to(message, "Click to contact Owner:", reply_markup=markup)

def _logic_subscriptions_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin required.")
        return
    bot.reply_to(message, "💳 Subscription Management", reply_markup=create_subscription_menu())

def _logic_statistics(message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin permissions required.")
        return
    total_users = len(active_users)
    total_files = sum(len(f) for f in user_files.values())
    running = 0
    my_running = 0
    for sk, info in list(bot_scripts.items()):
        try: s_owner = int(sk.split('_', 1)[0])
        except Exception: continue
        if is_bot_running(s_owner, info['file_id']):
            running += 1
            if s_owner == user_id: my_running += 1
    bot.reply_to(message, f"📊 Bot Statistics:\n\n👥 Total Users: {total_users}\n📂 Total File Records: {total_files}\n🟢 Total Active Bots: {running}\n⏳ Uptime: {get_uptime_str()}\n🔒 Bot Status: {'🔴 Locked' if bot_locked else '🟢 Unlocked'}\n🤖 Your Running Bots: {my_running}\n🛡️ Total Admins: {len(admin_ids)}")

def _logic_broadcast_init(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin required.")
        return
    msg = bot.reply_to(message, "📢 Send message to broadcast.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def _logic_toggle_lock_bot(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin required.")
        return
    global bot_locked
    bot_locked = not bot_locked
    bot.reply_to(message, f"🔒 Bot {'locked' if bot_locked else 'unlocked'}.")

def _logic_admin_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin required.")
        return
    bot.reply_to(message, "👑 Admin Panel", reply_markup=create_admin_panel())

def _logic_run_all_scripts(message_or_call):
    if isinstance(message_or_call, telebot.types.Message):
        admin_user_id = message_or_call.from_user.id
        reply_func = lambda text, **kw: bot.reply_to(message_or_call, text, **kw)
        admin_msg = message_or_call
    elif isinstance(message_or_call, telebot.types.CallbackQuery):
        admin_user_id = message_or_call.from_user.id
        bot.answer_callback_query(message_or_call.id)
        reply_func = lambda text, **kw: bot.send_message(message_or_call.message.chat.id, text, **kw)
        admin_msg = message_or_call.message
    else: return

    if admin_user_id not in admin_ids:
        reply_func("⚠️ Admin required.")
        return

    reply_func("⏳ Starting all user scripts...")
    started = 0
    users_processed = 0
    skipped = 0
    snapshot = {uid: list(files) for uid, files in user_files.items()}

    for tid, files in snapshot.items():
        if not files: continue
        users_processed += 1
        for f in files:
            fid, fname, ftype = f['file_id'], f['file_name'], f['file_type']
            if ftype not in ('py', 'js'): continue
            if is_bot_running(tid, fid): continue
            folder = get_upload_folder(tid, fid)
            fpath = os.path.join(folder, fname)
            if not os.path.exists(fpath):
                skipped += 1; continue
            try:
                if ftype == 'py':
                    threading.Thread(target=run_script, args=(fpath, tid, folder, fname, fid, admin_msg)).start()
                else:
                    threading.Thread(target=run_js_script, args=(fpath, tid, folder, fname, fid, admin_msg)).start()
                started += 1
                time.sleep(0.7)
            except Exception: skipped += 1

    reply_func(f"✅ Done:\n▶️ Started: {started}\n👥 Users: {users_processed}\n⚠️ Skipped: {skipped}")

# =============================================================================
# BACKUP & RESTORE SYSTEM
# =============================================================================
def _create_backup_zip() -> str:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f"hosting_backup_{timestamp}.zip"
    zip_path = os.path.join(BACKUP_DIR, zip_name)
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(DATABASE_PATH): zf.write(DATABASE_PATH, arcname='inf/bot_data.db')
            for root, dirs, files in os.walk(UPLOAD_BOTS_DIR):
                for file in files:
                    fp = os.path.join(root, file)
                    arc = os.path.relpath(fp, PERSISTENT_DIR)
                    zf.write(fp, arcname=arc)
        return zip_path
    except Exception as e: raise

def _cleanup_old_backups():
    try:
        backups = sorted(glob.glob(os.path.join(BACKUP_DIR, 'hosting_backup_*.zip')), key=os.path.getmtime, reverse=True)
        for old in backups[AUTO_BACKUP_KEEP:]:
            try: os.remove(old)
            except Exception: pass
    except Exception: pass

def _restore_from_zip(zip_path: str):
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, os.path.join(SAFETY_DIR, f'bot_data_{timestamp}.db'))

        temp_extract = tempfile.mkdtemp(prefix='restore_')
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_extract)

            for sk in list(bot_scripts.keys()):
                info = bot_scripts.get(sk)
                if info: kill_process_tree(info)
            bot_scripts.clear()

            db_restored = False
            for src in [os.path.join(temp_extract, 'inf', 'bot_data.db'), os.path.join(temp_extract, 'bot_data.db')]:
                if os.path.exists(src):
                    if os.path.exists(DATABASE_PATH): os.remove(DATABASE_PATH)
                    shutil.copy2(src, DATABASE_PATH)
                    db_restored = True
                    break

            uploads_restored = False
            for src in [os.path.join(temp_extract, 'upload_bots'), os.path.join(temp_extract, 'data', 'upload_bots')]:
                if os.path.isdir(src):
                    if os.path.exists(UPLOAD_BOTS_DIR):
                        safety_uploads = os.path.join(SAFETY_DIR, f'upload_bots_{timestamp}')
                        try: shutil.move(UPLOAD_BOTS_DIR, safety_uploads)
                        except Exception: shutil.rmtree(UPLOAD_BOTS_DIR, ignore_errors=True)
                    shutil.copytree(src, UPLOAD_BOTS_DIR)
                    uploads_restored = True
                    break

            if not db_restored and not uploads_restored: return False, "❌ Backup এ কিছু নেই"
            return True, "Restore Successful."
        finally: shutil.rmtree(temp_extract, ignore_errors=True)
    except Exception as e: return False, str(e)

def _restore_db_only(db_path: str):
    try:
        if not os.path.exists(db_path): return False, "❌ File not found"
        with open(db_path, 'rb') as f:
            if not f.read(16).startswith(b'SQLite format 3'): return False, "❌ Not a valid SQLite DB"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, os.path.join(SAFETY_DIR, f'bot_data_{timestamp}.db'))
        os.remove(DATABASE_PATH) if os.path.exists(DATABASE_PATH) else None
        shutil.copy2(db_path, DATABASE_PATH)
        return True, f"✅ DB restored"
    except Exception as e: return False, str(e)

# =============================================================================
# MESSAGE HANDLERS (COMMANDS & DOCS)
# =============================================================================
BUTTON_TEXT_TO_LOGIC = {
    "📢 Updates Channel": _logic_updates_channel,
    "📤 Upload File": _logic_upload_file,
    "📂 Check Files": _logic_check_files,
    "⚡ Bot Speed": _logic_bot_speed,
    "📞 Contact Owner": _logic_contact_owner,
    "📊 Statistics": _logic_statistics,
    "💳 Subscriptions": _logic_subscriptions_panel,
    "📢 Broadcast": _logic_broadcast_init,
    "🔒 Lock Bot": _logic_toggle_lock_bot,
    "🟢 Running All Code": _logic_run_all_scripts,
    "👑 Admin Panel": _logic_admin_panel,
}

@bot.message_handler(commands=['start', 'help'])
def command_send_welcome(message): _logic_send_welcome(message)

@bot.message_handler(func=lambda m: m.text in BUTTON_TEXT_TO_LOGIC)
def handle_button_text(message):
    fn = BUTTON_TEXT_TO_LOGIC.get(message.text)
    if fn: fn(message)

@bot.message_handler(commands=['ping'])
def ping(message):
    start = time.time()
    msg = bot.reply_to(message, "Pong!")
    bot.edit_message_text(f"Pong! Latency: {round((time.time() - start) * 1000, 2)} ms", message.chat.id, msg.message_id)

@bot.message_handler(commands=['backup'])
def backup_command(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin required."); return
    wait_msg = bot.reply_to(message, "⏳ Creating backup...")
    try:
        zip_path = _create_backup_zip()
        _cleanup_old_backups()
        with open(zip_path, 'rb') as f:
            bot.send_document(message.chat.id, f, visible_file_name=os.path.basename(zip_path), caption="✅ Backup complete.")
        bot.delete_message(message.chat.id, wait_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ {e}", message.chat.id, wait_msg.message_id)

@bot.message_handler(commands=['restore'])
def restore_command(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "⚠️ Admin required."); return
    RESTORE_STATE[message.from_user.id] = {"stage": "waiting_file"}
    bot.reply_to(message, "♻️ Send your backup file (.zip or .db):\n/cancel to abort.", parse_mode='Markdown')

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    uid = message.from_user.id
    cancelled = False
    if uid in RESTORE_STATE: del RESTORE_STATE[uid]; cancelled = True
    if uid in ENV_EDIT_STATE: del ENV_EDIT_STATE[uid]; cancelled = True
    bot.reply_to(message, "✅ Cancelled." if cancelled else "ℹ️ Nothing running.")

@bot.message_handler(content_types=['document'])
def handle_file_upload_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    doc = message.document

    if user_id in RESTORE_STATE and RESTORE_STATE[user_id].get('stage') == 'waiting_file':
        _handle_restore_upload(message, doc)
        return

    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked."); return

    file_name = sanitize_filename(doc.file_name) if doc.file_name else ""
    if not file_name:
        bot.reply_to(message, "⚠️ Invalid file name."); return

    category, ext = classify_file(file_name)
    if category == 'unknown':
        bot.reply_to(message, f"⚠️ Unsupported: `{ext}`", parse_mode='Markdown'); return

    if category == 'script':
        if get_user_file_count(user_id) >= get_user_file_limit(user_id):
            bot.reply_to(message, "⚠️ Script limit reached."); return

    if doc.file_size > 20 * 1024 * 1024:
        bot.reply_to(message, "⚠️ File > 20 MB."); return

    try:
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"⬆️ From {message.from_user.first_name} (`{user_id}`)", parse_mode='Markdown')
        except Exception: pass

        wait_msg = bot.reply_to(message, f"⏳ Downloading `{file_name}`...")
        tg_file = bot.get_file(doc.file_id)
        content = bot.download_file(tg_file.file_path)
        bot.edit_message_text("✅ Downloaded. Processing...", chat_id, wait_msg.message_id)

        if category == 'archive':
            handle_zip_file(content, file_name, message)
        else:
            file_id = _new_file_id()
            folder = get_upload_folder(user_id, file_id)
            fpath = os.path.join(folder, file_name)
            with open(fpath, 'wb') as f: f.write(content)
            if category == 'script':
                if ext == '.js': handle_js_file(fpath, user_id, folder, file_name, file_id, message)
                else: handle_py_file(fpath, user_id, folder, file_name, file_id, message)
            elif category == 'config':
                handle_config_file(fpath, user_id, folder, file_name, file_id, message)
    except Exception as e:
        logger.error(f"doc handler: {e}")
        bot.reply_to(message, f"❌ {str(e)}")

def handle_zip_file(downloaded_file_content, file_name_zip, message):
    user_id = message.from_user.id
    file_id = _new_file_id()
    upload_folder = get_upload_folder(user_id, file_id)
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_")
        zip_path = os.path.join(temp_dir, file_name_zip)
        with open(zip_path, 'wb') as nf: nf.write(downloaded_file_content)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        extracted = os.listdir(temp_dir)
        py_files = [f for f in extracted if f.lower().endswith('.py')]
        js_files = [f for f in extracted if f.lower().endswith('.js')]

        main_script_name, file_type = None, None
        for p in ['main.py', 'bot.py', 'app.py']:
            if p in py_files: main_script_name, file_type = p, 'py'; break
        if not main_script_name:
            for p in ['index.js', 'main.js', 'bot.js', 'app.js']:
                if p in js_files: main_script_name, file_type = p, 'js'; break
        if not main_script_name:
            if py_files: main_script_name, file_type = py_files[0], 'py'
            elif js_files: main_script_name, file_type = js_files[0], 'js'

        if not main_script_name:
            bot.reply_to(message, "❌ No `.py` or `.js` script found!"); return

        for item in os.listdir(temp_dir):
            src = os.path.join(temp_dir, item)
            dst = os.path.join(upload_folder, item)
            if os.path.isdir(dst): shutil.rmtree(dst)
            elif os.path.exists(dst): os.remove(dst)
            shutil.move(src, dst)

        save_user_file(user_id, file_id, main_script_name, file_type)
        main_path = os.path.join(upload_folder, main_script_name)
        bot.reply_to(message, f"✅ Extracted (id `{file_id}`). Starting `{main_script_name}`...", parse_mode='Markdown')

        if AUTO_INSTALL_DEPS:
            if file_type == 'py': install_pip_requirements(upload_folder, message.chat.id, main_script_name)
            elif file_type == 'js': install_npm_requirements(upload_folder, message.chat.id, main_script_name)

        if file_type == 'py':
            threading.Thread(target=run_script, args=(main_path, user_id, upload_folder, main_script_name, file_id, message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(main_path, user_id, upload_folder, main_script_name, file_id, message)).start()
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")
        shutil.rmtree(upload_folder, ignore_errors=True)
    finally:
        if temp_dir and os.path.exists(temp_dir): shutil.rmtree(temp_dir, ignore_errors=True)

def handle_py_file(file_path, script_owner_id, upload_folder, file_name, file_id, message):
    try:
        save_user_file(script_owner_id, file_id, file_name, 'py')
        if AUTO_INSTALL_DEPS: install_pip_requirements(upload_folder, message.chat.id, file_name)
        threading.Thread(target=run_script, args=(file_path, script_owner_id, upload_folder, file_name, file_id, message)).start()
    except Exception as e: bot.reply_to(message, f"❌ Error: {str(e)}")

def handle_js_file(file_path, script_owner_id, upload_folder, file_name, file_id, message):
    try:
        save_user_file(script_owner_id, file_id, file_name, 'js')
        if AUTO_INSTALL_DEPS: install_npm_requirements(upload_folder, message.chat.id, file_name)
        threading.Thread(target=run_js_script, args=(file_path, script_owner_id, upload_folder, file_name, file_id, message)).start()
    except Exception as e: bot.reply_to(message, f"❌ Error: {str(e)}")

def handle_config_file(file_path, script_owner_id, upload_folder, file_name, file_id, message):
    try:
        _, ext = classify_file(file_name)
        save_user_file(script_owner_id, file_id, file_name, ext.lstrip('.') or 'config')
        bot.reply_to(message, f"✅ Config saved: `{file_name}` (id `{file_id}`)", parse_mode='Markdown')
    except Exception as e: bot.reply_to(message, f"❌ Error: {str(e)}")

def _handle_restore_upload(message, doc):
    user_id = message.from_user.id
    fname = doc.file_name.lower() if doc.file_name else ""
    if not (fname.endswith('.zip') or fname.endswith('.db')):
        bot.reply_to(message, "⚠️ Send `.zip` or `.db` only."); return

    wait_msg = bot.reply_to(message, f"⏳ Downloading `{doc.file_name}`...")
    try:
        tg_file = bot.get_file(doc.file_id)
        content = bot.download_file(tg_file.file_path)
        temp_dir = tempfile.mkdtemp(prefix='restore_upload_')
        fpath = os.path.join(temp_dir, doc.file_name)
        with open(fpath, 'wb') as f: f.write(content)

        try:
            if fname.endswith('.zip'): ok, result = _restore_from_zip(fpath)
            else: ok, result = _restore_db_only(fpath)

            if ok: final = f"✅ *Restore Complete!*\n\n{result}\n\n🔄 *Restart the bot now* to load new data."
            else: final = f"❌ *Restore Failed*\n\n{result}"
            bot.edit_message_text(final, message.chat.id, wait_msg.message_id, parse_mode='Markdown')
            RESTORE_STATE.pop(user_id, None)
        finally: shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        bot.edit_message_text(f"❌ {e}", message.chat.id, wait_msg.message_id)
        RESTORE_STATE.pop(user_id, None)

# =============================================================================
# CALLBACKS
# =============================================================================
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if bot_locked and user_id not in admin_ids and data not in ['back_to_main', 'speed']:
        bot.answer_callback_query(call.id, "⚠️ Bot locked.", show_alert=True); return

    try:
        if data == 'upload': upload_callback(call)
        elif data == 'check_files': check_files_callback(call)
        elif data.startswith('file_'): file_control_callback(call)
        elif data.startswith('start_'): start_bot_callback(call)
        elif data.startswith('stop_'): stop_bot_callback(call)
        elif data.startswith('restart_'): restart_bot_callback(call)
        elif data.startswith('delete_'): delete_bot_callback(call)
        elif data.startswith('logs_'): logs_bot_callback(call)
        elif data.startswith('resources_'): resources_callback(call)
        elif data.startswith('autorestart_'): autorestart_callback(call)
        elif data.startswith('portinfo_'): portinfo_callback(call)
        elif data.startswith('envmanage_'): env_manage_callback(call)
        elif data.startswith('envadd_'): env_add_callback(call)
        elif data.startswith('envlist_'): env_list_callback(call)
        elif data.startswith('envdel_'): env_del_callback(call)
        elif data.startswith('filelist_'): file_list_callback(call)
        elif data.startswith('downloadfile_'): download_file_callback(call)
        elif data == 'speed': speed_callback(call)
        elif data == 'back_to_main': back_to_main_callback(call)
        elif data == 'stats':
            if user_id in admin_ids: stats_callback(call)
            else: bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True)
        elif data.startswith('confirm_broadcast_'): handle_confirm_broadcast(call)
        elif data == 'cancel_broadcast': handle_cancel_broadcast(call)
        elif data == 'subscription': admin_required_callback(call, subscription_management_callback)
        elif data == 'lock_bot': admin_required_callback(call, lock_bot_callback)
        elif data == 'unlock_bot': admin_required_callback(call, unlock_bot_callback)
        elif data == 'run_all_scripts': admin_required_callback(call, run_all_scripts_callback)
        elif data == 'broadcast': admin_required_callback(call, broadcast_init_callback)
        elif data == 'admin_panel': admin_required_callback(call, admin_panel_callback)
        elif data == 'add_admin': owner_required_callback(call, add_admin_init_callback)
        elif data == 'remove_admin': owner_required_callback(call, remove_admin_init_callback)
        elif data == 'list_admins': admin_required_callback(call, list_admins_callback)
        elif data == 'add_subscription': admin_required_callback(call, add_subscription_init_callback)
        elif data == 'remove_subscription': admin_required_callback(call, remove_subscription_init_callback)
        elif data == 'check_subscription': admin_required_callback(call, check_subscription_init_callback)
        elif data == 'user_list': admin_required_callback(call, user_list_callback)
        elif data == 'running_bots': admin_required_callback(call, running_bots_callback)
        elif data == 'all_files': admin_required_callback(call, all_files_callback)
        elif data == 'stop_all_bots': admin_required_callback(call, stop_all_bots_callback)
        elif data == 'clean_logs': admin_required_callback(call, clean_logs_callback)
        elif data == 'uptime': admin_required_callback(call, uptime_callback)
        elif data == 'system_info': admin_required_callback(call, system_info_callback)
        elif data == 'search_user': admin_required_callback(call, search_user_init_callback)
        elif data == 'backup_now': admin_required_callback(call, backup_now_callback)
        elif data == 'download_db': admin_required_callback(call, download_db_callback)
        elif data == 'backup_info': admin_required_callback(call, backup_info_callback)
        elif data == 'restore_info': admin_required_callback(call, restore_info_callback)
        else: bot.answer_callback_query(call.id, "Unknown.")
    except Exception as e:
        logger.error(f"callback '{data}': {e}")
        try: bot.answer_callback_query(call.id, "Error.", show_alert=True)
        except Exception: pass

def admin_required_callback(call, fn):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "⚠️ Admin required.", show_alert=True); return
    fn(call)

def owner_required_callback(call, fn):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "⚠️ Owner required.", show_alert=True); return
    fn(call)

def _parse_owner_file_id(call):
    _, owner_str, file_id = call.data.split('_', 2)
    return int(owner_str), file_id

def _check_access(call, owner_id):
    req = call.from_user.id
    if not (req == owner_id or req in admin_ids):
        bot.answer_callback_query(call.id, "⚠️ Not yours.", show_alert=True); return False
    return True

def upload_callback(call):
    user_id = call.from_user.id
    if get_user_file_count(user_id) >= get_user_file_limit(user_id):
        bot.answer_callback_query(call.id, "⚠️ Limit reached.", show_alert=True); return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📤 Send your file:\n• `script.py` / `script.js`\n• `archive.zip`\n• config files", parse_mode='Markdown')

def check_files_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    files = user_files.get(user_id, [])
    if not files:
        bot.answer_callback_query(call.id, "⚠️ No files.", show_alert=True)
        try:
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
            bot.edit_message_text("📂 Your files:\n\n(No files)", chat_id, call.message.message_id, reply_markup=markup)
        except Exception: pass
        return
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in sorted(files, key=lambda x: (x['file_name'].lower(), x['file_id'])):
        fid, fname, ftype = f['file_id'], f['file_name'], f['file_type']
        is_running = is_bot_running(user_id, fid)
        icon = ("🟢 Running" if is_running else "🔴 Stopped") if ftype in ('py', 'js') else "📄 Config"
        markup.add(types.InlineKeyboardButton(f"{fname}  ·  {fid[:6]} ({ftype}) - {icon}", callback_data=f'file_{user_id}_{fid}'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
    try: bot.edit_message_text("📂 Your files:", chat_id, call.message.message_id, reply_markup=markup)
    except Exception: pass

def file_control_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): check_files_callback(call); return
        fi = find_file_record(owner_id, file_id)
        if not fi: bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); check_files_callback(call); return
        fname, ftype = fi['file_name'], fi['file_type']
        folder = get_upload_folder(owner_id, file_id)
        auto_restart = fi.get('auto_restart', False)
        port = fi.get('port', 0)
        if ftype not in ('py', 'js'):
            bot.answer_callback_query(call.id)
            try:
                fp = os.path.join(folder, fname)
                size = os.path.getsize(fp) if os.path.exists(fp) else 0
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.row(types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{owner_id}_{file_id}'), types.InlineKeyboardButton("📥 Download", callback_data=f'downloadfile_{owner_id}_{file_id}'))
                markup.row(types.InlineKeyboardButton("🔙 Back", callback_data='check_files'))
                bot.edit_message_text(f"📄 Config: `{fname}`\n🆔 `{file_id}`\n📦 {size} bytes\n👤 `{owner_id}`", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
            except Exception: pass
            return
        bot.answer_callback_query(call.id)
        is_running = is_bot_running(owner_id, file_id)
        st = '🟢 Running' if is_running else '🔴 Stopped'
        try:
            bot.edit_message_text(f"⚙️ `{fname}` ({ftype})\n🆔 `{file_id}`\n👤 `{owner_id}`\nStatus: {st}", call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(owner_id, file_id, fname, is_running, auto_restart, port), parse_mode='Markdown')
        except Exception: pass
    except Exception: pass

def start_bot_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi: bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); return
        fname, ftype = fi['file_name'], fi['file_type']
        if ftype not in ('py', 'js'): bot.answer_callback_query(call.id, "ℹ️ Config can't start.", show_alert=True); return
        folder = get_upload_folder(owner_id, file_id)
        fpath = os.path.join(folder, fname)
        if not os.path.exists(fpath): bot.answer_callback_query(call.id, "⚠️ Missing file.", show_alert=True); remove_user_file_db(owner_id, file_id); return
        if is_bot_running(owner_id, file_id): bot.answer_callback_query(call.id, "⚠️ Already running.", show_alert=True); return
        bot.answer_callback_query(call.id, "⏳ Starting...")
        update_restart_count(owner_id, file_id, 0)
        if ftype == 'py': threading.Thread(target=run_script, args=(fpath, owner_id, folder, fname, file_id, call.message)).start()
        else: threading.Thread(target=run_js_script, args=(fpath, owner_id, folder, fname, file_id, call.message)).start()
        time.sleep(1.5)
        is_now = is_bot_running(owner_id, file_id)
        st = '🟢 Running' if is_now else '🟡 Starting (or failed)'
        try: bot.edit_message_text(f"⚙️ `{fname}` ({ftype})\n🆔 `{file_id}`\n👤 `{owner_id}`\nStatus: {st}", call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(owner_id, file_id, fname, is_now, fi.get('auto_restart', False), fi.get('port', 0)), parse_mode='Markdown')
        except Exception: pass
    except Exception: pass

def stop_bot_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi: bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); return
        fname, ftype = fi['file_name'], fi['file_type']
        sk = f"{owner_id}_{file_id}"
        if not is_bot_running(owner_id, file_id):
            bot.answer_callback_query(call.id, "⚠️ Already stopped.", show_alert=True)
            try: bot.edit_message_text(f"⚙️ `{fname}` ({ftype})\n🆔 `{file_id}`\nStatus: 🔴 Stopped", call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(owner_id, file_id, fname, False, fi.get('auto_restart', False), fi.get('port', 0)), parse_mode='Markdown')
            except Exception: pass
            return
        bot.answer_callback_query(call.id, "⏳ Stopping...")
        info = bot_scripts.get(sk)
        if info: kill_process_tree(info)
        bot_scripts.pop(sk, None)
        USED_PORTS.pop(sk, None)
        try: bot.edit_message_text(f"⚙️ `{fname}` ({ftype})\n🆔 `{file_id}`\nStatus: 🔴 Stopped", call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(owner_id, file_id, fname, False, fi.get('auto_restart', False), fi.get('port', 0)), parse_mode='Markdown')
        except Exception: pass
    except Exception: pass

def restart_bot_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi: bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); return
        fname, ftype = fi['file_name'], fi['file_type']
        if ftype not in ('py', 'js'): bot.answer_callback_query(call.id, "ℹ️ Can't restart.", show_alert=True); return
        folder = get_upload_folder(owner_id, file_id)
        fpath = os.path.join(folder, fname)
        sk = f"{owner_id}_{file_id}"
        if not os.path.exists(fpath): bot.answer_callback_query(call.id, "⚠️ Missing.", show_alert=True); remove_user_file_db(owner_id, file_id); bot_scripts.pop(sk, None); return
        bot.answer_callback_query(call.id, "⏳ Restarting...")
        if is_bot_running(owner_id, file_id):
            info = bot_scripts.get(sk)
            if info: kill_process_tree(info)
            bot_scripts.pop(sk, None)
            time.sleep(1.5)
        update_restart_count(owner_id, file_id, 0)
        if ftype == 'py': threading.Thread(target=run_script, args=(fpath, owner_id, folder, fname, file_id, call.message)).start()
        else: threading.Thread(target=run_js_script, args=(fpath, owner_id, folder, fname, file_id, call.message)).start()
        time.sleep(1.5)
        is_now = is_bot_running(owner_id, file_id)
        st = '🟢 Running' if is_now else '🟡 Starting (or failed)'
        try: bot.edit_message_text(f"⚙️ `{fname}` ({ftype})\n🆔 `{file_id}`\n👤 `{owner_id}`\nStatus: {st}", call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(owner_id, file_id, fname, is_now, fi.get('auto_restart', False), fi.get('port', 0)), parse_mode='Markdown')
        except Exception: pass
    except Exception: pass

def delete_bot_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi: bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); return
        fname = fi['file_name']
        bot.answer_callback_query(call.id, "🗑️ Deleting...")
        sk = f"{owner_id}_{file_id}"
        if is_bot_running(owner_id, file_id):
            info = bot_scripts.get(sk)
            if info: kill_process_tree(info)
            bot_scripts.pop(sk, None)
            time.sleep(0.5)
        folder = get_upload_folder(owner_id, file_id)
        if os.path.isdir(folder): shutil.rmtree(folder, ignore_errors=True)
        remove_user_file_db(owner_id, file_id)
        try: bot.edit_message_text(f"🗑️ Deleted `{fname}`.", call.message.chat.id, call.message.message_id, reply_markup=None, parse_mode='Markdown')
        except Exception: pass
    except Exception: pass

def logs_bot_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi: bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); return
        fname = fi['file_name']
        if fi['file_type'] not in ('py', 'js'): bot.answer_callback_query(call.id, "ℹ️ No logs.", show_alert=True); return
        folder = get_upload_folder(owner_id, file_id)
        log_path = os.path.join(folder, f"{os.path.splitext(fname)[0]}.log")
        if not os.path.exists(log_path): bot.answer_callback_query(call.id, "⚠️ No log file.", show_alert=True); return
        bot.answer_callback_query(call.id, "📜 Loading...")
        try:
            size = os.path.getsize(log_path)
            if size == 0: bot.send_message(call.message.chat.id, f"📜 Empty log.", parse_mode='Markdown'); return
            if size > 3500:
                with open(log_path, 'rb') as f:
                    max_b = 5 * 1024 * 1024
                    if size > max_b: f.seek(-max_b, os.SEEK_END); log_bytes = b"(last 5 MB)\n...\n" + f.read()
                    else: f.seek(0); log_bytes = f.read()
                try: preview = log_bytes.decode('utf-8', errors='ignore')
                except Exception: preview = ""
                last_line = ""
                for ln in reversed(preview.splitlines()[-10:]):
                    if ln.strip(): last_line = ln.strip()[:120]; break
                cap = (f"📜 `{fname}`\n🆔 `{file_id}`\n👤 `{owner_id}`\n📦 {size} bytes\n")
                if last_line: cap += f"🔎 Last: `{last_line}`"
                log_filename = f"{os.path.splitext(fname)[0]}_{file_id}.log"
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.log', delete=False) as tmp:
                    tmp.write(log_bytes); tmp_path = tmp.name
                try:
                    with open(tmp_path, 'rb') as fdoc: bot.send_document(call.message.chat.id, fdoc, visible_file_name=log_filename, caption=cap, parse_mode='Markdown')
                finally:
                    try: os.remove(tmp_path)
                    except Exception: pass
                return
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
            MAX = 3500
            if len(content) > MAX:
                content = content[-MAX:]; nl = content.find('\n')
                if nl != -1 and nl < 200: content = content[nl+1:]
                content = "...(tail)\n" + content
            if not content.strip(): content = "(empty)"
            safe = content.replace('`', "'")
            bot.send_message(call.message.chat.id, f"📜 `{fname}`:\n```\n{safe}\n```", parse_mode='Markdown')
        except Exception as e: bot.send_message(call.message.chat.id, f"❌ Error reading log.")
    except Exception: pass

def resources_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi: return
        if fi['file_type'] not in ('py', 'js'): bot.answer_callback_query(call.id, "ℹ️ No resources for config.", show_alert=True); return
        bot.answer_callback_query(call.id, "📊 Checking...")
        res = get_process_resource_usage(f"{owner_id}_{file_id}")
        if not res: bot.send_message(call.message.chat.id, f"📊 Resources for `{fi['file_name']}`:\n\n🔴 Not running", parse_mode='Markdown'); return
        bot.send_message(call.message.chat.id, f"📊 Resources for `{fi['file_name']}`:\n\n🟡 CPU: {res['cpu']}%\n🔵 Memory: {res['mem_mb']} MB\n🧵 Threads: {res['threads']}\n⏱️ Uptime: {res['uptime']}\n🔧 PID: {res['pid']}\n📌 Status: {res['status']}", parse_mode='Markdown')
    except Exception: pass

def autorestart_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi or fi['file_type'] not in ('py', 'js'): return
        new_val = not fi.get('auto_restart', False)
        update_auto_restart(owner_id, file_id, new_val)
        bot.answer_callback_query(call.id, f"⚙️ Auto-restart {'enabled' if new_val else 'disabled'}")
        is_running = is_bot_running(owner_id, file_id)
        try: bot.edit_message_text(f"⚙️ `{fi['file_name']}` ({fi['file_type']})\n🆔 `{file_id}`\n👤 `{owner_id}`\nStatus: {'🟢 Running' if is_running else '🔴 Stopped'}", call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(owner_id, file_id, fi['file_name'], is_running, new_val, fi.get('port', 0)), parse_mode='Markdown')
        except Exception: pass
    except Exception: pass

def portinfo_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi: return
        port = fi.get('port', 0)
        bot.answer_callback_query(call.id)
        if port: bot.send_message(call.message.chat.id, f"🌐 Port: `{port}`\n📄 `{fi['file_name']}`\n🆔 `{file_id}`", parse_mode='Markdown')
        else:
            new_port = allocate_port()
            if new_port:
                update_file_port(owner_id, file_id, new_port)
                USED_PORTS[f"{owner_id}_{file_id}"] = new_port
                bot.send_message(call.message.chat.id, f"🌐 Allocated port: `{new_port}`\n📄 `{fi['file_name']}`\n\nRestart the script to use this port.", parse_mode='Markdown')
            else: bot.send_message(call.message.chat.id, "❌ No available ports.")
    except Exception: pass

def env_manage_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi: bot.answer_callback_query(call.id, "⚠️ Not found.", show_alert=True); return
        bot.answer_callback_query(call.id)
        env_vars = load_script_env_from_db(owner_id, file_id)
        if env_vars:
            lines = [f"🔧 Environment Variables for `{fi['file_name']}`:\n"]
            for k in sorted(env_vars.keys()):
                v = env_vars[k]
                masked = v[:3] + "***" if len(v) > 3 else "***"
                lines.append(f"• `{k}` = `{masked}`")
                lines.append(f"   🗑️ [del:{k}]")
            text = "\n".join(lines)
        else: text = f"🔧 No env vars set for `{fi['file_name']}`.\nAdd one with the button below."
        markup = create_env_management_menu(owner_id, file_id)
        try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except Exception: bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    except Exception: pass

def env_add_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        bot.answer_callback_query(call.id)
        ENV_EDIT_STATE[call.from_user.id] = {'owner_id': owner_id, 'file_id': file_id, 'stage': 'add_env'}
        msg = bot.send_message(call.message.chat.id, "🔧 Send env var in format:\n`KEY=VALUE`\n\n/cancel to abort", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_env_add)
    except Exception: pass

def process_env_add(message):
    uid = message.from_user.id
    if uid not in ENV_EDIT_STATE or ENV_EDIT_STATE[uid].get('stage') != 'add_env': return
    state = ENV_EDIT_STATE[uid]
    if message.text and message.text.lower() == '/cancel':
        del ENV_EDIT_STATE[uid]; bot.reply_to(message, "✅ Cancelled."); return
    try:
        text = message.text.strip()
        if '=' not in text: raise ValueError()
        key, value = text.split('=', 1)
        key = key.strip(); value = value.strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key): raise ValueError()
        save_script_env_to_db(state['owner_id'], state['file_id'], key, value)
        del ENV_EDIT_STATE[uid]
        bot.reply_to(message, f"✅ Saved `{key}`", parse_mode='Markdown')
    except ValueError:
        msg = bot.send_message(message.chat.id, "⚠️ Invalid format. Use `KEY=VALUE`\n/cancel", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_env_add)

def env_list_callback(call): env_manage_callback(call)

def env_del_callback(call):
    try:
        parts = call.data.split('_', 3)
        if len(parts) < 4: return
        owner_id = int(parts[1]); file_id = parts[2]; key = parts[3]
        if not _check_access(call, owner_id): return
        delete_script_env_key(owner_id, file_id, key)
        bot.answer_callback_query(call.id, f"🗑️ Deleted {key}")
        env_manage_callback(call)
    except Exception: pass

def file_list_callback(call):
    try:
        owner_id, file_id = _parse_owner_file_id(call)
        if not _check_access(call, owner_id): return
        fi = find_file_record(owner_id, file_id)
        if not fi: return
        folder = get_upload_folder(owner_id, file_id)
        bot.answer_callback_query(call.id, "📁 Loading...")
        items = []
        try:
            for item in sorted(os.listdir(folder)):
                fp = os.path.join(folder, item)
                if os.path.isfile(fp): items.append((item, os.path.getsize(fp)))
        except Exception as e: bot.send_message(call.message.chat.id, f"❌ Error: {e}"); return
        if not items: bot.send_message(call.message.chat.id, "📁 Folder is empty."); return
        markup = types.InlineKeyboardMarkup(row_width=1)
        lines = [f"📁 Files in `{fi['file_name']}`:\n"]
        for item, size in items[:30]:
            size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} B"
            lines.append(f"• `{item}` ({size_str})")
            markup.add(types.InlineKeyboardButton(f"📥 {item}", callback_data=f'downloadfile_{owner_id}_{file_id}_{item}'))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data=f'file_{owner_id}_{file_id}'))
        bot.send_message(call.message.chat.id, "\n".join(lines), reply_markup=markup, parse_mode='Markdown')
    except Exception: pass

def download_file_callback(call):
    try:
        parts = call.data.split('_', 3)
        if len(parts) < 4: return
        owner_id = int(parts[1]); file_id = parts[2]; item_name = parts[3]
        if not _check_access(call, owner_id): return
        folder = get_upload_folder(owner_id, file_id)
        fp = os.path.join(folder, item_name)
        if not os.path.exists(fp) or not os.path.isfile(fp): bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True); return
        bot.answer_callback_query(call.id, "📥 Sending...")
        try:
            with open(fp, 'rb') as f: bot.send_document(call.message.chat.id, f, visible_file_name=item_name)
        except Exception as e: bot.send_message(call.message.chat.id, f"❌ Error: {e}")
    except Exception: pass

def speed_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    start = time.time()
    try:
        bot.edit_message_text("🏃 Testing...", chat_id, call.message.message_id)
        bot.send_chat_action(chat_id, 'typing')
        rt = round((time.time() - start) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        lvl = get_user_status_str(user_id)
        bot.answer_callback_query(call.id)
        bot.edit_message_text(f"⚡ Bot Speed:\n\n⏱️ API: {rt} ms\n🚦 Status: {status}\n👤 You: {lvl}\n⏳ Uptime: {get_uptime_str()}", chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
    except Exception: pass

def back_to_main_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    file_limit = get_user_file_limit(user_id)
    current = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
    expiry_info = ""
    if user_id == OWNER_ID: st = "👑 Owner"
    elif user_id in admin_ids: st = "🛡️ Admin"
    elif user_id in user_subscriptions:
        ed = user_subscriptions[user_id].get('expiry')
        if ed and ed > datetime.now():
            st = "⭐ Premium"
            dl = (ed - datetime.now()).days
            expiry_info = f"\n⏳ Expires in: {dl} days"
        else: st = "🆓 Free User (Expired)"
    else: st = "🆓 Free User"
    text = (f"〽️ Welcome back, {call.from_user.first_name}!\n\n"
            f"🆔 ID: `{user_id}`\n🔰 Status: {st}{expiry_info}\n"
            f"📁 Scripts: {current} / {limit_str}\n\n👇 Use buttons or commands.")
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id), parse_mode='Markdown')
    except Exception: pass

# --- Admin callbacks ---
def subscription_management_callback(call):
    bot.answer_callback_query(call.id)
    try: bot.edit_message_text("💳 Subscriptions:", call.message.chat.id, call.message.message_id, reply_markup=create_subscription_menu())
    except Exception: pass

def stats_callback(call):
    bot.answer_callback_query(call.id)
    _logic_statistics(call.message)
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception: pass

def lock_bot_callback(call):
    global bot_locked
    bot_locked = True
    bot.answer_callback_query(call.id, "🔒 Locked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception: pass

def unlock_bot_callback(call):
    global bot_locked
    bot_locked = False
    bot.answer_callback_query(call.id, "🔓 Unlocked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception: pass

def run_all_scripts_callback(call): _logic_run_all_scripts(call)

def broadcast_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send message.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    uid = message.from_user.id
    if uid not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    content = message.text
    if not content and not (message.photo or message.video or message.document or message.sticker or message.voice or message.audio):
        msg = bot.send_message(message.chat.id, "📢 Send broadcast or /cancel.")
        bot.register_next_step_handler(msg, process_broadcast_message); return
    target = len(active_users)
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_broadcast_{message.message_id}"), types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast"))
    preview = content[:1000].strip() if content else "(media)"
    bot.reply_to(message, f"⚠️ Confirm:\n\n```\n{preview}\n```\nTo {target} users. Sure?", reply_markup=markup, parse_mode='Markdown')

def handle_confirm_broadcast(call):
    uid = call.from_user.id
    if uid not in admin_ids: bot.answer_callback_query(call.id, "⚠️ Admin only.", show_alert=True); return
    try:
        orig = call.message.reply_to_message
        if not orig: raise ValueError("No original.")
        txt, pid, vid = None, None, None
        if orig.text: txt = orig.text
        elif orig.photo: pid = orig.photo[-1].file_id
        elif orig.video: vid = orig.video.file_id
        else: raise ValueError("No text/media.")
        bot.answer_callback_query(call.id, "🚀 Starting...")
        bot.edit_message_text(f"📢 Broadcasting to {len(active_users)} users...", call.message.chat.id, call.message.message_id, reply_markup=None)
        threading.Thread(target=execute_broadcast, args=(txt, pid, vid, orig.caption if (pid or vid) else None, call.message.chat.id)).start()
    except Exception as e: bot.edit_message_text("❌ Error.", call.message.chat.id, call.message.message_id, reply_markup=None)

def handle_cancel_broadcast(call):
    bot.answer_callback_query(call.id, "Cancelled.")
    bot.delete_message(call.message.chat.id, call.message.message_id)

def execute_broadcast(txt, pid, vid, caption, admin_chat_id):
    sent = failed = blocked = 0
    start = time.time()
    users = list(active_users)
    total = len(users)
    for i, uid in enumerate(users):
        try:
            if txt: bot.send_message(uid, txt, parse_mode='Markdown')
            elif pid: bot.send_photo(uid, pid, caption=caption, parse_mode='Markdown' if caption else None)
            elif vid: bot.send_video(uid, vid, caption=caption, parse_mode='Markdown' if caption else None)
            sent += 1
        except telebot.apihelper.ApiTelegramException as e:
            ed = str(e).lower()
            if any(s in ed for s in ["blocked", "deactivated", "chat not found", "kicked", "restricted"]): blocked += 1
            elif "flood" in ed or "too many" in ed:
                ra = 5
                m = re.search(r"retry after (\d+)", ed)
                if m: ra = int(m.group(1)) + 1
                time.sleep(ra)
                try:
                    if txt: bot.send_message(uid, txt, parse_mode='Markdown')
                    sent += 1
                except Exception: failed += 1
            else: failed += 1
        except Exception: failed += 1
        if (i + 1) % 25 == 0 and i < total - 1: time.sleep(1.5)
        elif i % 5 == 0: time.sleep(0.2)
    try: bot.send_message(admin_chat_id, f"📢 Done!\n✅ Sent: {sent}\n❌ Failed: {failed}\n🚫 Blocked: {blocked}\n👥 Targets: {total}\n⏱️ {round(time.time()-start, 2)}s")
    except Exception: pass

def admin_panel_callback(call):
    bot.answer_callback_query(call.id)
    try: bot.edit_message_text("👑 Admin Panel", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
    except Exception: pass

def add_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Enter User ID.\n/cancel")
    bot.register_next_step_handler(msg, process_add_admin_id)

def process_add_admin_id(message):
    if message.from_user.id != OWNER_ID: bot.reply_to(message, "⚠️ Owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        nid = int(message.text.strip())
        if nid <= 0 or nid == OWNER_ID: raise ValueError()
        if nid in admin_ids: bot.reply_to(message, "⚠️ Already admin."); return
        add_admin_db(nid)
        bot.reply_to(message, f"✅ Promoted `{nid}`.")
        try: bot.send_message(nid, "🎉 You are now an Admin.")
        except Exception: pass
    except ValueError:
        msg = bot.send_message(message.chat.id, "👑 Invalid ID. /cancel")
        bot.register_next_step_handler(msg, process_add_admin_id)

def remove_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👑 Enter ID to demote.\n/cancel")
    bot.register_next_step_handler(msg, process_remove_admin_id)

def process_remove_admin_id(message):
    if message.from_user.id != OWNER_ID: bot.reply_to(message, "⚠️ Owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        aid = int(message.text.strip())
        if aid == OWNER_ID: raise ValueError()
        if aid not in admin_ids: bot.reply_to(message, "⚠️ Not admin."); return
        if remove_admin_db(aid):
            bot.reply_to(message, f"✅ Demoted `{aid}`.")
            try: bot.send_message(aid, "ℹ️ Removed as Admin.")
            except Exception: pass
    except ValueError:
        msg = bot.send_message(message.chat.id, "👑 Invalid. /cancel")
        bot.register_next_step_handler(msg, process_remove_admin_id)

def list_admins_callback(call):
    bot.answer_callback_query(call.id)
    try:
        s = "\n".join(f"- `{a}` {'(Owner)' if a == OWNER_ID else ''}" for a in sorted(admin_ids))
        if not s: s = "(none)"
        bot.edit_message_text(f"👑 Admins:\n\n{s}", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception: pass

def add_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 `ID days` (e.g., `12345 30`).\n/cancel", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_add_subscription_details)

def process_add_subscription_details(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.split()
        if len(parts) != 2: raise ValueError()
        uid = int(parts[0]); days = int(parts[1])
        if uid <= 0 or days <= 0: raise ValueError()
        cur_exp = user_subscriptions.get(uid, {}).get('expiry')
        start = datetime.now()
        if cur_exp and cur_exp > start: start = cur_exp
        new_exp = start + timedelta(days=days)
        save_subscription(uid, new_exp)
        bot.reply_to(message, f"✅ Sub `{uid}` +{days}d. Expiry: {new_exp:%Y-%m-%d}")
        try: bot.send_message(uid, f"🎉 Sub activated for {days} days!")
        except Exception: pass
    except ValueError:
        msg = bot.send_message(message.chat.id, "💳 `ID days` or /cancel.")
        bot.register_next_step_handler(msg, process_add_subscription_details)

def remove_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter ID.\n/cancel")
    bot.register_next_step_handler(msg, process_remove_subscription_id)

def process_remove_subscription_id(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        if uid <= 0: raise ValueError()
        if uid not in user_subscriptions: bot.reply_to(message, "⚠️ No active sub."); return
        remove_subscription_db(uid)
        bot.reply_to(message, f"✅ Sub removed from `{uid}`.")
        try: bot.send_message(uid, "ℹ️ Your subscription removed.")
        except Exception: pass
    except ValueError:
        msg = bot.send_message(message.chat.id, "💳 Valid ID /cancel.")
        bot.register_next_step_handler(msg, process_remove_subscription_id)

def check_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Enter ID.\n/cancel")
    bot.register_next_step_handler(msg, process_check_subscription_id)

def process_check_subscription_id(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        if uid <= 0: raise ValueError()
        if uid in user_subscriptions:
            ed = user_subscriptions[uid].get('expiry')
            if ed:
                if ed > datetime.now():
                    dl = (ed - datetime.now()).days
                    bot.reply_to(message, f"✅ Active. Expiry: {ed:%Y-%m-%d} ({dl}d left).")
                else:
                    bot.reply_to(message, f"⚠️ Expired."); remove_subscription_db(uid)
        else: bot.reply_to(message, f"ℹ️ No sub for `{uid}`.")
    except ValueError:
        msg = bot.send_message(message.chat.id, "💳 Valid ID /cancel.")
        bot.register_next_step_handler(msg, process_check_subscription_id)

def user_list_callback(call):
    bot.answer_callback_query(call.id)
    users = sorted(list(active_users))
    if not users: text = "👥 No users yet."
    else:
        lines = [f"👥 Total: {len(users)}\n"]
        for uid in users[:50]:
            tag = ""
            if uid == OWNER_ID: tag = " 👑"
            elif uid in admin_ids: tag = " 🛡️"
            elif uid in user_subscriptions and user_subscriptions[uid].get('expiry') > datetime.now(): tag = " ⭐"
            lines.append(f"• `{uid}`{tag} — 📁 {len(user_files.get(uid, []))}")
        if len(users) > 50: lines.append(f"\n... +{len(users)-50}")
        text = "\n".join(lines)
    try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception: pass

def running_bots_callback(call):
    bot.answer_callback_query(call.id)
    running = []
    for sk, info in list(bot_scripts.items()):
        try: s_owner = int(sk.split('_', 1)[0])
        except Exception: continue
        if is_bot_running(s_owner, info['file_id']):
            uptime = datetime.now() - info['start_time']
            res = get_process_resource_usage(sk)
            running.append({'owner': s_owner, 'file': info['file_name'], 'pid': info['process'].pid, 'uptime': str(uptime).split('.')[0], 'cpu': res['cpu'] if res else 0, 'mem': res['mem_mb'] if res else 0})
    if not running: text = "🟢 No bots running."
    else:
        lines = [f"🟢 Running: {len(running)}\n"]
        for r in running[:30]:
            lines.append(f"• 👤 `{r['owner']}` — `{r['file']}`\n   PID: `{r['pid']}` | ⏱️ {r['uptime']} | 🟡 {r['cpu']}% | 🔵 {r['mem']}MB")
        if len(running) > 30: lines.append(f"\n... +{len(running)-30}")
        text = "\n".join(lines)
    try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception: pass

def all_files_callback(call):
    bot.answer_callback_query(call.id)
    total = sum(len(f) for f in user_files.values())
    if total == 0: text = "📁 No files."
    else:
        lines = [f"📁 Total: {total}\n"]
        c = 0
        for uid, files in sorted(user_files.items()):
            if c >= 30: break
            for f in files:
                if c >= 30: break
                lines.append(f"• 👤 `{uid}` — `{f['file_name']}` ({f['file_type']})")
                c += 1
        if total > 30: lines.append(f"\n... +{total-30}")
        text = "\n".join(lines)
    try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception: pass

def stop_all_bots_callback(call):
    bot.answer_callback_query(call.id, "🛑 Stopping...")
    count = 0
    for sk in list(bot_scripts.keys()):
        info = bot_scripts.get(sk)
        if info:
            kill_process_tree(info)
            bot_scripts.pop(sk, None)
            count += 1
    USED_PORTS.clear()
    try: bot.edit_message_text(f"🛑 Stopped {count}.", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
    except Exception: pass

def clean_logs_callback(call):
    bot.answer_callback_query(call.id, "🧹 Cleaning...")
    count = 0
    try:
        for root, dirs, files in os.walk(UPLOAD_BOTS_DIR):
            for f in files:
                if f.endswith('.log'):
                    try: os.remove(os.path.join(root, f)); count += 1
                    except Exception: pass
    except Exception: pass
    try: bot.edit_message_text(f"🧹 Cleaned {count} log(s).", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
    except Exception: pass

def uptime_callback(call):
    bot.answer_callback_query(call.id)
    try: bot.edit_message_text(f"⏱️ Uptime:\n\n🟢 Running: `{get_uptime_str()}`\n🚀 Started: `{BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}`\n🐍 Python: `{sys.version.split()[0]}`\n💻 `{sys.platform}`", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception: pass

def system_info_callback(call):
    bot.answer_callback_query(call.id)
    try:
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_count = psutil.cpu_count() or 1
        cpu_percent = psutil.cpu_percent(interval=0.5)
        text = (f"🖥️ System Info:\n\n🐍 Python: `{sys.version.split()[0]}`\n💻 Platform: `{sys.platform}`\n🔧 CPU Cores: `{cpu_count}`\n🟡 CPU Usage: `{cpu_percent}%`\n\n"
                f"🔵 RAM Total: `{vm.total / (1024**3):.2f} GB`\n🔵 RAM Used: `{vm.used / (1024**3):.2f} GB`\n🔵 RAM Free: `{vm.available / (1024**3):.2f} GB`\n🔵 RAM Usage: `{vm.percent}%`\n\n"
                f"💿 Disk Total: `{disk.total / (1024**3):.2f} GB`\n💿 Disk Used: `{disk.used / (1024**3):.2f} GB`\n💿 Disk Free: `{disk.free / (1024**3):.2f} GB`\n💿 Disk Usage: `{disk.percent}%`\n\n"
                f"⏱️ Uptime: `{get_uptime_str()}`\n👥 Users: `{len(active_users)}`\n📁 Files: `{sum(len(f) for f in user_files.values())}`\n🟢 Running Bots: `{len(bot_scripts)}`\n🔒 Status: `{'Locked' if bot_locked else 'Unlocked'}`")
        try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
        except Exception: bot.send_message(call.message.chat.id, text, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception: pass

def search_user_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🔍 Enter User ID.\n/cancel")
    bot.register_next_step_handler(msg, process_search_user)

def process_search_user(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "⚠️ Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        if uid <= 0: raise ValueError()
        st = get_user_status_str(uid)
        if uid in user_subscriptions:
            e = user_subscriptions[uid].get('expiry')
            if e and e > datetime.now(): st = f"⭐ Premium ({(e - datetime.now()).days}d)"
        files = user_files.get(uid, [])
        rc = sum(1 for f in files if f['file_type'] in ('py', 'js') and is_bot_running(uid, f['file_id']))
        bot.reply_to(message, f"🔍 User Info:\n\n🆔 `{uid}`\n🔰 {st}\n📁 Files: {len(files)}\n🟢 Running: {rc}\n📋 Active: {'✅' if uid in active_users else '❌'}", parse_mode='Markdown')
    except ValueError:
        msg = bot.send_message(message.chat.id, "🔍 Valid ID /cancel.")
        bot.register_next_step_handler(msg, process_search_user)

def backup_now_callback(call):
    bot.answer_callback_query(call.id, "📦 Creating...")
    try:
        zip_path = _create_backup_zip()
        _cleanup_old_backups()
        with open(zip_path, 'rb') as f: bot.send_document(call.message.chat.id, f, visible_file_name=os.path.basename(zip_path), caption="✅ Backup complete.")
    except Exception as e: bot.send_message(call.message.chat.id, f"❌ {e}")

def download_db_callback(call):
    bot.answer_callback_query(call.id, "📥 Preparing...")
    try:
        if not os.path.exists(DATABASE_PATH): bot.send_message(call.message.chat.id, "❌ DB not found."); return
        db_name = f"bot_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        tmp = os.path.join(tempfile.gettempdir(), db_name)
        shutil.copy2(DATABASE_PATH, tmp)
        try:
            with open(tmp, 'rb') as f: bot.send_document(call.message.chat.id, f, visible_file_name=db_name, caption="📊 Database")
        finally:
            try: os.remove(tmp)
            except Exception: pass
    except Exception as e: bot.send_message(call.message.chat.id, f"❌ {e}")

def backup_info_callback(call):
    bot.answer_callback_query(call.id)
    try:
        backups = sorted(glob.glob(os.path.join(BACKUP_DIR, 'hosting_backup_*.zip')), key=os.path.getmtime, reverse=True)
        if not backups: text = "📦 *Backup Info*\n\n❌ No backups yet."
        else:
            lines = [f"📦 *Backup Info*\n🔄 Auto: {'✅ ON' if AUTO_BACKUP_ENABLED else '❌ OFF'}\n⏱️ Every: `{AUTO_BACKUP_INTERVAL_HOURS}h`\n📁 Keep: `{AUTO_BACKUP_KEEP}`\n\n📚 *Recent* ({len(backups)}):\n"]
            for bpath in backups[:5]:
                lines.append(f"• `{os.path.basename(bpath)[:32]}...`\n  📦 {os.path.getsize(bpath)/(1024*1024):.2f} MB | 📅 {datetime.fromtimestamp(os.path.getmtime(bpath)).strftime('%m-%d %H:%M')}")
            if len(backups) > 5: lines.append(f"\n... +{len(backups)-5}")
            text = "\n".join(lines)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.row(types.InlineKeyboardButton("📦 Backup Now", callback_data="backup_now"), types.InlineKeyboardButton("📥 Download DB", callback_data="download_db"))
        markup.row(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
        try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except Exception: bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    except Exception: pass

def restore_info_callback(call):
    bot.answer_callback_query(call.id)
    text = ("♻️ *Restore Guide*\n\n*Step 1:* `/restore` পাঠান\n*Step 2:* আপনার backup file (.zip / .db) পাঠান\n*Step 3:* Bot auto-restore করবে\n*Step 4:* Server restart করুন\n\n"
            f"📁 *Safety Backup:*\n`{SAFETY_DIR}/`\n\n⚠️ Restore এর আগে safety backup নেওয়া হয়।")
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
    try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except Exception: bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

# =============================================================================
# CLEANUP + ZOMBIE
# =============================================================================
def cleanup():
    logger.warning("Shutting down. Cleaning child processes...")
    for sk in list(bot_scripts.keys()):
        info = bot_scripts.get(sk)
        if info: kill_process_tree(info)

atexit.register(cleanup)

def cleanup_zombie_processes():
    try:
        current_pid = os.getpid()
        known_pids = set()
        for info in bot_scripts.values():
            proc = info.get('process')
            if proc and hasattr(proc, 'pid'): known_pids.add(proc.pid)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
            try:
                pid = proc.info['pid']
                if pid in (current_pid, os.getppid()) or pid in known_pids: continue
                if UPLOAD_BOTS_DIR in (proc.info.get('cwd') or ''):
                    logger.warning(f"Killing zombie {pid}")
                    try:
                        proc.terminate()
                        try: proc.wait(timeout=2)
                        except psutil.TimeoutExpired: proc.kill()
                    except Exception: pass
            except (psutil.NoSuchProcess, psutil.AccessDenied): continue
    except Exception: pass

def start_zombie_cleanup_thread():
    def _loop():
        while not _polling_stop.is_set():
            _polling_stop.wait(300)
            if _polling_stop.is_set(): break
            try: cleanup_zombie_processes()
            except Exception: pass
    threading.Thread(target=_loop, name="ZombieCleanup", daemon=True).start()

def _auto_backup_loop():
    if not AUTO_BACKUP_ENABLED: return
    _polling_stop.wait(60)
    while not _polling_stop.is_set():
        try:
            _polling_stop.wait(AUTO_BACKUP_INTERVAL_HOURS * 3600)
            if _polling_stop.is_set(): break
            _create_backup_zip()
            _cleanup_old_backups()
        except Exception: pass

def start_auto_backup_thread():
    threading.Thread(target=_auto_backup_loop, name="AutoBackup", daemon=True).start()

# =============================================================================
# POLLING
# =============================================================================
def _polling_loop():
    try: bot.remove_webhook()
    except Exception: pass
    _polling_stop.wait(2)
    failures = 0
    max_backoff = 120

    while not _polling_stop.is_set():
        try:
            bot.infinity_polling(logger_level=logging.INFO, timeout=25, long_polling_timeout=20, skip_pending=True)
            failures = 0
        except requests.exceptions.ReadTimeout:
            failures += 1
            _polling_stop.wait(min(5 * failures, max_backoff))
        except requests.exceptions.ConnectionError:
            failures += 1
            _polling_stop.wait(min(15 * failures, max_backoff))
        except telebot.apihelper.ApiTelegramException as ae:
            s = str(ae).lower()
            if "webhook" in s or "409" in s:
                try: bot.remove_webhook()
                except Exception: pass
                _polling_stop.wait(3)
            elif "429" in s or "too many" in s: _polling_stop.wait(30)
            else:
                failures += 1
                _polling_stop.wait(min(10 * failures, max_backoff))
        except Exception:
            failures += 1
            _polling_stop.wait(min(30 * failures, max_backoff))

def start_hosting_bot_in_thread():
    global _polling_thread
    if _polling_thread is not None and _polling_thread.is_alive(): return _polling_thread
    _polling_stop.clear()
    _polling_thread = threading.Thread(target=_polling_loop, name="HostingBotPolling", daemon=True)
    _polling_thread.start()
    start_zombie_cleanup_thread()
    start_auto_backup_thread()
    return _polling_thread

def stop_hosting_bot():
    global _polling_thread
    _polling_stop.set()
    if _polling_thread and _polling_thread.is_alive(): _polling_thread.join(timeout=5)

# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    init_db()
    load_data()
    start_hosting_bot_in_thread()
    try:
        while True: time.sleep(3600)
    except KeyboardInterrupt:
        stop_hosting_bot()
        cleanup()
