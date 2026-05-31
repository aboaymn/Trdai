import sqlite3
import asyncio
from datetime import date, datetime, timedelta
import uuid

class Database:
    def __init__(self, path="bot.db"):
        self.path = path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path, check_same_thread=False)

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language TEXT DEFAULT 'ar',
                    daily_analysis_count INTEGER DEFAULT 0,
                    last_analysis_date TEXT,
                    is_vip INTEGER DEFAULT 0,
                    vip_expiry TEXT,
                    stars_balance INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    joined_date TEXT
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title_ar TEXT,
                    title_en TEXT,
                    link TEXT,
                    reward_type TEXT,
                    reward_value INTEGER,
                    max_users INTEGER,
                    completed_users INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    join_date TEXT,
                    reward_given INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    currency TEXT,
                    package TEXT,
                    date TEXT,
                    transaction_id TEXT
                );
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS support_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_text TEXT,
                    replied INTEGER DEFAULT 0,
                    timestamp TEXT
                );
            ''')

    async def get_user(self, user_id):
        def _get():
            with self._connect() as conn:
                return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return await asyncio.to_thread(_get)

    async def add_user(self, user_id, username, first_name, referred_by=None):
        def _add():
            with self._connect() as conn:
                code = f"{user_id}_{uuid.uuid4().hex[:6]}"
                conn.execute('''INSERT OR IGNORE INTO users (user_id, username, first_name, referral_code, referred_by, joined_date)
                                VALUES (?,?,?,?,?,?)''',
                             (user_id, username, first_name, code, referred_by, date.today().isoformat()))
                if referred_by:
                    conn.execute("INSERT INTO referrals (referrer_id, referred_id, join_date) VALUES (?,?,?)",
                                 (referred_by, user_id, date.today().isoformat()))
        await asyncio.to_thread(_add)

    async def update_language(self, user_id, lang):
        def _upd():
            with self._connect() as conn:
                conn.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        await asyncio.to_thread(_upd)

    async def get_daily_analysis_count(self, user_id):
        user = await self.get_user(user_id)
        if not user:
            return 0
        today = date.today().isoformat()
        if user[4] != today:
            await self.reset_daily_analysis(user_id)
            return 0
        return user[3]

    async def reset_daily_analysis(self, user_id):
        def _rst():
            with self._connect() as conn:
                conn.execute("UPDATE users SET daily_analysis_count=0, last_analysis_date=? WHERE user_id=?",
                             (date.today().isoformat(), user_id))
        await asyncio.to_thread(_rst)

    async def increment_analysis(self, user_id):
        def _inc():
            with self._connect() as conn:
                conn.execute("UPDATE users SET daily_analysis_count=daily_analysis_count+1, last_analysis_date=? WHERE user_id=?",
                             (date.today().isoformat(), user_id))
        await asyncio.to_thread(_inc)

    async def set_vip(self, user_id, days):
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        def _set():
            with self._connect() as conn:
                conn.execute("UPDATE users SET is_vip=1, vip_expiry=? WHERE user_id=?", (expiry, user_id))
        await asyncio.to_thread(_set)

    async def check_vip_expired(self):
        now = datetime.now().isoformat()
        def _check():
            with self._connect() as conn:
                conn.execute("UPDATE users SET is_vip=0 WHERE vip_expiry<? AND is_vip=1", (now,))
        await asyncio.to_thread(_check)

    async def get_active_tasks(self):
        def _get():
            with self._connect() as conn:
                return conn.execute("SELECT * FROM tasks WHERE is_active=1 AND completed_users<max_users").fetchall()
        return await asyncio.to_thread(_get)

    async def add_task(self, title_ar, title_en, link, reward_type, reward_value, max_users):
        def _add():
            with self._connect() as conn:
                conn.execute('''INSERT INTO tasks (title_ar, title_en, link, reward_type, reward_value, max_users)
                                VALUES (?,?,?,?,?,?)''',
                             (title_ar, title_en, link, reward_type, reward_value, max_users))
        await asyncio.to_thread(_add)

    async def complete_task(self, task_id, user_id, reward_type, reward_value):
        def _complete():
            with self._connect() as conn:
                conn.execute("UPDATE tasks SET completed_users=completed_users+1 WHERE id=?", (task_id,))
                if reward_type == 'analysis':
                    conn.execute("UPDATE users SET daily_analysis_count=daily_analysis_count+? WHERE user_id=?",
                                 (reward_value, user_id))
                elif reward_type == 'stars':
                    conn.execute("UPDATE users SET stars_balance=stars_balance+? WHERE user_id=?",
                                 (reward_value, user_id))
        await asyncio.to_thread(_complete)

    async def give_referral_reward_if_due(self, referrer_id):
        def _give():
            with self._connect() as conn:
                refs = conn.execute('''SELECT r.referred_id, r.join_date, u.is_vip
                                       FROM referrals r JOIN users u ON r.referred_id=u.user_id
                                       WHERE r.referrer_id=? AND r.reward_given=0''',
                                    (referrer_id,)).fetchall()
                for ref in refs:
                    referred_id, join_date_str, is_vip = ref
                    days = (date.today() - date.fromisoformat(join_date_str)).days
                    if days >= 10 and is_vip:
                        conn.execute("UPDATE users SET daily_analysis_count=daily_analysis_count+10 WHERE user_id=?",
                                     (referrer_id,))
                        conn.execute("UPDATE referrals SET reward_given=1 WHERE referred_id=?", (referred_id,))
        await asyncio.to_thread(_give)

    async def add_payment(self, user_id, amount, currency, package, txid):
        def _add():
            with self._connect() as conn:
                conn.execute('''INSERT INTO payments (user_id, amount, currency, package, date, transaction_id)
                                VALUES (?,?,?,?,?,?)''',
                             (user_id, amount, currency, package, datetime.now().isoformat(), txid))
        await asyncio.to_thread(_add)

    async def add_support_message(self, user_id, message_text):
        def _add():
            with self._connect() as conn:
                conn.execute("INSERT INTO support_messages (user_id, message_text, timestamp) VALUES (?,?,?)",
                             (user_id, message_text, datetime.now().isoformat()))
        await asyncio.to_thread(_add)

    async def get_unreplied_support(self):
        def _get():
            with self._connect() as conn:
                return conn.execute("SELECT id, user_id, message_text FROM support_messages WHERE replied=0").fetchall()
        return await asyncio.to_thread(_get)

    async def mark_support_replied(self, msg_id):
        def _upd():
            with self._connect() as conn:
                conn.execute("UPDATE support_messages SET replied=1 WHERE id=?", (msg_id,))
        await asyncio.to_thread(_upd)

db = Database()