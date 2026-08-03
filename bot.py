import os
import random
import hashlib
import time
from datetime import datetime
from functools import lru_cache
from threading import Lock
import telebot
import psycopg2
import psycopg2.extras
from psycopg2 import pool

# ===== КОНФИГ =====
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("❌ Токен не найден!")

ADMIN_ID = int(os.getenv('ADMIN_ID', 6573154279))
bot = telebot.TeleBot(TOKEN)

# ===== ПУЛ СОЕДИНЕНИЙ С БАЗОЙ ДАННЫХ =====
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не найден!")

# Создаём пул соединений (минимум 1, максимум 10)
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

# ===== КЭШ ПОЛЬЗОВАТЕЛЕЙ =====
user_cache = {}
cache_lock = Lock()
CACHE_TTL = 15  # секунд

def get_cached_user(user_id):
    """Получить пользователя из кэша или базы данных"""
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
    """Очистить кэш для конкретного пользователя"""
    with cache_lock:
        if user_id in user_cache:
            del user_cache[user_id]

def clear_cache():
    """Очистить весь кэш"""
    with cache_lock:
        user_cache.clear()

# ============================================================
# ФУНКЦИИ РАБОТЫ С БД
# ============================================================

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
        # Собираем все обновления в один запрос
        set_clause = ', '.join([f'{key} = %s' for key in kwargs.keys()])
        values = list(kwargs.values()) + [user_id]
        cur.execute(f'UPDATE users SET {set_clause} WHERE id = %s', values)
        conn.commit()
        cur.close()
        # Очищаем кэш
        invalidate_cache(user_id)
    finally:
        release_db_connection(conn)

def user_exists(user_id):
    return get_cached_user(user_id) is not None

def is_logged_in(user_id):
    user = get_cached_user(user_id)
    return user and user['is_logged_in'] == 1

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
                is_logged_in INTEGER DEFAULT 0
            )
        ''')
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
main_keyboard.add('📊 Топ игроков', '🚪 Выйти')

creator_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
creator_keyboard.add('💰 Изменить баланс', '👤 Удалить аккаунт')
creator_keyboard.add('📊 Статистика сервера', '👥 Список игроков')
creator_keyboard.add('⬅️ Назад')

# ============================================================
# АВТОРИЗАЦИЯ
# ============================================================

@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    
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
    
    if not user_exists(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не зарегистрированы. Нажмите "Зарегистрироваться".')
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
        bot.send_message(msg.chat.id, '❌ Игрок с таким ником не найден. Попробуйте ещё раз.')
        return
    
    bot.send_message(msg.chat.id, '🔑 Введите пароль:')
    bot.register_next_step_handler(msg, login_password, nick)

def login_password(msg, nick):
    password = msg.text.strip()
    user = get_user_by_nick(nick)
    
    if not user or user['password'] != hash_password(password):
        bot.send_message(msg.chat.id, '❌ Неверный пароль. Попробуйте ещё раз.')
        return
    
    update_user(user['id'], is_logged_in=1)
    bot.send_message(msg.chat.id, f'✅ Добро пожаловать, {nick}!', reply_markup=main_keyboard)

@bot.message_handler(func=lambda m: m.text == '✨ Зарегистрироваться')
def register_start(msg):
    user_id = msg.from_user.id
    
    if user_exists(user_id):
        bot.send_message(msg.chat.id, '❌ У вас уже есть аккаунт! Войдите через "Войти".')
        return
    
    bot.send_message(msg.chat.id, '📝 Придумайте игровой ник (от 2 до 20 символов, без пробелов):')
    bot.register_next_step_handler(msg, register_nick)

def register_nick(msg):
    nick = msg.text.strip()
    
    if len(nick) < 2 or len(nick) > 20:
        bot.send_message(msg.chat.id, '❌ Ник должен быть от 2 до 20 символов. Попробуйте ещё раз:')
        bot.register_next_step_handler(msg, register_nick)
        return
    
    if ' ' in nick:
        bot.send_message(msg.chat.id, '❌ Ник не должен содержать пробелов. Попробуйте ещё раз:')
        bot.register_next_step_handler(msg, register_nick)
        return
    
    if get_user_by_nick(nick):
        bot.send_message(msg.chat.id, '❌ Этот ник уже занят. Придумайте другой:')
        bot.register_next_step_handler(msg, register_nick)
        return
    
    bot.send_message(msg.chat.id, '🔑 Придумайте пароль (минимум 4 символа):')
    bot.register_next_step_handler(msg, register_password, nick)

def register_password(msg, nick):
    password = msg.text.strip()
    
    if len(password) < 4:
        bot.send_message(msg.chat.id, '❌ Пароль должен быть минимум 4 символа. Попробуйте ещё раз:')
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
    
    update_user(
        user_id,
        game_nick=nick,
        password=hashed_password,
        reg_date=datetime.now().strftime('%d.%m.%Y %H:%M'),
        is_logged_in=1
    )
    
    bot.send_message(msg.chat.id, f'✅ Поздравляю, {nick}! Вы зарегистрированы и авторизованы.', reply_markup=main_keyboard)

@bot.message_handler(func=lambda m: m.text == '🚪 Выйти')
def logout(msg):
    user_id = msg.from_user.id
    update_user(user_id, is_logged_in=0)
    bot.send_message(msg.chat.id, '👋 Вы вышли из аккаунта.', reply_markup=auth_keyboard)

# ============================================================
# ПРОФИЛЬ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы. Войдите или зарегистрируйтесь.', reply_markup=auth_keyboard)
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    game_nick = user['game_nick']
    balance = user['balance']
    
    username = msg.from_user.username
    display_username = f'@{username}' if username else 'Нет юза'
    
    text = f'''
👤 ПРОФИЛЬ

📛 Ник: {game_nick}
🔖 Юзернейм: {display_username}
💰 Баланс: {balance} монет
'''
    
    bot.send_message(msg.chat.id, text)

# ============================================================
# БАЛАНС
# ============================================================

@bot.message_handler(func=lambda m: m.text == '💰 Баланс')
def balance(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    bot.send_message(msg.chat.id, f'💰 Твой баланс: {user["balance"]} монет')

# ============================================================
# ТОП ИГРОКОВ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '📊 Топ игроков')
def top_players(msg):
    user_id = msg.from_user.id
    
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
        text += f'{medal} {nick} — {balance} монет\n'
    
    bot.send_message(msg.chat.id, text)

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

def is_admin(user_id):
    return user_id == ADMIN_ID

# ============================================================
# КОМАНДЫ СОЗДАТЕЛЯ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '💰 Изменить баланс' and is_admin(m.from_user.id))
def change_balance_start(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '💰 ИЗМЕНИТЬ БАЛАНС\n\nВведите: @ник сумма\nПример: @alex88 +1000 или @alex88 -500')
    bot.register_next_step_handler(msg, process_change_balance)

def process_change_balance(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: @ник сумма')
            return
        
        nick = parts[0].replace('@', '')
        amount = int(parts[1])
        
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        
        new_balance = max(0, user['balance'] + amount)
        update_user(user['id'], balance=new_balance)
        
        text = f'✅ Баланс {nick} изменён на {new_balance} монет'
        if amount > 0:
            text += f' (+{amount})'
        else:
            text += f' ({amount})'
        
        bot.send_message(msg.chat.id, text)
        
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
        # Очищаем кэш
        if user:
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
💰 Общий баланс: {total_balance}
🏆 Макс. баланс: {max_balance}
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
        text += f'{i}. {nick} — {balance} монет\n'
        if i >= 20:
            text += '\nПоказаны первые 20 игроков.'
            break
    
    bot.send_message(msg.chat.id, text)

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == '__main__':
    print('✅ Бот запущен!')
    print('⚡ Оптимизация включена (кэш, пул соединений)')
    bot.remove_webhook()
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f'❌ Ошибка: {e}. Перезапуск через 5 секунд...')
            time.sleep(5)