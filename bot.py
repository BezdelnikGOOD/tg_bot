import os
import random
import hashlib
import json
import time
from datetime import datetime, timedelta
import telebot
import psycopg2
import psycopg2.extras
import requests

# ===== КОНФИГ =====
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("❌ Токен не найден!")

ADMIN_ID = int(os.getenv('ADMIN_ID', 6573154279))
bot = telebot.TeleBot(TOKEN)

# ===== БАЗА ДАННЫХ =====
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не найден!")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ===== ИНИЦИАЛИЗАЦИЯ =====
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            game_nick TEXT UNIQUE,
            password TEXT,
            balance INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            reg_date TEXT,
            is_logged_in INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            role TEXT DEFAULT 'user',
            admin_level INTEGER DEFAULT 0,
            vip_level INTEGER DEFAULT 0,
            vip_end TEXT DEFAULT NULL,
            energy INTEGER DEFAULT 50,
            max_energy INTEGER DEFAULT 50,
            inventory TEXT DEFAULT '[]',
            last_daily TEXT DEFAULT NULL,
            bp_level INTEGER DEFAULT 0,
            bp_exp INTEGER DEFAULT 0,
            bp_premium INTEGER DEFAULT 0,
            bp_rewards_collected TEXT DEFAULT '[]',
            bp_season INTEGER DEFAULT 1,
            notifications INTEGER DEFAULT 1,
            pp_level INTEGER DEFAULT 0,
            pp_exp INTEGER DEFAULT 0,
            pp_tier TEXT DEFAULT 'free',
            pp_rewards_collected TEXT DEFAULT '[]',
            pp_season INTEGER DEFAULT 1,
            pp_skin TEXT DEFAULT '',
            clan_id INTEGER DEFAULT NULL,
            clan_role TEXT DEFAULT NULL
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price INTEGER,
            income INTEGER,
            cooldown INTEGER DEFAULT 300,
            owner_id BIGINT DEFAULT NULL,
            owner_nick TEXT DEFAULT NULL,
            last_collected TEXT DEFAULT NULL
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS clans (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE,
            leader_id BIGINT,
            level INTEGER DEFAULT 1,
            bank INTEGER DEFAULT 0,
            created_at TEXT,
            member_count INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 0
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS clan_members (
            user_id BIGINT,
            clan_id INTEGER,
            role TEXT DEFAULT 'member',
            joined_at TEXT,
            PRIMARY KEY (user_id, clan_id)
        )
    ''')
    
    cur.execute('SELECT COUNT(*) FROM businesses')
    count = cur.fetchone()[0]
    
    if count == 0:
        businesses = [
            (1, '🍋 Лимонадный киоск', 'food', 1000, 120),
            (2, '🍦 Мороженое', 'food', 2500, 300),
            (3, '🍿 Попкорн', 'food', 5000, 600),
            (4, '🍔 Закусочная', 'food', 10000, 1200),
            (5, '🌮 Тако-бар', 'food', 20000, 2400),
            (6, '🍕 Пиццерия', 'food', 40000, 4800),
            (7, '🍣 Суши-бар', 'food', 80000, 9600),
            (8, '🥩 Стейк-хаус', 'food', 150000, 18000),
            (9, '🍷 Ресторан', 'food', 300000, 36000),
            (10, '🍾 Элитный ресторан', 'food', 600000, 72000),
            (11, '🛒 Ларёк', 'trade', 1500, 180),
            (12, '📱 Салон связи', 'trade', 4000, 480),
            (13, '🏪 Магазин', 'trade', 8000, 960),
            (14, '👗 Бутик', 'trade', 18000, 2160),
            (15, '💎 Ювелирка', 'trade', 35000, 4200),
            (16, '🏦 Обменник', 'trade', 70000, 8400),
            (17, '🏢 Офисный центр', 'trade', 140000, 16800),
            (18, '🏨 Отель', 'trade', 280000, 33600),
            (19, '🏗️ Строительная фирма', 'trade', 550000, 66000),
            (20, '🏙️ Недвижимость', 'trade', 1100000, 132000),
            (21, '🍺 Пивоварня', 'factory', 3000, 360),
            (22, '🧵 Швейная фабрика', 'factory', 7000, 840),
            (23, '🔩 Металлообработка', 'factory', 15000, 1800),
            (24, '🏭 Завод', 'factory', 30000, 3600),
            (25, '🔬 Химзавод', 'factory', 60000, 7200),
            (26, '⚡ Электростанция', 'factory', 120000, 14400),
            (27, '🚗 Автозавод', 'factory', 250000, 30000),
            (28, '✈️ Авиазавод', 'factory', 500000, 60000),
            (29, '🚀 Космический завод', 'factory', 1000000, 120000),
            (30, '⚛️ Атомная станция', 'factory', 2000000, 240000),
            (31, '🎮 Игровой клуб', 'entertainment', 5000, 600),
            (32, '🎲 Казино', 'entertainment', 12000, 1440),
            (33, '🎬 Кинотеатр', 'entertainment', 25000, 3000),
            (34, '🏟️ Стадион', 'entertainment', 50000, 6000),
            (35, '🎭 Театр', 'entertainment', 100000, 12000),
            (36, '🎵 Музыкальный лейбл', 'entertainment', 200000, 24000),
            (37, '🎬 Киностудия', 'entertainment', 400000, 48000),
            (38, '📺 Телеканал', 'entertainment', 800000, 96000),
            (39, '🎮 Игровая студия', 'entertainment', 1600000, 192000),
            (40, '🤖 IT-корпорация', 'entertainment', 3200000, 384000),
            (41, '🏦 Банк', 'mega', 200000, 24000),
            (42, '🛢️ Нефтяная вышка', 'mega', 500000, 60000),
            (43, '💎 Алмазный рудник', 'mega', 1200000, 144000),
            (44, '🚢 Судоходная компания', 'mega', 2500000, 300000),
            (45, '✈️ Авиакомпания', 'mega', 5000000, 600000),
            (46, '🛰️ Спутниковая сеть', 'mega', 10000000, 1200000),
            (47, '🏙️ Город-спутник', 'mega', 25000000, 3000000),
            (48, '🪐 Космическая станция', 'mega', 50000000, 6000000),
            (49, '🌌 Межгалактическая империя', 'mega', 100000000, 12000000),
            (50, '♾️ Бесконечность', 'mega', 500000000, 60000000),
        ]
        
        for b in businesses:
            cur.execute('''
                INSERT INTO businesses (id, name, category, price, income, cooldown)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (b[0], b[1], b[2], b[3], b[4], 300))
        
        conn.commit()
        print('✅ 50 бизнесов добавлены')
    
    conn.commit()
    cur.close()
    conn.close()
    print('✅ База данных готова')

init_db()

# ============================================================
# ФУНКЦИИ РАБОТЫ С БД
# ============================================================

def get_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def get_user_by_nick(nick):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM users WHERE game_nick = %s', (nick,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def update_user(user_id, **kwargs):
    conn = get_db_connection()
    cur = conn.cursor()
    for key, value in kwargs.items():
        cur.execute(f'UPDATE users SET {key} = %s WHERE id = %s', (value, user_id))
    conn.commit()
    cur.close()
    conn.close()

def user_exists(user_id):
    return get_user(user_id) is not None

def is_logged_in(user_id):
    user = get_user(user_id)
    return user and user['is_logged_in'] == 1

def is_banned(user_id):
    user = get_user(user_id)
    return user and user['is_banned'] == 1

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ============================================================
# КЛАВИАТУРЫ
# ============================================================

auth_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
auth_keyboard.add('🔑 Войти', '✨ Зарегистрироваться')

main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_keyboard.add('👤 Профиль', '💰 Баланс')
main_keyboard.add('🎰 Играть', '📊 Топ игроков')
main_keyboard.add('🏷️ Все статусы', '🏢 Бизнесы')
main_keyboard.add('👑 Подписка', '🎒 Инвентарь')
main_keyboard.add('🛒 Магазин', '🤝 Торговля')
main_keyboard.add('🎖️ Премиум Пасс', '🏰 Кланы')
main_keyboard.add('🚪 Выйти')

# ============================================================
# АВТОРИЗАЦИЯ
# ============================================================

@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Вы заблокированы.')
        return
    
    if user_exists(user_id):
        if is_logged_in(user_id):
            user = get_user(user_id)
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
    
    if user['is_banned']:
        bot.send_message(msg.chat.id, '🚫 Ваш аккаунт заблокирован.')
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
    
    user = get_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    game_nick = user['game_nick']
    balance = user['balance']
    level = user['level']
    exp = user['exp']
    reg_date = user['reg_date']
    
    username = msg.from_user.username
    display_username = f'@{username}' if username else 'Нет юза'
    
    needed = level * 50
    progress = int(exp / needed * 10) if needed > 0 else 0
    bar = '█' * progress + '░' * (10 - progress)
    
    text = f'''
👤 ПРОФИЛЬ

📛 Ник: {game_nick}
🔖 Юзернейм: {display_username}
💰 Баланс: {balance} монет
📈 Уровень: {level}
⭐ Опыт: {exp} / {needed}
📊 Прогресс: [{bar}]
📅 В игре с: {reg_date}
'''
    
    bot.send_message(msg.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '💰 Баланс')
def balance(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    bot.send_message(msg.chat.id, f'💰 Твой баланс: {user["balance"]} монет')

# ============================================================
# ИГРА
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🎰 Играть')
def game(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    if user['balance'] < 10:
        bot.send_message(msg.chat.id, '❌ Не хватает 10 монет!')
        return
    
    update_user(user_id, balance=user['balance'] - 10)
    win = random.choice([0, 1])
    
    if win:
        update_user(user_id, balance=user['balance'] - 10 + 25)
        bot.send_message(msg.chat.id, '🎉 Ты выиграл! +25 монет')
    else:
        bot.send_message(msg.chat.id, '😢 Ты проиграл. -10 монет')

# ============================================================
# ТОП
# ============================================================

@bot.message_handler(func=lambda m: m.text == '📊 Топ игроков')
def top_players(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT game_nick, balance FROM users ORDER BY balance DESC LIMIT 10')
    players = cur.fetchall()
    cur.close()
    conn.close()
    
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    
    text = '🏆 ТОП-10 ПО БАЛАНСУ\n\n'
    for i, (nick, balance) in enumerate(players, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        text += f'{medal} {nick} — {balance} монет\n'
    
    bot.send_message(msg.chat.id, text)

# ============================================================
# ВСЕ СТАТУСЫ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🏷️ Все статусы')
def all_statuses(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    balance = user['balance']
    
    statuses = [
        (0, '💀 Банкрот'),
        (1, '🕊️ Бедняга'),
        (50, '🪙 Новичок'),
        (200, '💰 Середняк'),
        (500, '💎 Богач'),
        (1000, '👑 Магнат'),
        (5000, '🏦 Инвестор'),
        (10000, '🏰 Барон'),
        (50000, '💵 Миллионер'),
        (100000, '🌟 Легенда')
    ]
    
    status = get_status(balance)
    
    next_status = None
    for threshold, name in statuses:
        if balance < threshold:
            next_status = (threshold, name)
            break
    
    text = '🏷️ ВСЕ СТАТУСЫ\n\n'
    for threshold, name in statuses:
        text += f'{name}: {threshold}\n'
    
    text += f'\n📌 Твой статус: {status}'
    
    if next_status:
        text += f'\n📈 До "{next_status[1]}": {next_status[0] - balance} монет'
    
    bot.send_message(msg.chat.id, text)

def get_status(balance):
    if balance >= 100000:
        return '🌟 Легенда'
    elif balance >= 50000:
        return '💵 Миллионер'
    elif balance >= 10000:
        return '🏰 Барон'
    elif balance >= 5000:
        return '🏦 Инвестор'
    elif balance >= 1000:
        return '👑 Магнат'
    elif balance >= 500:
        return '💎 Богач'
    elif balance >= 200:
        return '💰 Середняк'
    elif balance >= 50:
        return '🪙 Новичок'
    elif balance >= 1:
        return '🕊️ Бедняга'
    else:
        return '💀 Банкрот'

# ============================================================
# БИЗНЕСЫ (упрощённо)
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🏢 Бизнесы')
def businesses_main(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🏢 БИЗНЕСЫ\n\nЭта функция в разработке. Скоро появится!')

# ============================================================
# ПОДПИСКА (упрощённо)
# ============================================================

@bot.message_handler(func=lambda m: m.text == '👑 Подписка')
def subscription_menu(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '👑 ПОДПИСКА\n\nЭта функция в разработке. Скоро появится!')

# ============================================================
# ИНВЕНТАРЬ (упрощённо)
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🎒 Инвентарь')
def inventory_menu(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🎒 ИНВЕНТАРЬ\n\nЭта функция в разработке. Скоро появится!')

# ============================================================
# МАГАЗИН (упрощённо)
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🛒 Магазин')
def shop_main(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🛒 МАГАЗИН\n\nЭта функция в разработке. Скоро появится!')

# ============================================================
# ТОРГОВЛЯ (упрощённо)
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🤝 Торговля')
def trade_menu(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🤝 ТОРГОВЛЯ\n\nЭта функция в разработке. Скоро появится!')

# ============================================================
# ПРЕМИУМ ПАСС (упрощённо)
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🎖️ Премиум Пасс')
def premium_pass_menu(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🎖️ ПРЕМИУМ ПАСС\n\nЭта функция в разработке. Скоро появится!')

# ============================================================
# КЛАНЫ (упрощённо)
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🏰 Кланы')
def clans_main(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🏰 КЛАНЫ\n\nЭта функция в разработке. Скоро появится!')

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