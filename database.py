import sqlite3
import asyncio
from datetime import date, datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, path="bot.db"):
        self.path = path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path, check_same_thread=False)

    def _init_db(self):
        try:
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
                    CREATE TABLE IF NOT EXISTS user_tasks (
                        user_id INTEGER,
                        task_id INTEGER,
                        completed_date TEXT,
                        PRIMARY KEY (user_id, task_id)
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
        except Exception as e:
            logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")

    async def get_user(self, user_id):
        def _get():
            with self._connect() as conn:
                return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return await asyncio.to_thread(_get)

    async def add_user(self, user_id, username, first_name, referred_by=None):
        def _add():
            with self._connect() as conn:
                code = f"{user_id}_{uuid.uuid4().hex[:6]}"
                try:
                    conn.execute('''INSERT OR IGNORE INTO users 
                                    (user_id, username, first_name, referral_code, referred_by, joined_date, last_analysis_date)
                                    VALUES (?,?,?,?,?,?,?)''',
                                 (user_id, username, first_name, code, referred_by, date.today().isoformat(), date.today().isoformat()))
                    if referred_by:
                        conn.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id, join_date) VALUES (?,?,?)",
                                     (referred_by, user_id, date.today().isoformat()))
                except Exception as e:
                    logger.error(f"خطأ في إضافة المستخدم {user_id}: {e}")
        await asyncio.to_thread(_add)

    async def update_language(self, user_id, lang):
        def _upd():
            try:
                with self._connect() as conn:
                    conn.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
            except Exception as e:
                logger.error(f"خطأ في تحديث اللغة: {e}")
        await asyncio.to_thread(_upd)

    async def get_daily_analysis_count(self, user_id):
        """ترجع عدد التحليلات المتبقية اليوم (للمستخدمين العاديين)"""
        user = await self.get_user(user_id)
        if not user:
            return 0
        
        today = date.today().isoformat()
        last_analysis_date = user[5]
        
        # إذا كان آخر تحليل في يوم مختلف، أعد التعيين
        if last_analysis_date != today:
            await self.reset_daily_analysis(user_id)
            return 3  # 3 تحليلات مجانية يومياً
        
        used = user[4]  # عدد التحليلات المستخدمة
        remaining = max(0, 3 - used)
        return remaining

    async def reset_daily_analysis(self, user_id):
        def _rst():
            try:
                with self._connect() as conn:
                    conn.execute("UPDATE users SET daily_analysis_count=0, last_analysis_date=? WHERE user_id=?",
                                 (date.today().isoformat(), user_id))
            except Exception as e:
                logger.error(f"خطأ في إعادة تعيين التحليلات: {e}")
        await asyncio.to_thread(_rst)

    async def increment_analysis(self, user_id):
        def _inc():
            try:
                with self._connect() as conn:
                    conn.execute("UPDATE users SET daily_analysis_count=daily_analysis_count+1, last_analysis_date=? WHERE user_id=?",
                                 (date.today().isoformat(), user_id))
            except Exception as e:
                logger.error(f"خطأ في زيادة التحليلات: {e}")
        await asyncio.to_thread(_inc)

    async def set_vip(self, user_id, days):
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        def _set():
            try:
                with self._connect() as conn:
                    conn.execute("UPDATE users SET is_vip=1, vip_expiry=? WHERE user_id=?", (expiry, user_id))
            except Exception as e:
                logger.error(f"خطأ في تعيين VIP: {e}")
        await asyncio.to_thread(_set)

    async def is_user_vip(self, user_id):
        """تحقق من أن المستخدم VIP نشط"""
        user = await self.get_user(user_id)
        if not user:
            return False
        
        is_vip = user[6]  # is_vip column
        vip_expiry = user[7]  # vip_expiry column
        
        if not is_vip:
            return False
        
        if vip_expiry and datetime.fromisoformat(vip_expiry) < datetime.now():
            # انتهت صلاحية VIP
            await self.expire_vip(user_id)
            return False
        
        return True

    async def expire_vip(self, user_id):
        def _expire():
            try:
                with self._connect() as conn:
                    conn.execute("UPDATE users SET is_vip=0, vip_expiry=NULL WHERE user_id=?", (user_id,))
            except Exception as e:
                logger.error(f"خطأ في انتهاء VIP: {e}")
        await asyncio.to_thread(_expire)

    async def check_vip_expired(self):
        now = datetime.now().isoformat()
        def _check():
            try:
                with self._connect() as conn:
                    conn.execute("UPDATE users SET is_vip=0 WHERE vip_expiry<? AND is_vip=1", (now,))
            except Exception as e:
                logger.error(f"خطأ في فحص انتهاء VIP: {e}")
        await asyncio.to_thread(_check)

    async def get_active_tasks(self):
        def _get():
            try:
                with self._connect() as conn:
                    return conn.execute("SELECT * FROM tasks WHERE is_active=1 AND completed_users<max_users").fetchall()
            except Exception as e:
                logger.error(f"خطأ في الحصول على المهام: {e}")
                return []
        return await asyncio.to_thread(_get)

    async def has_completed_task(self, user_id, task_id):
        """تحقق من أن المستخدم أكمل المهمة من قبل"""
        def _check():
            with self._connect() as conn:
                result = conn.execute("SELECT * FROM user_tasks WHERE user_id=? AND task_id=?", 
                                     (user_id, task_id)).fetchone()
                return result is not None
        return await asyncio.to_thread(_check)

    async def add_task(self, title_ar, title_en, link, reward_type, reward_value, max_users):
        def _add():
            try:
                with self._connect() as conn:
                    conn.execute('''INSERT INTO tasks (title_ar, title_en, link, reward_type, reward_value, max_users)
                                    VALUES (?,?,?,?,?,?)''',
                                 (title_ar, title_en, link, reward_type, reward_value, max_users))
            except Exception as e:
                logger.error(f"خطأ في إضافة المهمة: {e}")
        await asyncio.to_thread(_add)

    async def complete_task(self, task_id, user_id, reward_type, reward_value):
        """انتهت المهمة للمستخدم وأضف المكافأة"""
        def _complete():
            try:
                with self._connect() as conn:
                    # تحقق من أن المستخدم لم ينهِ المهمة من قبل
                    existing = conn.execute("SELECT * FROM user_tasks WHERE user_id=? AND task_id=?",
                                           (user_id, task_id)).fetchone()
                    if existing:
                        return False  # تم إنهاء المهمة من قبل
                    
                    # سجل إكمال المهمة
                    conn.execute("INSERT INTO user_tasks (user_id, task_id, completed_date) VALUES (?,?,?)",
                                (user_id, task_id, date.today().isoformat()))
                    
                    # زيادة عدد المستخدمين الذين أنهوا المهمة
                    conn.execute("UPDATE tasks SET completed_users=completed_users+1 WHERE id=?", (task_id,))
                    
                    # أضف المكافأة
                    if reward_type == 'analysis':
                        conn.execute("UPDATE users SET daily_analysis_count=daily_analysis_count+? WHERE user_id=?",
                                     (reward_value, user_id))
                    elif reward_type == 'stars':
                        conn.execute("UPDATE users SET stars_balance=stars_balance+? WHERE user_id=?",
                                     (reward_value, user_id))
                    
                    return True
            except Exception as e:
                logger.error(f"خطأ في إنهاء المهمة: {e}")
                return False
        return await asyncio.to_thread(_complete)

    async def give_referral_reward_if_due(self, referrer_id):
        def _give():
            try:
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
            except Exception as e:
                logger.error(f"خطأ في منح مكافأة الإحالة: {e}")
        await asyncio.to_thread(_give)

    async def add_payment(self, user_id, amount, currency, package, txid):
        def _add():
            try:
                with self._connect() as conn:
                    conn.execute('''INSERT INTO payments (user_id, amount, currency, package, date, transaction_id)
                                    VALUES (?,?,?,?,?,?)''',
                                 (user_id, amount, currency, package, datetime.now().isoformat(), txid))
            except Exception as e:
                logger.error(f"خطأ في إضافة الدفع: {e}")
        await asyncio.to_thread(_add)

    async def add_support_message(self, user_id, message_text):
        def _add():
            try:
                with self._connect() as conn:
                    conn.execute("INSERT INTO support_messages (user_id, message_text, timestamp) VALUES (?,?,?)",
                                 (user_id, message_text, datetime.now().isoformat()))
            except Exception as e:
                logger.error(f"خطأ في إضافة رسالة الدعم: {e}")
        await asyncio.to_thread(_add)

    async def get_unreplied_support(self):
        def _get():
            try:
                with self._connect() as conn:
                    return conn.execute("SELECT id, user_id, message_text FROM support_messages WHERE replied=0 ORDER BY timestamp DESC").fetchall()
            except Exception as e:
                logger.error(f"خطأ في الحصول على رسائل الدعم: {e}")
                return []
        return await asyncio.to_thread(_get)

    async def mark_support_replied(self, msg_id):
        def _upd():
            try:
                with self._connect() as conn:
                    conn.execute("UPDATE support_messages SET replied=1 WHERE id=?", (msg_id,))
            except Exception as e:
                logger.error(f"خطأ في وضع علامة الرد: {e}")
        await asyncio.to_thread(_upd)

    async def get_all_users(self):
        """احصل على جميع المستخدمين للبث"""
        def _get():
            try:
                with self._connect() as conn:
                    return conn.execute("SELECT user_id FROM users").fetchall()
            except Exception as e:
                logger.error(f"خطأ في الحصول على المستخدمين: {e}")
                return []
        return await asyncio.to_thread(_get)

db = Database()
