import os
import random
import hashlib
import time
import json
import threading
from datetime import datetime, timedelta
from threading import Lock
import telebot
import psycopg2
import psycopg2.extras
from psycopg2 import pool
import pytz

# ===== КОНФИГ =====
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("❌ Токен не найден!")

ADMIN_ID = int(os.getenv('ADMIN_ID', 6573154279))
bot = telebot.TeleBot(TOKEN)

# ===== ЧАСОВОЙ ПОЯС ЕКБ =====
TIMEZONE = pytz.timezone('Asia/Yekaterinburg')

def get_current_time():
    return datetime.now(TIMEZONE)

# ===== ПУЛ СОЕДИНЕНИЙ =====
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не найден!")

try:
    db_pool = pool.SimpleConnectionPool(1, 10, DATABASE_URL)
    print('✅ Пул соединений создан')
except Exception as e:
    print(f'❌ Ошибка создания пула: {e}')
    db_pool = None

def get_db_connection():
    if db_pool:
        return db_pool.getconn()
    return psycopg2.connect(DATABASE_URL)

def release_db_connection(conn):
    if db_pool:
        db_pool.putconn(conn)
    else:
        conn.close()

# ===== КЭШ =====
user_cache = {}
cache_lock = Lock()
CACHE_TTL = 15

def get_cached_user(user_id):
    with cache_lock:
        if user_id in user_cache:
            data, timestamp = user_cache[user_id]
            if time.time() - timestamp < CACHE_TTL:
                return data
    user = get_user(user_id)
    with cache_lock:
        user_cache[user_id] = (user, time.time())
    return user

def invalidate_cache(user_id):
    with cache_lock:
        if user_id in user_cache:
            del user_cache[user_id]

# ===== ФУНКЦИИ БД =====
def get_user(user_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        cur.close()
        return user
    finally:
        release_db_connection(conn)

def get_user_by_nick(nick):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM users WHERE game_nick = %s', (nick,))
        user = cur.fetchone()
        cur.close()
        return user
    finally:
        release_db_connection(conn)

def update_user(user_id, **kwargs):
    if not kwargs:
        return
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        set_clause = ', '.join([f'{key} = %s' for key in kwargs.keys()])
        values = list(kwargs.values()) + [user_id]
        cur.execute(f'UPDATE users SET {set_clause} WHERE id = %s', values)
        conn.commit()
        cur.close()
        invalidate_cache(user_id)
    finally:
        release_db_connection(conn)

def create_user(user_id, nick, hashed_password, reg_date):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO users (id, game_nick, password, reg_date, is_logged_in, balance, cases_opened, secret_items)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, nick, hashed_password, reg_date, 1, 0, 0, 0))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f'❌ Ошибка создания пользователя: {e}')
        return False
    finally:
        release_db_connection(conn)

def user_exists(user_id):
    return get_cached_user(user_id) is not None

def is_logged_in(user_id):
    user = get_cached_user(user_id)
    return user and user['is_logged_in'] == 1

def is_banned(user_id):
    user = get_cached_user(user_id)
    return user and user.get('is_banned', 0) == 1

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    user = get_cached_user(user_id)
    if not user:
        return False
    return user.get('admin_level', 0) >= 1

# ===== СТАТУСЫ (30 штук) =====
def get_status(balance):
    if balance >= 1000000000:
        return '🌌✨ Легенда Вселенной'
    elif balance >= 50000000:
        return '⚛️ Абсолют'
    elif balance >= 10000000:
        return '∞ Бесконечность'
    elif balance >= 5000000:
        return '🌠 Вселенная'
    elif balance >= 1000000:
        return '🌌 Космос'
    elif balance >= 500000:
        return '♾️ Бессмертный'
    elif balance >= 250000:
        return '✨ Творец'
    elif balance >= 100000:
        return '⚡ Бог'
    elif balance >= 70000:
        return '🔥 Миф'
    elif balance >= 50000:
        return '🌟 Легенда'
    elif balance >= 30000:
        return '🗿 Титан'
    elif balance >= 20000:
        return '🏯 Император'
    elif balance >= 15000:
        return '👑 Король'
    elif balance >= 10000:
        return '⚜️ Князь'
    elif balance >= 7000:
        return '🏛️ Герцог'
    elif balance >= 5000:
        return '👑 Граф'
    elif balance >= 3000:
        return '🏰 Барон'
    elif balance >= 2000:
        return '👔 Магнат'
    elif balance >= 1500:
        return '💼 Инвестор'
    elif balance >= 1200:
        return '📈 Бизнесмен'
    elif balance >= 900:
        return '🏢 Предприниматель'
    elif balance >= 700:
        return '💪 Трудяга'
    elif balance >= 500:
        return '⚖️ Середняк'
    elif balance >= 400:
        return '🏦 Копилка'
    elif balance >= 300:
        return '🔨 Работяга'
    elif balance >= 200:
        return '📝 Стажёр'
    elif balance >= 100:
        return '🎓 Студент'
    elif balance >= 50:
        return '🌱 Новичок'
    elif balance >= 10:
        return '🕊️ Бедняк'
    elif balance >= 1:
        return '🥺 Попрошайка'
    else:
        return '🏚️ Бездомный'

# ============================================================
# УНИКАЛЬНЫЙ СТАТУС "ЛЕГЕНДА ВСЕЛЕННОЙ"
# ============================================================

def check_unique_status(user_id):
    """Проверяет, достиг ли игрок 1 лярда монет"""
    user = get_user(user_id)
    if not user:
        return
    
    balance = user['balance']
    
    if balance >= 1000000000:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute('SELECT id FROM users WHERE balance >= 1000000000 AND id != %s', (user_id,))
            existing = cur.fetchone()
            cur.close()
            
            if not existing:
                bot.send_message(user_id, 
                    '🌌✨ **ПОЗДРАВЛЯЮ!**\n\n'
                    'Вы достигли 1 000 000 000 монет!\n'
                    'Вы получили уникальный статус: **Легенда Вселенной**! 🏆\n\n'
                    'Вы первый и пока единственный, кто достиг этого уровня!')
                
                notify_all_players(f'🌌✨ {user["game_nick"]} достиг 1 000 000 000 монет и получил уникальный статус **"Легенда Вселенной"**!')
            else:
                bot.send_message(user_id, 
                    '🌌✨ **ПОЗДРАВЛЯЮ!**\n\n'
                    'Вы достигли 1 000 000 000 монет!\n'
                    'К сожалению, статус "Легенда Вселенной" уже занят.\n\n'
                    'Но вы можете стать первым, кто достигнет 2 000 000 000 монет!')
        finally:
            release_db_connection(conn)

# ============================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================

def init_db():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                game_nick TEXT UNIQUE,
                password TEXT,
                balance INTEGER DEFAULT 0,
                reg_date TEXT,
                is_logged_in INTEGER DEFAULT 0,
                cases_opened INTEGER DEFAULT 0,
                secret_items INTEGER DEFAULT 0,
                admin_level INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                nick TEXT,
                message TEXT,
                timestamp TEXT
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS muted_users (
                user_id BIGINT PRIMARY KEY,
                muted_until TEXT
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS boss (
                id SERIAL PRIMARY KEY,
                hp INTEGER DEFAULT 10000,
                max_hp INTEGER DEFAULT 10000,
                start_time TEXT,
                end_time TEXT,
                active INTEGER DEFAULT 0,
                participants TEXT DEFAULT '[]'
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS boss_leaderboard (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                nick TEXT,
                damage INTEGER DEFAULT 0,
                position INTEGER DEFAULT 0,
                reward_claimed INTEGER DEFAULT 0
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                maintenance_mode INTEGER DEFAULT 0,
                maintenance_until TEXT DEFAULT NULL
            )
        ''')
        cur.execute('INSERT INTO settings (id) VALUES (1) ON CONFLICT DO NOTHING')
        
        conn.commit()
        cur.close()
        print('✅ База данных готова')
    finally:
        release_db_connection(conn)

init_db()

# ============================================================
# КЛАВИАТУРЫ
# ============================================================

auth_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
auth_keyboard.add('🔑 Войти', '✨ Зарегистрироваться')

main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_keyboard.add('👤 Профиль', '💰 Баланс')
main_keyboard.add('📊 Топ игроков', '🎁 Кейсы')
main_keyboard.add('🏆 Топ кейсов', '⭐ Топ секретов')
main_keyboard.add('💬 Чат', '📊 Статус')
main_keyboard.add('🚪 Выйти')

creator_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
creator_keyboard.add('💰 Изменить баланс', '👤 Удалить аккаунт')
creator_keyboard.add('📊 Статистика сервера', '👥 Список игроков')
creator_keyboard.add('🐉 Создать босса', '📊 Статус босса')
creator_keyboard.add('⚙️ Управление боссом', '🏆 Топ урона боссу')
creator_keyboard.add('⚔️ Лидерборд босса', '🗑️ Очистить лидерборд')
creator_keyboard.add('🚫 Убрать из лидерборда', '🔇 Замутить')
creator_keyboard.add('🔊 Размутить', '🔄 Сбросить Легенду')
creator_keyboard.add('⬅️ Назад')

# ============================================================
# КЕЙСЫ
# ============================================================

CASES = {
    1: {
        'name': 'Денежный',
        'emoji': '💰',
        'price': 100,
        'rewards': [
            {'type': 'coins', 'min': 100, 'max': 300, 'chance': 50},
            {'type': 'coins', 'min': 300, 'max': 600, 'chance': 30},
            {'type': 'coins', 'min': 600, 'max': 900, 'chance': 15},
            {'type': 'coins', 'min': 900, 'max': 1000, 'chance': 4.9},
            {'type': 'secret_jackpot', 'min': 5000, 'max': 5000, 'chance': 0.1},
        ]
    }
}

# Фото для кейсов
CASE_PHOTO_URL = 'https://i.ibb.co/LzXf1Vkg/3-20260803162303.png'

# ============================================================
# ЧАТ
# ============================================================

def save_chat_message(user_id, nick, message):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO chat_messages (user_id, nick, message, timestamp)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, nick, message, get_current_time().strftime('%H:%M')))
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

def get_chat_messages(limit=20):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT user_id, nick, message, timestamp FROM chat_messages ORDER BY id DESC LIMIT %s
        ''', (limit,))
        messages = cur.fetchall()
        cur.close()
        
        formatted = []
        for user_id, nick, message, timestamp in messages[::-1]:
            if user_id == ADMIN_ID:
                display_name = f'👑 **Создатель**'
            elif is_admin(user_id):
                display_name = f'⭐ **{nick}** (Админ)'
            else:
                display_name = f'**{nick}**'
            
            formatted.append((display_name, message, timestamp))
        
        return formatted
    finally:
        release_db_connection(conn)

def clear_chat():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM chat_messages')
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

def is_muted(user_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT muted_until FROM muted_users WHERE user_id = %s', (user_id,))
        result = cur.fetchone()
        if not result:
            return False
        muted_until = datetime.fromisoformat(result[0])
        if get_current_time() > muted_until:
            cur.execute('DELETE FROM muted_users WHERE user_id = %s', (user_id,))
            conn.commit()
            return False
        return True
    finally:
        release_db_connection(conn)

def mute_user(user_id, minutes):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        muted_until = (get_current_time() + timedelta(minutes=minutes)).isoformat()
        cur.execute('''
            INSERT INTO muted_users (user_id, muted_until)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET muted_until = %s
        ''', (user_id, muted_until, muted_until))
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

def unmute_user(user_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM muted_users WHERE user_id = %s', (user_id,))
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

def notify_chat_message(user_id, nick, message):
    if user_id == ADMIN_ID:
        sender_display = f'👑 **Создатель**'
        notify_all = True
    elif is_admin(user_id):
        sender_display = f'⭐ **{nick}** (Админ)'
        notify_all = True
    else:
        sender_display = f'**{nick}**'
        notify_all = False
    
    if notify_all:
        notify_all_players(f'💬 {sender_display}: {message}')
    else:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute('SELECT id FROM users WHERE admin_level > 0 OR id = %s', (ADMIN_ID,))
            admins = cur.fetchall()
            cur.close()
            
            for admin_id in admins:
                try:
                    bot.send_message(admin_id[0], f'💬 {sender_display} написал в чат:\n{message}')
                except:
                    pass
        finally:
            release_db_connection(conn)

# ============================================================
# БОСС
# ============================================================

def create_boss():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        now = get_current_time()
        end_time = now + timedelta(hours=1)
        cur.execute('''
            INSERT INTO boss (hp, max_hp, start_time, end_time, active)
            VALUES (%s, %s, %s, %s, %s)
        ''', (10000, 10000, now.isoformat(), end_time.isoformat(), 1))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f'❌ Ошибка создания босса: {e}')
        return False
    finally:
        release_db_connection(conn)

def get_boss():
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM boss WHERE active = 1 ORDER BY id DESC LIMIT 1')
        boss = cur.fetchone()
        cur.close()
        return boss
    finally:
        release_db_connection(conn)

def hit_boss(damage=1):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('UPDATE boss SET hp = hp - %s WHERE active = 1', (damage,))
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

def get_boss_participants():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT participants FROM boss WHERE active = 1 ORDER BY id DESC LIMIT 1')
        result = cur.fetchone()
        cur.close()
        if result and result[0]:
            return json.loads(result[0])
        return []
    finally:
        release_db_connection(conn)

def add_boss_participant(user_id, nick):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT participants FROM boss WHERE active = 1 ORDER BY id DESC LIMIT 1')
        result = cur.fetchone()
        participants = json.loads(result[0]) if result and result[0] else []
        found = False
        for p in participants:
            if p['id'] == user_id:
                p['hits'] += 1
                found = True
                break
        if not found:
            participants.append({'id': user_id, 'nick': nick, 'hits': 1})
        cur.execute('UPDATE boss SET participants = %s WHERE active = 1', (json.dumps(participants),))
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

def finish_boss():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        cur.execute('SELECT user_id, nick FROM boss_leaderboard ORDER BY damage DESC LIMIT 1')
        top = cur.fetchone()
        
        if top:
            user_id, nick = top
            cur.execute('SELECT balance FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()
            if user:
                new_balance = user[0] + 500000
                cur.execute('UPDATE users SET balance = %s WHERE id = %s', (new_balance, user_id))
                cur.execute('UPDATE boss_leaderboard SET reward_claimed = 1 WHERE user_id = %s', (user_id,))
                bot.send_message(user_id, f'🎉 *ПОЗДРАВЛЯЮ!*\nВы заняли 1 место по урону боссу и получили 500 000 монет!')
                notify_all_players(f'🏆 {nick} занял 1 место по урону боссу и получил 500 000 монет!')
        
        cur.execute('UPDATE boss SET active = 0 WHERE active = 1')
        conn.commit()
        cur.close()
        
        clear_boss_leaderboard()
    finally:
        release_db_connection(conn)

def get_boss_remaining_time():
    boss = get_boss()
    if not boss:
        return '0 мин'
    end_time = datetime.fromisoformat(boss['end_time'])
    remaining = end_time - get_current_time()
    return f'{remaining.seconds // 60} минут'

# ============================================================
# БОСС ЛИДЕРБОРД
# ============================================================

def add_boss_damage(user_id, nick, damage=1):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id FROM boss_leaderboard WHERE user_id = %s', (user_id,))
        result = cur.fetchone()
        if result:
            cur.execute('UPDATE boss_leaderboard SET damage = damage + %s WHERE user_id = %s', (damage, user_id))
        else:
            cur.execute('INSERT INTO boss_leaderboard (user_id, nick, damage) VALUES (%s, %s, %s)', (user_id, nick, damage))
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

def get_boss_leaderboard():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT user_id, nick, damage, reward_claimed FROM boss_leaderboard ORDER BY damage DESC')
        leaderboard = cur.fetchall()
        cur.close()
        return leaderboard
    finally:
        release_db_connection(conn)

def clear_boss_leaderboard():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM boss_leaderboard')
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

def remove_from_boss_leaderboard(user_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM boss_leaderboard WHERE user_id = %s', (user_id,))
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

def get_boss_leaderboard_top():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT user_id, nick, damage FROM boss_leaderboard ORDER BY damage DESC LIMIT 1')
        top = cur.fetchone()
        cur.close()
        return top
    finally:
        release_db_connection(conn)

# ============================================================
# УВЕДОМЛЕНИЯ
# ============================================================

def notify_all_players(text, parse_mode='Markdown'):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE is_logged_in = 1')
        users = cur.fetchall()
        cur.close()
    finally:
        release_db_connection(conn)
    
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f'📢 {text}', parse_mode=parse_mode)
            sent += 1
        except:
            pass
    
    try:
        bot.send_message(ADMIN_ID, f'📢 [УВЕДОМЛЕНИЕ] {text}')
    except:
        pass
    
    return sent

# ============================================================
# ТЕХНИЧЕСКИЙ ПЕРЕРЫВ
# ============================================================

def is_maintenance_mode():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT maintenance_mode, maintenance_until FROM settings LIMIT 1')
        result = cur.fetchone()
        cur.close()
        
        if not result:
            return False
        
        mode, until = result
        if mode == 1 and until:
            until_time = datetime.fromisoformat(until)
            if get_current_time() > until_time:
                cur = conn.cursor()
                cur.execute('UPDATE settings SET maintenance_mode = 0, maintenance_until = NULL')
                conn.commit()
                cur.close()
                return False
            return True
        return False
    finally:
        release_db_connection(conn)

def get_maintenance_time():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT maintenance_until FROM settings LIMIT 1')
        result = cur.fetchone()
        cur.close()
        if result and result[0]:
            until = datetime.fromisoformat(result[0])
            remaining = until - get_current_time()
            return remaining.seconds // 60
        return 0
    finally:
        release_db_connection(conn)

def set_maintenance_mode(minutes):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if minutes > 0:
            until = (get_current_time() + timedelta(minutes=minutes)).isoformat()
            cur.execute('UPDATE settings SET maintenance_mode = 1, maintenance_until = %s', (until,))
        else:
            cur.execute('UPDATE settings SET maintenance_mode = 0, maintenance_until = NULL')
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

# ============================================================
# АВТОРИЗАЦИЯ
# ============================================================

@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Вы заблокированы.')
        return
    
    if user_exists(user_id):
        if is_logged_in(user_id):
            user = get_cached_user(user_id)
            bot.send_message(msg.chat.id, f'👋 Снова здесь, {user["game_nick"]}!', reply_markup=main_keyboard)
        else:
            bot.send_message(msg.chat.id, '🔐 У вас уже есть аккаунт. Войдите.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '👋 Добро пожаловать! Зарегистрируйтесь или войдите.', reply_markup=auth_keyboard)

@bot.message_handler(func=lambda m: m.text == '🔑 Войти')
def login_start(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not user_exists(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не зарегистрированы. Нажмите "Зарегистрироваться".')
        return
    
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Вы заблокированы.')
        return
    
    if is_logged_in(user_id):
        bot.send_message(msg.chat.id, '✅ Вы уже авторизованы!', reply_markup=main_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🔐 Введите ваш игровой ник:')
    bot.register_next_step_handler(msg, login_nick)

def login_nick(msg):
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    
    if not user:
        bot.send_message(msg.chat.id, '❌ Игрок с таким ником не найден.')
        return
    
    bot.send_message(msg.chat.id, '🔑 Введите пароль:')
    bot.register_next_step_handler(msg, login_password, nick)

def login_password(msg, nick):
    password = msg.text.strip()
    user = get_user_by_nick(nick)
    
    if not user or user['password'] != hash_password(password):
        bot.send_message(msg.chat.id, '❌ Неверный пароль.')
        return
    
    update_user(user['id'], is_logged_in=1)
    bot.send_message(msg.chat.id, f'✅ Добро пожаловать, {nick}!', reply_markup=main_keyboard)

@bot.message_handler(func=lambda m: m.text == '✨ Зарегистрироваться')
def register_start(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if user_exists(user_id):
        bot.send_message(msg.chat.id, '❌ У вас уже есть аккаунт! Войдите через "Войти".')
        return
    
    bot.send_message(msg.chat.id, '📝 Придумайте игровой ник (от 2 до 20 символов, без пробелов):')
    bot.register_next_step_handler(msg, register_nick)

def register_nick(msg):
    nick = msg.text.strip()
    
    if len(nick) < 2 or len(nick) > 20:
        bot.send_message(msg.chat.id, '❌ Ник должен быть от 2 до 20 символов.')
        bot.register_next_step_handler(msg, register_nick)
        return
    
    if ' ' in nick:
        bot.send_message(msg.chat.id, '❌ Ник не должен содержать пробелов.')
        bot.register_next_step_handler(msg, register_nick)
        return
    
    if get_user_by_nick(nick):
        bot.send_message(msg.chat.id, '❌ Этот ник уже занят.')
        bot.register_next_step_handler(msg, register_nick)
        return
    
    bot.send_message(msg.chat.id, '🔑 Придумайте пароль (минимум 4 символа):')
    bot.register_next_step_handler(msg, register_password, nick)

def register_password(msg, nick):
    password = msg.text.strip()
    
    if len(password) < 4:
        bot.send_message(msg.chat.id, '❌ Пароль должен быть минимум 4 символа.')
        bot.register_next_step_handler(msg, register_password, nick)
        return
    
    bot.send_message(msg.chat.id, '🔁 Повторите пароль:')
    bot.register_next_step_handler(msg, register_confirm, nick, password)

def register_confirm(msg, nick, password):
    if msg.text.strip() != password:
        bot.send_message(msg.chat.id, '❌ Пароли не совпадают. Начните заново: /start')
        return
    
    user_id = msg.from_user.id
    hashed_password = hash_password(password)
    reg_date = get_current_time().strftime('%d.%m.%Y %H:%M')
    
    success = create_user(user_id, nick, hashed_password, reg_date)
    if not success:
        bot.send_message(msg.chat.id, '❌ Ошибка регистрации. Попробуйте позже.')
        return
    
    bot.send_message(msg.chat.id, f'✅ Поздравляю, {nick}! Вы зарегистрированы и авторизованы.', reply_markup=main_keyboard)

@bot.message_handler(func=lambda m: m.text == '🚪 Выйти')
def logout(msg):
    user_id = msg.from_user.id
    update_user(user_id, is_logged_in=0)
    bot.send_message(msg.chat.id, '👋 Вы вышли из аккаунта.', reply_markup=auth_keyboard)

# ============================================================
# КРАСИВЫЙ ПРОФИЛЬ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    nick = user['game_nick']
    balance = user['balance']
    cases_opened = user.get('cases_opened', 0)
    secret_items = user.get('secret_items', 0)
    
    username = msg.from_user.username
    display_username = f'@{username}' if username else 'Нет юза'
    
    status = get_status(balance)
    
    text = f'''
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
   ✦  👤 ПРОФИЛЬ  ✦
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

📛 Ник: {nick}
🔖 Юзернейм: {display_username}

💰 Баланс: {balance:,} монет

🎁 Кейсов открыто: {cases_opened}
⭐ Секретов: {secret_items}

🏷️ Статус: {status}

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ============================================================
# БАЛАНС
# ============================================================

@bot.message_handler(func=lambda m: m.text == '💰 Баланс')
def balance(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    bot.send_message(msg.chat.id, f'💰 Твой баланс: {user["balance"]:,} монет')

# ============================================================
# СТАТУС (ПРОГРЕСС)
# ============================================================

@bot.message_handler(commands=['status'])
def status_command(msg):
    status_cmd(msg)

@bot.message_handler(func=lambda m: m.text == '📊 Статус')
def status_cmd(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    balance = user['balance']
    current_status = get_status(balance)
    
    statuses = [
        (0, '🏚️ Бездомный'),
        (1, '🥺 Попрошайка'),
        (10, '🕊️ Бедняк'),
        (50, '🌱 Новичок'),
        (100, '🎓 Студент'),
        (200, '📝 Стажёр'),
        (300, '🔨 Работяга'),
        (400, '🏦 Копилка'),
        (500, '⚖️ Середняк'),
        (700, '💪 Трудяга'),
        (900, '🏢 Предприниматель'),
        (1200, '📈 Бизнесмен'),
        (1500, '💼 Инвестор'),
        (2000, '👔 Магнат'),
        (3000, '🏰 Барон'),
        (5000, '👑 Граф'),
        (7000, '🏛️ Герцог'),
        (10000, '⚜️ Князь'),
        (15000, '👑 Король'),
        (20000, '🏯 Император'),
        (30000, '🗿 Титан'),
        (50000, '🌟 Легенда'),
        (70000, '🔥 Миф'),
        (100000, '⚡ Бог'),
        (250000, '✨ Творец'),
        (500000, '♾️ Бессмертный'),
        (1000000, '🌌 Космос'),
        (5000000, '🌠 Вселенная'),
        (10000000, '∞ Бесконечность'),
        (50000000, '⚛️ Абсолют'),
        (1000000000, '🌌✨ Легенда Вселенной'),
    ]
    
    next_status = None
    for threshold, name in statuses:
        if balance < threshold:
            next_status = (threshold, name)
            break
    
    if next_status:
        threshold, name = next_status
        remaining = threshold - balance
        current_threshold = 0
        for t, _ in statuses:
            if t <= balance:
                current_threshold = t
        
        progress = int((balance - current_threshold) / (threshold - current_threshold) * 10) if threshold > current_threshold else 0
        bar = '█' * progress + '░' * (10 - progress)
        
        text = f'''
📊 **ТВОЙ СТАТУС**

💰 Баланс: {balance:,} монет

🏷️ Текущий статус: {current_status}
🎯 Следующий: {name} ({threshold:,} монет)

📈 До следующего статуса: {remaining:,} монет
📊 Прогресс: [{bar}] {progress * 10}%

💡 Советы:
🎰 Играй в игры, чтобы заработать монеты
🎁 Открывай кейсы
👑 Стань Легендой Вселенной!
'''
    else:
        text = f'''
📊 **ТВОЙ СТАТУС**

💰 Баланс: {balance:,} монет

🏷️ Текущий статус: 🌌✨ Легенда Вселенной

👑 Ты достиг максимального статуса!
Поздравляю! Ты лучший!

💡 Советы:
🎰 Продолжай играть, чтобы удерживать статус
🎁 Открывай кейсы
🏆 Стань первым, кто достигнет 2 000 000 000 монет!
'''
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ============================================================
# ТОП ИГРОКОВ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '📊 Топ игроков')
def top_players(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT game_nick, balance FROM users ORDER BY balance DESC LIMIT 10')
        players = cur.fetchall()
        cur.close()
    finally:
        release_db_connection(conn)
    
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    
    text = '🏆 ТОП-10 ПО БАЛАНСУ\n\n'
    for i, (nick, balance) in enumerate(players, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        status_emoji = get_status(balance).split()[0] if balance >= 1000000000 else ''
        text += f'{medal} {nick} — {balance:,} монет {status_emoji}\n'
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ============================================================
# ТОП КЕЙСОВ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🏆 Топ кейсов')
def top_cases(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT game_nick, cases_opened FROM users WHERE cases_opened > 0 ORDER BY cases_opened DESC LIMIT 10')
        players = cur.fetchall()
        cur.close()
    finally:
        release_db_connection(conn)
    
    if not players:
        bot.send_message(msg.chat.id, '📭 Пока никто не открывал кейсы. Будь первым! 🎁')
        return
    
    text = '🏆 ТОП-10 ПО ОТКРЫТИЮ КЕЙСОВ\n\n'
    for i, (nick, count) in enumerate(players, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        text += f'{medal} {nick} — {count} кейсов\n'
    
    bot.send_message(msg.chat.id, text)

# ============================================================
# ТОП СЕКРЕТОВ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '⭐ Топ секретов')
def top_secrets(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT game_nick, secret_items FROM users WHERE secret_items > 0 ORDER BY secret_items DESC LIMIT 10')
        players = cur.fetchall()
        cur.close()
    finally:
        release_db_connection(conn)
    
    if not players:
        bot.send_message(msg.chat.id, '📭 Пока никто не выбивал секретные предметы. Удачи! 🍀')
        return
    
    text = '⭐ ТОП-10 ПО СЕКРЕТНЫМ ПРЕДМЕТАМ\n\n'
    for i, (nick, count) in enumerate(players, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        text += f'{medal} {nick} — {count} секретов\n'
    
    bot.send_message(msg.chat.id, text)

# ============================================================
# КЕЙСЫ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🎁 Кейсы')
def cases_menu(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    caption = f'''
🎁 **КЕЙСЫ**

💰 Ваш баланс: {user['balance']:,} монет

📦 Доступные кейсы:
'''
    
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    for case_id, case in CASES.items():
        keyboard.add(
            telebot.types.InlineKeyboardButton(
                f'{case["emoji"]} {case["name"]} кейс — {case["price"]} монет',
                callback_data=f'case_{case_id}'
            )
        )
    
    bot.send_photo(msg.chat.id, CASE_PHOTO_URL, caption=caption, parse_mode='Markdown', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('case_'))
def case_details(call):
    user_id = call.from_user.id
    case_id = int(call.data.split('_')[1])
    case = CASES.get(case_id)
    
    if not case:
        bot.answer_callback_query(call.id, '❌ Кейс не найден.')
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, '❌ Ошибка.')
        return
    
    rewards_text = ''
    for r in case['rewards']:
        if r['type'] == 'coins':
            rewards_text += f'• {r["chance"]}% — {r["min"]}–{r["max"]} монет\n'
        elif r['type'] == 'secret_jackpot':
            rewards_text += f'• {r["chance"]}% — ⭐ СЕКРЕТНЫЙ ДЖЕКПОТ ({r["min"]} монет)\n'
    
    text = f'''
{case["emoji"]} **{case["name"]} кейс**

💰 Стоимость: {case["price"]} монет

🎲 Шансы:
{rewards_text}

Вы хотите купить этот кейс?
'''
    
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        telebot.types.InlineKeyboardButton('✅ Да', callback_data=f'buy_{case_id}'),
        telebot.types.InlineKeyboardButton('❌ Нет', callback_data='cancel_buy')
    )
    
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption=text,
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_buy')
def cancel_buy(call):
    cases_menu(call.message)
    bot.answer_callback_query(call.id)

# ============================================================
# ЛОГИКА ОТКРЫТИЯ КЕЙСА
# ============================================================

def process_buy_case_logic(msg, user_id, case_id, case, user):
    update_user(user_id, balance=user['balance'] - case['price'])
    
    msg1 = bot.send_message(msg.chat.id, f'🎁 ОТКРЫТИЕ КЕЙСА...\n\nВы выбрали: {case["emoji"]} {case["name"]} кейс\n💰 Стоимость: {case["price"]} монет')
    time.sleep(1.5)
    bot.delete_message(msg.chat.id, msg1.message_id)
    
    msg2 = bot.send_message(msg.chat.id, '🌀 Крутим...')
    time.sleep(1.5)
    bot.delete_message(msg.chat.id, msg2.message_id)
    
    total_chance = sum(r['chance'] for r in case['rewards'])
    rand = random.random() * total_chance
    cumulative = 0
    selected_reward = case['rewards'][-1]
    
    for reward in case['rewards']:
        cumulative += reward['chance']
        if rand <= cumulative:
            selected_reward = reward
            break
    
    update_user(user_id, cases_opened=user.get('cases_opened', 0) + 1)
    
    boss = get_boss()
    if boss:
        hit_boss(1)
        add_boss_participant(user_id, user['game_nick'])
        add_boss_damage(user_id, user['game_nick'], 1)
        
        if boss['hp'] <= 1:
            finish_boss()
            notify_all_players('🎉 *БОСС УБИТ!* Топ-1 по урону получает 500 000 монет!')
    
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        telebot.types.InlineKeyboardButton('🎁 Открыть ещё', callback_data=f'open_again_{case_id}')
    )
    
    if selected_reward['type'] == 'coins':
        amount = random.randint(selected_reward['min'], selected_reward['max'])
        update_user(user_id, balance=user['balance'] - case['price'] + amount)
        
        # Проверяем уникальный статус
        check_unique_status(user_id)
        
        caption = f'''
🎁 ОТКРЫТИЕ КЕЙСА... ✅

💰 ВЫПАЛО: {amount} монет!

📦 Ваш баланс: {user['balance'] - case['price'] + amount:,} монет
📊 Всего открыто: {user.get('cases_opened', 0) + 1} кейсов
'''
        
        bot.send_photo(msg.chat.id, CASE_PHOTO_URL, caption=caption, parse_mode='Markdown', reply_markup=keyboard)
    
    elif selected_reward['type'] == 'secret_jackpot':
        amount = selected_reward['min']
        update_user(user_id, balance=user['balance'] - case['price'] + amount)
        update_user(user_id, secret_items=user.get('secret_items', 0) + 1)
        
        # Проверяем уникальный статус
        check_unique_status(user_id)
        
        caption = f'''
⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️
🎉 СЕКРЕТНЫЙ ДЖЕКПОТ!
⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️

💰 +{amount} монет!

Поздравляю! Ты сорвал джекпот! 🍀
📊 Всего открыто: {user.get('cases_opened', 0) + 1} кейсов
⭐ Всего секретов: {user.get('secret_items', 0) + 1}
'''
        
        bot.send_photo(msg.chat.id, CASE_PHOTO_URL, caption=caption, parse_mode='Markdown', reply_markup=keyboard)

# ============================================================
# ОБРАБОТЧИКИ КЕЙСОВ
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_buy_case(call):
    user_id = call.from_user.id
    case_id = int(call.data.split('_')[1])
    case = CASES.get(case_id)
    
    if not case:
        bot.answer_callback_query(call.id, '❌ Кейс не найден.')
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, '❌ Ошибка.')
        return
    
    if user['balance'] < case['price']:
        bot.answer_callback_query(call.id, f'❌ Не хватает {case["price"] - user["balance"]} монет!')
        return
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    process_buy_case_logic(call.message, user_id, case_id, case, user)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('open_again_'))
def open_again(call):
    user_id = call.from_user.id
    case_id = int(call.data.split('_')[2])
    case = CASES.get(case_id)
    
    if not case:
        bot.answer_callback_query(call.id, '❌ Кейс не найден.')
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, '❌ Ошибка.')
        return
    
    if user['balance'] < case['price']:
        bot.answer_callback_query(call.id, f'❌ Не хватает {case["price"] - user["balance"]} монет!')
        return
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    process_buy_case_logic(call.message, user_id, case_id, case, user)
    bot.answer_callback_query(call.id)

# ============================================================
# ЧАТ
# ============================================================

@bot.message_handler(commands=['chat'])
def chat_command(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Вы заблокированы.')
        return
    
    if is_muted(user_id):
        bot.send_message(msg.chat.id, '🔇 Вы замучены. Не можете писать в чат.')
        return
    
    try:
        text = msg.text.split(' ', 1)[1].strip()
        if not text:
            raise IndexError
        
        user = get_cached_user(user_id)
        nick = user['game_nick']
        
        save_chat_message(user_id, nick, text)
        notify_chat_message(user_id, nick, text)
        
        bot.send_message(msg.chat.id, f'💬 Сообщение отправлено в общий чат.')
        
    except IndexError:
        messages = get_chat_messages(20)
        if not messages:
            bot.send_message(msg.chat.id, '💬 Чат пуст. Напишите первое сообщение!')
            return
        
        text = '💬 **ВСЕМИРНЫЙ ЧАТ**\n\n'
        for display_name, message, timestamp in messages:
            text += f'[{timestamp}] {display_name}: {message}\n'
        
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💬 Чат')
def chat_button(msg):
    user_id = msg.from_user.id
    
    if is_maintenance_mode():
        minutes = get_maintenance_time()
        bot.send_message(msg.chat.id, f'⏸️ Бот на техническом перерыве. Возвращаемся через {minutes} минут! 🔧')
        return
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    messages = get_chat_messages(20)
    if not messages:
        bot.send_message(msg.chat.id, '💬 Чат пуст. Напишите первое сообщение!\n\nИспользуйте: /chat текст')
        return
    
    text = '💬 **ВСЕМИРНЫЙ ЧАТ**\n\n'
    for display_name, message, timestamp in messages:
        text += f'[{timestamp}] {display_name}: {message}\n'
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['clear_chat'])
def clear_chat_cmd(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    clear_chat()
    bot.send_message(msg.chat.id, '✅ Чат очищен.')

# ============================================================
# БОСС
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🐉 Создать босса' and is_admin(m.from_user.id))
def create_boss_cmd(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    boss = get_boss()
    if boss:
        bot.send_message(msg.chat.id, '❌ Босс уже активен!')
        return
    
    success = create_boss()
    if success:
        bot.send_message(msg.chat.id, '🐉 Босс создан! У него 10 000 HP. У вас есть 1 час!')
        notify_all_players('🐉 *ВНИМАНИЕ!* Босс появился! Убейте его за 1 час! Каждый открытый кейс наносит 1 урон!')
    else:
        bot.send_message(msg.chat.id, '❌ Ошибка создания босса.')

@bot.message_handler(func=lambda m: m.text == '📊 Статус босса')
def boss_status(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    boss = get_boss()
    if not boss:
        bot.send_message(msg.chat.id, '📭 Босс не активен.')
        return
    
    now = get_current_time()
    end_time = datetime.fromisoformat(boss['end_time'])
    remaining = end_time - now
    minutes = remaining.seconds // 60
    
    hp_percent = int(boss['hp'] / boss['max_hp'] * 10)
    bar = '█' * hp_percent + '░' * (10 - hp_percent)
    
    participants = get_boss_participants()
    
    text = f'''
🐉 **СТАТУС БОССА**

❤️ HP: {boss['hp']} / {boss['max_hp']}
📊 Прогресс: [{bar}] {int((1 - boss['hp'] / boss['max_hp']) * 100)}%
⏳ Осталось: {minutes} минут
👥 Участников: {len(participants)}

📌 За каждое открытие кейса наносится 1 урон!
'''
    
    if participants:
        top = sorted(participants, key=lambda x: x['hits'], reverse=True)[:5]
        text += '\n🏆 ТОП-5 УЧАСТНИКОВ:\n'
        for i, p in enumerate(top, 1):
            text += f'{i}. {p["nick"]} — {p["hits"]} ударов\n'
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '⚙️ Управление боссом' and is_admin(m.from_user.id))
def manage_boss(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    boss = get_boss()
    if not boss:
        bot.send_message(msg.chat.id, '📭 Босс не активен. Сначала создайте босса!')
        return
    
    text = f'''
⚙️ **УПРАВЛЕНИЕ БОССОМ**

🐉 Текущий босс:
❤️ HP: {boss['hp']} / {boss['max_hp']}
⏳ Осталось: {get_boss_remaining_time()}

Выберите действие:

1️⃣ Изменить HP
2️⃣ Изменить время
3️⃣ Удалить босса
'''
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_manage_boss)

def process_manage_boss(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        choice = int(msg.text.strip())
        if choice == 1:
            bot.send_message(msg.chat.id, '✏️ Введите новое HP босса:')
            bot.register_next_step_handler(msg, change_boss_hp)
        elif choice == 2:
            bot.send_message(msg.chat.id, '✏️ Введите новое время (в минутах):')
            bot.register_next_step_handler(msg, change_boss_time)
        elif choice == 3:
            finish_boss()
            bot.send_message(msg.chat.id, '✅ Босс удалён.')
            notify_all_players('👑 Босс был удалён администратором.')
        else:
            bot.send_message(msg.chat.id, '❌ Неверный номер.')
    except:
        bot.send_message(msg.chat.id, '❌ Введите номер.')

def change_boss_hp(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        new_hp = int(msg.text.strip())
        if new_hp < 1:
            bot.send_message(msg.chat.id, '❌ HP должно быть больше 0.')
            return
        
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute('UPDATE boss SET hp = %s, max_hp = %s WHERE active = 1', (new_hp, new_hp))
            conn.commit()
            cur.close()
            bot.send_message(msg.chat.id, f'✅ HP босса изменено на {new_hp}!')
        finally:
            release_db_connection(conn)
    except:
        bot.send_message(msg.chat.id, '❌ Введите число.')

def change_boss_time(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        minutes = int(msg.text.strip())
        if minutes < 1:
            bot.send_message(msg.chat.id, '❌ Время должно быть больше 0.')
            return
        
        new_end = (get_current_time() + timedelta(minutes=minutes)).isoformat()
        
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute('UPDATE boss SET end_time = %s WHERE active = 1', (new_end,))
            conn.commit()
            cur.close()
            bot.send_message(msg.chat.id, f'✅ Время изменено на {minutes} минут!')
        finally:
            release_db_connection(conn)
    except:
        bot.send_message(msg.chat.id, '❌ Введите число минут.')

# ============================================================
# БОСС ЛИДЕРБОРД
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🏆 Топ урона боссу')
def boss_top_damage(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    participants = get_boss_participants()
    if not participants:
        bot.send_message(msg.chat.id, '📭 Нет участников.')
        return
    
    top = sorted(participants, key=lambda x: x['hits'], reverse=True)[:10]
    
    text = '🏆 ТОП-10 ПО УРОНУ БОССУ\n\n'
    for i, p in enumerate(top, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        text += f'{medal} {p["nick"]} — {p["hits"]} ударов\n'
    
    bot.send_message(msg.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '⚔️ Лидерборд босса')
def boss_leaderboard(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    leaderboard = get_boss_leaderboard()
    if not leaderboard:
        bot.send_message(msg.chat.id, '📭 Лидерборд пуст.')
        return
    
    text = '⚔️ **ЛИДЕРБОРД БОССА**\n\n'
    for i, (uid, nick, damage, claimed) in enumerate(leaderboard[:10], 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        claimed_text = ' ✅' if claimed else ''
        text += f'{medal} {nick} — {damage} урона{claimed_text}\n'
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '🗑️ Очистить лидерборд' and is_admin(m.from_user.id))
def clear_leaderboard(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    clear_boss_leaderboard()
    bot.send_message(msg.chat.id, '✅ Лидерборд очищен.')

@bot.message_handler(func=lambda m: m.text == '🚫 Убрать из лидерборда' and is_admin(m.from_user.id))
def remove_from_leaderboard_start(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '✏️ Введите ник игрока для удаления из лидерборда:')
    bot.register_next_step_handler(msg, process_remove_from_leaderboard)

def process_remove_from_leaderboard(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, '❌ Игрок не найден.')
        return
    
    remove_from_boss_leaderboard(user['id'])
    bot.send_message(msg.chat.id, f'✅ {nick} удалён из лидерборда.')

# ============================================================
# МУТ / РАЗМУТ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🔇 Замутить' and is_admin(m.from_user.id))
def mute_button(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '✏️ Введите ник и время в минутах:\nПример: Alex 30')
    bot.register_next_step_handler(msg, process_mute_button)

def process_mute_button(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            bot.send_message(msg.chat.id, '❌ Формат: ник минуты\nПример: Alex 30')
            return
        
        nick = parts[0]
        minutes = int(parts[1]) if len(parts) > 1 else 60
        
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        
        mute_user(user['id'], minutes)
        bot.send_message(msg.chat.id, f'🔇 {nick} замучен на {minutes} минут.')
        
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник минуты')

@bot.message_handler(func=lambda m: m.text == '🔊 Размутить' and is_admin(m.from_user.id))
def unmute_button(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '✏️ Введите ник для размута:\nПример: Alex')
    bot.register_next_step_handler(msg, process_unmute_button)

def process_unmute_button(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, '❌ Игрок не найден.')
        return
    
    unmute_user(user['id'])
    bot.send_message(msg.chat.id, f'🔊 {nick} размучен.')

# ============================================================
# ТЕХНИЧЕСКИЙ ПЕРЕРЫВ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '⏸️ Включить перерыв' and is_admin(m.from_user.id))
def enable_maintenance(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '⏸️ **ТЕХНИЧЕСКИЙ ПЕРЕРЫВ**\n\nВведите время в минутах:\nПример: 15', parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_enable_maintenance)

def process_enable_maintenance(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        minutes = int(msg.text.strip())
        if minutes < 1:
            bot.send_message(msg.chat.id, '❌ Минимум 1 минута.')
            return
        
        set_maintenance_mode(minutes)
        bot.send_message(msg.chat.id, f'⏸️ Бот ушёл на технический перерыв на {minutes} минут! 🔧')
        notify_all_players(f'⏸️ *Бот на техническом перерыве!*\nВозвращаемся через {minutes} минут! 🔧')
    except:
        bot.send_message(msg.chat.id, '❌ Введите число минут.')

@bot.message_handler(func=lambda m: m.text == '▶️ Выключить перерыв' and is_admin(m.from_user.id))
def disable_maintenance(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    set_maintenance_mode(0)
    bot.send_message(msg.chat.id, '▶️ Технический перерыв завершён! Бот снова работает.')
    notify_all_players('▶️ *Бот снова работает!* Добро пожаловать! 🎉')

# ============================================================
# СБРОС СТАТУСА "ЛЕГЕНДА ВСЕЛЕННОЙ"
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🔄 Сбросить Легенду' and is_admin(m.from_user.id))
def reset_legend_status(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, game_nick, balance FROM users WHERE balance >= 1000000000')
        users = cur.fetchall()
        cur.close()
        
        if not users:
            bot.send_message(msg.chat.id, '📭 Нет игроков с балансом 1 лярд.')
            return
        
        text = '👑 **СПИСОК ЛЕГЕНД**\n\n'
        for user_id, nick, balance in users:
            text += f'• {nick} — {balance:,} монет\n'
        text += '\nВведите ник для сброса статуса (или "нет"):'
        
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_reset_legend, users)
    finally:
        release_db_connection(conn)

def process_reset_legend(msg, users):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    nick = msg.text.strip()
    if nick.lower() == 'нет':
        bot.send_message(msg.chat.id, '✅ Отменено.')
        return
    
    for user_id, user_nick, balance in users:
        if user_nick == nick:
            update_user(user_id, balance=999999999)
            bot.send_message(msg.chat.id, f'✅ Статус "{nick}" сброшен! Баланс изменён на 999 999 999.')
            return
    
    bot.send_message(msg.chat.id, '❌ Игрок не найден среди Легенд.')

# ============================================================
# ПАНЕЛЬ СОЗДАТЕЛЯ
# ============================================================

@bot.message_handler(commands=['creator'])
def creator_panel(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    bot.send_message(msg.chat.id, '👑 Панель создателя', reply_markup=creator_keyboard)

@bot.message_handler(func=lambda m: m.text == '⬅️ Назад' and is_admin(m.from_user.id))
def back_to_main_creator(msg):
    bot.send_message(msg.chat.id, '🏠 Главное меню', reply_markup=main_keyboard)

# ============================================================
# КОМАНДЫ СОЗДАТЕЛЯ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '💰 Изменить баланс' and is_admin(m.from_user.id))
def change_balance_start(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '💰 ИЗМЕНИТЬ БАЛАНС\n\nВведите: @ник сумма\nПример: @alex88 +1000')
    bot.register_next_step_handler(msg, process_change_balance)

def process_change_balance(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        parts = msg.text.split()
        nick = parts[0].replace('@', '')
        amount = int(parts[1])
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        new_balance = max(0, user['balance'] + amount)
        update_user(user['id'], balance=new_balance)
        bot.send_message(msg.chat.id, f'✅ Баланс {nick} изменён на {new_balance} монет')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: @ник сумма')

@bot.message_handler(func=lambda m: m.text == '👤 Удалить аккаунт' and is_admin(m.from_user.id))
def delete_account_start(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '⚠️ Введите ник для удаления:')
    bot.register_next_step_handler(msg, process_delete_account)

def process_delete_account(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, '❌ Игрок не найден.')
        return
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM users WHERE game_nick = %s', (nick,))
        conn.commit()
        cur.close()
        invalidate_cache(user['id'])
    finally:
        release_db_connection(conn)
    
    bot.send_message(msg.chat.id, f'🗑️ Аккаунт {nick} удалён.')

@bot.message_handler(func=lambda m: m.text == '📊 Статистика сервера' and is_admin(m.from_user.id))
def creator_stats(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM users')
        total_users = cur.fetchone()[0]
        cur.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
        total_balance = cur.fetchone()[0]
        cur.execute('SELECT COALESCE(MAX(balance), 0) FROM users')
        max_balance = cur.fetchone()[0]
        cur.close()
    finally:
        release_db_connection(conn)
    
    text = f'''
📊 СТАТИСТИКА СЕРВЕРА

👥 Всего игроков: {total_users}
💰 Общий баланс: {total_balance:,}
🏆 Макс. баланс: {max_balance:,}
'''
    bot.send_message(msg.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '👥 Список игроков' and is_admin(m.from_user.id))
def creator_players_list(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT game_nick, balance FROM users ORDER BY balance DESC')
        players = cur.fetchall()
        cur.close()
    finally:
        release_db_connection(conn)
    
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    
    text = '👥 ВСЕ ИГРОКИ\n\n'
    for i, (nick, balance) in enumerate(players, 1):
        text += f'{i}. {nick} — {balance:,} монет\n'
        if i >= 20:
            text += '\nПоказаны первые 20 игроков.'
            break
    
    bot.send_message(msg.chat.id, text)

# ============================================================
# ФОН ПРОВЕРКА БОССА
# ============================================================

def check_boss_timeout():
    while True:
        time.sleep(60)
        boss = get_boss()
        if boss:
            now = get_current_time()
            end_time = datetime.fromisoformat(boss['end_time'])
            if now > end_time:
                conn = get_db_connection()
                try:
                    cur = conn.cursor()
                    cur.execute('SELECT id, balance FROM users')
                    users = cur.fetchall()
                    for user_id, balance in users:
                        new_balance = max(0, balance - 500)
                        update_user(user_id, balance=new_balance)
                    cur.close()
                finally:
                    release_db_connection(conn)
                
                finish_boss()
                notify_all_players('💀 *БОСС УШЁЛ!* Все игроки теряют 500 монет!')

threading.Thread(target=check_boss_timeout, daemon=True).start()

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == '__main__':
    print('✅ Бот запущен!')
    bot.remove_webhook()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f'❌ Ошибка: {e}. Перезапуск через 5 секунд...')
            time.sleep(5)