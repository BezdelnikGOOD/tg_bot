import os
import random
import hashlib
from datetime import datetime, timedelta
import telebot
import psycopg2
import psycopg2.extras
import json
import time

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
            admin_level INTEGER DEFAULT 0
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

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С БД =====
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

def create_user(user_id, nick, hashed_password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO users (id, game_nick, password, reg_date)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, nick, hashed_password, datetime.now().strftime('%d.%m.%Y %H:%M')))
    conn.commit()
    cur.close()
    conn.close()

def update_user(user_id, **kwargs):
    conn = get_db_connection()
    cur = conn.cursor()
    for key, value in kwargs.items():
        cur.execute(f'UPDATE users SET {key} = %s WHERE id = %s', (value, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_all_businesses():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM businesses ORDER BY id')
    businesses = cur.fetchall()
    cur.close()
    conn.close()
    return businesses

def get_business_by_id(biz_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM businesses WHERE id = %s', (biz_id,))
    biz = cur.fetchone()
    cur.close()
    conn.close()
    return biz

def buy_business(biz_id, user_id, nick):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE businesses SET owner_id = %s, owner_nick = %s, last_collected = %s WHERE id = %s', 
                (user_id, nick, datetime.now().isoformat(), biz_id))
    conn.commit()
    cur.close()
    conn.close()

def collect_business_income(biz_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE businesses SET last_collected = %s WHERE id = %s', 
                (datetime.now().isoformat(), biz_id))
    conn.commit()
    cur.close()
    conn.close()

def get_user_businesses(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM businesses WHERE owner_id = %s ORDER BY id', (user_id,))
    businesses = cur.fetchall()
    cur.close()
    conn.close()
    return businesses

def get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users')
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

def add_exp(user_id, amount):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT exp, level FROM users WHERE id = %s', (user_id,))
    exp, level = cur.fetchone()
    new_exp = exp + amount
    level_up = False
    while new_exp >= level * 50:
        new_exp -= level * 50
        level += 1
        level_up = True
        cur.execute('UPDATE users SET balance = balance + 50 WHERE id = %s', (user_id,))
    cur.execute('UPDATE users SET exp = %s, level = %s WHERE id = %s', (new_exp, level, user_id))
    conn.commit()
    cur.close()
    conn.close()
    return level_up, level

def get_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    total_users = cur.fetchone()[0]
    cur.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
    total_balance = cur.fetchone()[0]
    cur.execute('SELECT COALESCE(MAX(balance), 0) FROM users')
    max_balance = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM businesses WHERE owner_id IS NOT NULL')
    total_businesses_owned = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total_users, total_balance, max_balance, total_businesses_owned

def log_admin_action(user_id, action):
    with open('admin_logs.txt', 'a') as f:
        f.write(f'{datetime.now().strftime("%d.%m.%Y %H:%M")} | Админ ID: {user_id} | {action}\n')

# ===== СИСТЕМА УРОВНЕЙ АДМИНОВ =====
ADMIN_LEVELS = {
    1: {'name': 'Модератор', 'emoji': '🟢', 'permissions': ['ban', 'unban', 'give_coins', 'view_stats']},
    2: {'name': 'Старший модератор', 'emoji': '🔵', 'permissions': ['ban', 'unban', 'give_coins', 'view_stats', 'promote_moderator']},
    3: {'name': 'Администратор', 'emoji': '🟣', 'permissions': ['ban', 'unban', 'give_coins', 'view_stats', 'promote_moderator', 'manage_businesses']},
    4: {'name': 'Главный администратор', 'emoji': '🔴', 'permissions': ['ban', 'unban', 'give_coins', 'view_stats', 'promote_moderator', 'manage_businesses', 'manage_admins']},
    5: {'name': 'Создатель', 'emoji': '👑', 'permissions': ['all']},
}

def get_admin_level(user_id):
    user = get_user(user_id)
    if not user:
        return 0
    return user.get('admin_level', 0)

def get_admin_level_name(level):
    return ADMIN_LEVELS.get(level, {}).get('name', 'Нет ранга')

def get_admin_level_emoji(level):
    return ADMIN_LEVELS.get(level, {}).get('emoji', '🔘')

def has_permission(user_id, permission):
    level = get_admin_level(user_id)
    if level == 0:
        return False
    if level == 5:
        return True
    perms = ADMIN_LEVELS.get(level, {}).get('permissions', [])
    return permission in perms or 'all' in perms

# ===== КЛАВИАТУРЫ =====
auth_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
auth_keyboard.add('🔑 Войти', '✨ Зарегистрироваться')

main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_keyboard.add('👤 Профиль', '💰 Баланс')
main_keyboard.add('🎰 Играть', '📊 Топ игроков')
main_keyboard.add('🏷️ Все статусы', '🏢 Бизнесы')
main_keyboard.add('🚪 Выйти')

business_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
business_keyboard.add('🏢 Мои бизнесы', '📋 Все бизнесы')
business_keyboard.add('🔙 Назад')

admin_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
admin_keyboard.add('📊 Статистика', '👥 Список игроков')
admin_keyboard.add('👑 Назначить админа', '👑 Список админов')
admin_keyboard.add('📈 Изменить уровень', '➕ Выдать монеты')
admin_keyboard.add('➖ Забрать монеты', '🎁 Выдать опыт')
admin_keyboard.add('🔍 Найти игрока', '⏳ Бан/Разбан')
admin_keyboard.add('🔄 Сброс баланса', '📢 Рассылка')
admin_keyboard.add('🗑️ Удалить аккаунт', '📋 Логи админа')
admin_keyboard.add('🎲 Крутить рулетку', '💩 Наказать')
admin_keyboard.add('🎁 Случайный бонус', '🤡 Клоун-час')
admin_keyboard.add('📢 Смешная рассылка', '⬅️ Назад')

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_admin(user_id):
    return user_id == ADMIN_ID or get_admin_level(user_id) >= 1

def is_logged_in(user_id):
    user = get_user(user_id)
    return user and user['is_logged_in'] == 1

def is_banned(user_id):
    user = get_user(user_id)
    return user and user['is_banned'] == 1

def get_status(balance):
    if balance >= 100000: return '🌟 Легенда'
    elif balance >= 50000: return '💵 Миллионер'
    elif balance >= 10000: return '🏰 Барон'
    elif balance >= 5000: return '🏦 Инвестор'
    elif balance >= 1000: return '👑 Магнат'
    elif balance >= 500: return '💎 Богач'
    elif balance >= 200: return '💰 Середняк'
    elif balance >= 50: return '🪙 Новичок'
    elif balance >= 1: return '🕊️ Бедняга'
    else: return '💀 Банкрот'

def get_progress_bar(exp, level):
    needed = level * 50
    filled = min(exp, needed)
    percent = int((filled / needed) * 10) if needed > 0 else 0
    bar = '█' * percent + '░' * (10 - percent)
    return bar, filled, needed

def get_next_status(balance):
    statuses = [
        (0, '💀 Банкрот'), (1, '🕊️ Бедняга'), (50, '🪙 Новичок'),
        (200, '💰 Середняк'), (500, '💎 Богач'), (1000, '👑 Магнат'),
        (5000, '🏦 Инвестор'), (10000, '🏰 Барон'), (50000, '💵 Миллионер'),
        (100000, '🌟 Легенда')
    ]
    for threshold, name in statuses:
        if balance < threshold:
            return threshold, name
    return None

# ===== АВТОРИЗАЦИЯ =====
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Вы заблокированы.')
        return
    if get_user(user_id):
        if is_logged_in(user_id):
            bot.send_message(msg.chat.id, f'👋 Снова здесь, {msg.from_user.first_name}!', reply_markup=main_keyboard)
        else:
            bot.send_message(msg.chat.id, '🔐 Войдите или зарегистрируйтесь.', reply_markup=auth_keyboard)
        return
    bot.send_message(msg.chat.id, '👋 Добро пожаловать!', reply_markup=auth_keyboard)

@bot.message_handler(func=lambda m: m.text == '🔑 Войти')
def login_start(msg):
    bot.send_message(msg.chat.id, '🔐 Введите ник:')
    bot.register_next_step_handler(msg, login_nick)

def login_nick(msg):
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ник не найден.')
        return
    bot.send_message(msg.chat.id, '🔑 Введите пароль:')
    bot.register_next_step_handler(msg, login_password, nick)

def login_password(msg, nick):
    user = get_user_by_nick(nick)
    if not user or user['password'] != hash_password(msg.text.strip()):
        bot.send_message(msg.chat.id, '❌ Неверный пароль.')
        return
    update_user(user['id'], is_logged_in=1)
    bot.send_message(msg.chat.id, f'✅ Добро пожаловать, {nick}!', reply_markup=main_keyboard)

@bot.message_handler(func=lambda m: m.text == '✨ Зарегистрироваться')
def register_start(msg):
    bot.send_message(msg.chat.id, '📝 Придумайте ник:')
    bot.register_next_step_handler(msg, register_nick)

def register_nick(msg):
    nick = msg.text.strip()
    if get_user_by_nick(nick):
        bot.send_message(msg.chat.id, '❌ Ник занят.')
        return
    bot.send_message(msg.chat.id, '🔑 Придумайте пароль:')
    bot.register_next_step_handler(msg, register_password, nick)

def register_password(msg, nick):
    password = msg.text.strip()
    bot.send_message(msg.chat.id, '🔁 Повторите пароль:')
    bot.register_next_step_handler(msg, register_confirm, nick, password)

def register_confirm(msg, nick, password):
    if msg.text.strip() != password:
        bot.send_message(msg.chat.id, '❌ Пароли не совпадают.')
        return
    user_id = msg.from_user.id
    create_user(user_id, nick, hash_password(password))
    update_user(user_id, is_logged_in=1)
    bot.send_message(msg.chat.id, f'✅ Зарегистрирован, {nick}!', reply_markup=main_keyboard)

@bot.message_handler(func=lambda m: m.text == '🚪 Выйти')
def logout(msg):
    update_user(msg.from_user.id, is_logged_in=0)
    bot.send_message(msg.chat.id, '👋 Выход.', reply_markup=auth_keyboard)

# ===== ПРОФИЛЬ =====
@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    user = get_user(user_id)
    if not user:
        return
    bar, _, needed = get_progress_bar(user['exp'], user['level'])
    
    admin_level = get_admin_level(user_id)
    if admin_level > 0:
        status = f"{get_admin_level_emoji(admin_level)} {get_admin_level_name(admin_level)}"
    else:
        status = get_status(user['balance'])
    
    text = f'''
👤 ПРОФИЛЬ
Ник: {user['game_nick']}
Баланс: {user['balance']} монет
Уровень: {user['level']}
Опыт: {user['exp']}/{needed}
Прогресс: [{bar}]
Статус: {status}
'''
    if admin_level > 0:
        text += f"\n👑 Админ-ранг: {admin_level}"
    bot.send_message(msg.chat.id, text)

# ===== БАЛАНС =====
@bot.message_handler(func=lambda m: m.text == '💰 Баланс')
def balance(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    user = get_user(user_id)
    bot.send_message(msg.chat.id, f'💰 Баланс: {user["balance"]} монет')

# ===== ИГРА =====
@bot.message_handler(func=lambda m: m.text == '🎰 Играть')
def game(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    user = get_user(user_id)
    if user['balance'] < 10:
        bot.send_message(msg.chat.id, '❌ Нужно 10 монет.')
        return
    update_user(user_id, balance=user['balance'] - 10)
    win = random.choice([0, 1])
    if win:
        update_user(user_id, balance=user['balance'] - 10 + 25)
        add_exp(user_id, 10)
        bot.send_message(msg.chat.id, '🎉 Выиграл! +25 монет, +10 опыта')
    else:
        add_exp(user_id, 2)
        bot.send_message(msg.chat.id, '😢 Проиграл. -10 монет, +2 опыта')

# ===== ТОП =====
@bot.message_handler(func=lambda m: m.text == '📊 Топ игроков')
def top_players(msg):
    if not is_logged_in(msg.from_user.id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT game_nick, balance FROM users ORDER BY balance DESC LIMIT 10')
    players = cur.fetchall()
    cur.close()
    conn.close()
    text = '🏆 ТОП-10\n\n'
    for i, (nick, balance) in enumerate(players, 1):
        text += f'{i}. {nick} — {balance} монет\n'
    bot.send_message(msg.chat.id, text)

# ===== ВСЕ СТАТУСЫ =====
@bot.message_handler(func=lambda m: m.text == '🏷️ Все статусы')
def all_statuses(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    user = get_user(user_id)
    balance = user['balance']
    status = get_status(balance)
    next_data = get_next_status(balance)
    text = f'''
🏷️ СТАТУСЫ
💀 Банкрот: 0
🕊️ Бедняга: 1-49
🪙 Новичок: 50-199
💰 Середняк: 200-499
💎 Богач: 500-999
👑 Магнат: 1000-4999
🏦 Инвестор: 5000-9999
🏰 Барон: 10000-49999
💵 Миллионер: 50000-99999
🌟 Легенда: 100000+

Твой статус: {status}
'''
    if next_data:
        threshold, name = next_data
        text += f'До {name}: {threshold - balance} монет'
    bot.send_message(msg.chat.id, text)

# ===== БИЗНЕСЫ =====
@bot.message_handler(func=lambda m: m.text == '🏢 Бизнесы')
def businesses_main(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    text = '🏢 БИЗНЕСЫ\nВыберите действие:'
    bot.send_message(msg.chat.id, text, reply_markup=business_keyboard)

@bot.message_handler(func=lambda m: m.text == '📋 Все бизнесы')
def show_all_businesses(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    all_biz = get_all_businesses()
    text = '📋 ВСЕ БИЗНЕСЫ\n\n'
    
    for biz in all_biz:
        status = '🟢 СВОБОДЕН' if biz['owner_id'] is None else f'🔒 {biz["owner_nick"]}'
        text += f"{biz['id']}. {biz['name']} — {biz['price']} монет ({biz['income']}/час) {status}\n"
    
    text += '\nВведите номер бизнеса для покупки (1-50):'
    bot.send_message(msg.chat.id, text)
    bot.register_next_step_handler(msg, process_buy_business)

def process_buy_business(msg):
    user_id = msg.from_user.id
    try:
        biz_id = int(msg.text.strip())
        if biz_id < 1 or biz_id > 50:
            bot.send_message(msg.chat.id, '❌ Введите число от 1 до 50.')
            return
    except:
        bot.send_message(msg.chat.id, '❌ Введите номер бизнеса (1-50).')
        return
    
    biz = get_business_by_id(biz_id)
    if not biz:
        bot.send_message(msg.chat.id, '❌ Бизнес не найден.')
        return
    
    if biz['owner_id'] is not None:
        bot.send_message(msg.chat.id, f'🔒 {biz["name"]} уже принадлежит {biz["owner_nick"]}.')
        return
    
    user = get_user(user_id)
    if user['balance'] < biz['price']:
        bot.send_message(msg.chat.id, f'❌ Не хватает {biz["price"] - user["balance"]} монет.')
        return
    
    update_user(user_id, balance=user['balance'] - biz['price'])
    buy_business(biz_id, user_id, user['game_nick'])
    bot.send_message(msg.chat.id, f'✅ Вы купили {biz["name"]}! Доход: {biz["income"]} монет в час.')
    
    if is_admin(user_id):
        bot.send_message(ADMIN_ID, f'👑 {user["game_nick"]} купил {biz["name"]}!')

@bot.message_handler(func=lambda m: m.text == '🏢 Мои бизнесы')
def show_my_businesses(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    my_biz = get_user_businesses(user_id)
    if not my_biz:
        bot.send_message(msg.chat.id, '📭 У вас нет бизнесов.')
        return
    
    text = '🏢 МОИ БИЗНЕСЫ\n\n'
    for biz in my_biz:
        last = datetime.fromisoformat(biz['last_collected']) if biz['last_collected'] else datetime.now()
        now = datetime.now()
        hours = (now - last).total_seconds() / 3600
        income = int(biz['income'] * hours) if hours > 0 else 0
        text += f"{biz['id']}. {biz['name']} — {biz['income']}/час\n   Накоплено: {income} монет\n\n"
    
    text += 'Введите номер бизнеса для сбора дохода:'
    bot.send_message(msg.chat.id, text)
    bot.register_next_step_handler(msg, process_collect_income)

def process_collect_income(msg):
    user_id = msg.from_user.id
    try:
        biz_id = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, '❌ Введите номер бизнеса.')
        return
    
    biz = get_business_by_id(biz_id)
    if not biz or biz['owner_id'] != user_id:
        bot.send_message(msg.chat.id, '❌ Это не ваш бизнес.')
        return
    
    last = datetime.fromisoformat(biz['last_collected']) if biz['last_collected'] else datetime.now()
    now = datetime.now()
    hours = (now - last).total_seconds() / 3600
    income = int(biz['income'] * hours)
    
    if income < 1:
        bot.send_message(msg.chat.id, '⏳ Доход ещё не накопился.')
        return
    
    collect_business_income(biz_id)
    update_user(user_id, balance=get_user(user_id)['balance'] + income)
    bot.send_message(msg.chat.id, f'💰 Собрано {income} монет с {biz["name"]}!')

@bot.message_handler(func=lambda m: m.text == '🔙 Назад')
def back_from_business(msg):
    user_id = msg.from_user.id
    if is_logged_in(user_id):
        bot.send_message(msg.chat.id, '🏠 Главное меню', reply_markup=main_keyboard)
    else:
        bot.send_message(msg.chat.id, '🔐 Войдите', reply_markup=auth_keyboard)

# ===== АДМИН-ПАНЕЛЬ =====
@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    user_id = msg.from_user.id
    if not is_admin(user_id):
        bot.send_message(msg.chat.id, '❌ Доступ запрещён.')
        return
    bot.send_message(msg.chat.id, '🔐 Админ-панель', reply_markup=admin_keyboard)

@bot.message_handler(func=lambda m: m.text == '⬅️ Назад' and is_admin(m.from_user.id))
def back_to_main(msg):
    bot.send_message(msg.chat.id, '🏠 Главное меню', reply_markup=main_keyboard)

# 1. Статистика
@bot.message_handler(func=lambda m: m.text == '📊 Статистика' and is_admin(m.from_user.id))
def stats(msg):
    total_users, total_balance, max_balance, total_businesses = get_stats()
    text = f'''
📊 СТАТИСТИКА
👥 Игроков: {total_users}
💰 Общий баланс: {total_balance:,}
🏆 Макс. баланс: {max_balance:,}
🏢 Бизнесов куплено: {total_businesses}/50
'''
    bot.send_message(msg.chat.id, text)

# 2. Список игроков
@bot.message_handler(func=lambda m: m.text == '👥 Список игроков' and is_admin(m.from_user.id))
def players_list(msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT game_nick, balance FROM users ORDER BY balance DESC LIMIT 10')
    players = cur.fetchall()
    cur.close()
    conn.close()
    text = '👥 ТОП-10 ИГРОКОВ\n\n'
    for i, (nick, balance) in enumerate(players, 1):
        text += f'{i}. {nick} — {balance} монет\n'
    bot.send_message(msg.chat.id, text)

# 3. Назначить админа
@bot.message_handler(func=lambda m: m.text == '👑 Назначить админа' and is_admin(m.from_user.id))
def promote_admin_start(msg):
    if not has_permission(msg.from_user.id, 'manage_admins'):
        bot.send_message(msg.chat.id, '❌ У вас нет прав.')
        return
    bot.send_message(msg.chat.id, '✏️ Введите ник и уровень (1-5):\nПример: Алексей 3')
    bot.register_next_step_handler(msg, promote_admin_process)

def promote_admin_process(msg):
    try:
        parts = msg.text.split()
        nick, level = parts[0], int(parts[1])
        if level < 1 or level > 5:
            bot.send_message(msg.chat.id, '❌ Уровень от 1 до 5.')
            return
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        update_user(user['id'], admin_level=level)
        bot.send_message(msg.chat.id, f'✅ {nick} теперь {get_admin_level_name(level)} {get_admin_level_emoji(level)}')
        log_admin_action(msg.from_user.id, f'Назначил {nick} на уровень {level}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник уровень')

# 4. Список админов
@bot.message_handler(commands=['admins'])
@bot.message_handler(func=lambda m: m.text == '👑 Список админов' and is_admin(m.from_user.id))
def list_admins(msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT game_nick, admin_level, balance FROM users WHERE admin_level > 0 ORDER BY admin_level DESC, balance DESC')
    admins = cur.fetchall()
    cur.close()
    conn.close()
    
    if not admins:
        bot.send_message(msg.chat.id, '📭 Нет администраторов.')
        return
    
    text = '👑 СПИСОК АДМИНИСТРАТОРОВ\n\n'
    for nick, level, balance in admins:
        emoji = get_admin_level_emoji(level)
        name = get_admin_level_name(level)
        text += f'{emoji} {nick} — {name} (уровень {level})\n'
        text += f'   💰 Баланс: {balance:,} монет\n\n'
    bot.send_message(msg.chat.id, text)

# 5. Изменить уровень
@bot.message_handler(func=lambda m: m.text == '📈 Изменить уровень' and is_admin(m.from_user.id))
def change_level_start(msg):
    if not has_permission(msg.from_user.id, 'give_coins'):
        bot.send_message(msg.chat.id, '❌ У вас нет прав.')
        return
    bot.send_message(msg.chat.id, '✏️ Введите ник и уровень:\nПример: Алексей 5')
    bot.register_next_step_handler(msg, change_level_process)

def change_level_process(msg):
    try:
        parts = msg.text.split()
        nick, new_level = parts[0], int(parts[1])
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        update_user(user['id'], level=new_level)
        bot.send_message(msg.chat.id, f'✅ Уровень {nick} изменён на {new_level}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник уровень')

# 6. Выдать монеты
@bot.message_handler(func=lambda m: m.text == '➕ Выдать монеты' and is_admin(m.from_user.id))
def give_coins_start(msg):
    if not has_permission(msg.from_user.id, 'give_coins'):
        bot.send_message(msg.chat.id, '❌ У вас нет прав.')
        return
    bot.send_message(msg.chat.id, '✏️ Введите ник и сумму:')
    bot.register_next_step_handler(msg, give_coins_process)

def give_coins_process(msg):
    try:
        parts = msg.text.split()
        nick, amount = parts[0], int(parts[1])
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        update_user(user['id'], balance=user['balance'] + amount)
        bot.send_message(msg.chat.id, f'✅ {nick} получил {amount} монет.')
        log_admin_action(msg.from_user.id, f'Выдал {amount} монет {nick}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник сумма')

# 7. Забрать монеты
@bot.message_handler(func=lambda m: m.text == '➖ Забрать монеты' and is_admin(m.from_user.id))
def take_coins_start(msg):
    if not has_permission(msg.from_user.id, 'give_coins'):
        bot.send_message(msg.chat.id, '❌ У вас нет прав.')
        return
    bot.send_message(msg.chat.id, '✏️ Введите ник и сумму:')
    bot.register_next_step_handler(msg, take_coins_process)

def take_coins_process(msg):
    try:
        parts = msg.text.split()
        nick, amount = parts[0], int(parts[1])
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        new_balance = max(0, user['balance'] - amount)
        update_user(user['id'], balance=new_balance)
        bot.send_message(msg.chat.id, f'✅ У {nick} списано {amount} монет.')
        log_admin_action(msg.from_user.id, f'Списал {amount} монет у {nick}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник сумма')

# 8. Выдать опыт
@bot.message_handler(func=lambda m: m.text == '🎁 Выдать опыт' and is_admin(m.from_user.id))
def give_exp_start(msg):
    if not has_permission(msg.from_user.id, 'give_coins'):
        bot.send_message(msg.chat.id, '❌ У вас нет прав.')
        return
    bot.send_message(msg.chat.id, '✏️ Введите ник и опыт:')
    bot.register_next_step_handler(msg, give_exp_process)

def give_exp_process(msg):
    try:
        parts = msg.text.split()
        nick, amount = parts[0], int(parts[1])
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        add_exp(user['id'], amount)
        bot.send_message(msg.chat.id, f'✅ {nick} получил {amount} опыта.')
        log_admin_action(msg.from_user.id, f'Выдал {amount} опыта {nick}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник опыт')

# 9. Найти игрока
@bot.message_handler(func=lambda m: m.text == '🔍 Найти игрока' and is_admin(m.from_user.id))
def find_player_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник или ID:')
    bot.register_next_step_handler(msg, find_player_process)

def find_player_process(msg):
    query = msg.text.strip()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if query.isdigit():
        cur.execute('SELECT * FROM users WHERE id = %s', (int(query),))
    else:
        cur.execute('SELECT * FROM users WHERE game_nick ILIKE %s', (f'%{query}%',))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user:
        bot.send_message(msg.chat.id, '❌ Игрок не найден.')
        return
    text = f'''
📋 ИНФОРМАЦИЯ
👤 Ник: {user['game_nick']}
🆔 ID: {user['id']}
💰 Баланс: {user['balance']} монет
📈 Уровень: {user['level']}
⭐ Опыт: {user['exp']}
👑 Роль: {user['role']}
🚫 Бан: {"Да" if user['is_banned'] else "Нет"}
'''
    bot.send_message(msg.chat.id, text)

# 10. Бан/Разбан
@bot.message_handler(func=lambda m: m.text == '⏳ Бан/Разбан' and is_admin(m.from_user.id))
def ban_player_start(msg):
    if not has_permission(msg.from_user.id, 'ban'):
        bot.send_message(msg.chat.id, '❌ У вас нет прав.')
        return
    bot.send_message(msg.chat.id, '✏️ Введите ник:')
    bot.register_next_step_handler(msg, ban_player_process)

def ban_player_process(msg):
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, '❌ Игрок не найден.')
        return
    new_status = 0 if user['is_banned'] else 1
    status_text = 'забанен' if new_status == 1 else 'разбанен'
    update_user(user['id'], is_banned=new_status)
    bot.send_message(msg.chat.id, f'✅ {nick} {status_text}!')
    log_admin_action(msg.from_user.id, f'{status_text} {nick}')

# 11. Сброс баланса
@bot.message_handler(func=lambda m: m.text == '🔄 Сброс баланса' and is_admin(m.from_user.id))
def reset_balance_all(msg):
    if not has_permission(msg.from_user.id, 'give_coins'):
        bot.send_message(msg.chat.id, '❌ У вас нет прав.')
        return
    bot.send_message(msg.chat.id, '⚠️ Напишите ДА для подтверждения:')
    bot.register_next_step_handler(msg, reset_balance_confirm)

def reset_balance_confirm(msg):
    if msg.text.upper() == 'ДА':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('UPDATE users SET balance = 0')
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(msg.chat.id, '✅ Баланс всех игроков обнулён.')
        log_admin_action(msg.from_user.id, 'Сброс баланса всем')

# 12. Рассылка
@bot.message_handler(func=lambda m: m.text == '📢 Рассылка' and is_admin(m.from_user.id))
def broadcast_start(msg):
    if not has_permission(msg.from_user.id, 'give_coins'):
        bot.send_message(msg.chat.id, '❌ У вас нет прав.')
        return
    bot.send_message(msg.chat.id, '✏️ Введите текст:')
    bot.register_next_step_handler(msg, broadcast_process)

def broadcast_process(msg):
    text = msg.text
    users = get_all_users()
    if not users:
        bot.send_message(msg.chat.id, '❌ Нет пользователей.')
        return
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f'📢 {text}')
            sent += 1
        except:
            pass
    bot.send_message(msg.chat.id, f'✅ Отправлено {sent} пользователям.')
    log_admin_action(msg.from_user.id, f'Рассылка: {text[:30]}...')

# 13. Удалить аккаунт
@bot.message_handler(func=lambda m: m.text == '🗑️ Удалить аккаунт' and is_admin(m.from_user.id))
def delete_account_start(msg):
    if not has_permission(msg.from_user.id, 'manage_admins'):
        bot.send_message(msg.chat.id, '❌ У вас нет прав.')
        return
    bot.send_message(msg.chat.id, '⚠️ Введите ник для удаления:')
    bot.register_next_step_handler(msg, delete_account_process)

def delete_account_process(msg):
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, '❌ Игрок не найден.')
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM users WHERE game_nick = %s', (nick,))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(msg.chat.id, f'🗑️ Аккаунт {nick} удалён.')
    log_admin_action(msg.from_user.id, f'Удалил {nick}')

# 14. Логи админа
@bot.message_handler(func=lambda m: m.text == '📋 Логи админа' and is_admin(m.from_user.id))
def show_logs(msg):
    try:
        with open('admin_logs.txt', 'r') as f:
            logs = f.read().splitlines()
            last_logs = logs[-20:] if len(logs) > 20 else logs
            text = '📋 Последние 20 действий:\n\n' + '\n'.join(last_logs)
            bot.send_message(msg.chat.id, text)
    except:
        bot.send_message(msg.chat.id, '📭 Логов пока нет.')

# ===== ПРИКОЛЫ ДЛЯ АДМИНОВ =====

# 15. Рулетка
@bot.message_handler(func=lambda m: m.text == '🎲 Крутить рулетку' and is_admin(m.from_user.id))
def admin_roulette(msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, game_nick, balance FROM users ORDER BY RANDOM() LIMIT 1')
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if not user:
        bot.send_message(msg.chat.id, '❌ Нет игроков.')
        return
    
    user_id, nick, balance = user
    outcome = random.choice(['+', '-', '🎉', '💀'])
    amount = random.randint(10, 500)
    
    if outcome == '+':
        update_user(user_id, balance=balance + amount)
        text = f'🎲 РУЛЕТКА!\nИгрок: {nick}\nРезультат: +{amount} монет! 🎉'
    elif outcome == '-':
        new_balance = max(0, balance - amount)
        update_user(user_id, balance=new_balance)
        text = f'🎲 РУЛЕТКА!\nИгрок: {nick}\nРезультат: -{amount} монет! 💀'
    elif outcome == '🎉':
        bonus = random.randint(100, 1000)
        update_user(user_id, balance=balance + bonus)
        text = f'🎲 РУЛЕТКА!\nИгрок: {nick}\nДЖЕКПОТ! +{bonus} монет! 🎉🎉🎉'
    else:
        new_balance = max(0, balance - amount * 2)
        update_user(user_id, balance=new_balance)
        text = f'🎲 РУЛЕТКА!\nИгрок: {nick}\nБАНКРОТ! -{amount*2} монет! 💀💀💀'
    
    bot.send_message(msg.chat.id, text)
    log_admin_action(msg.from_user.id, f'Рулетка: {nick}')

# 16. Наказание
@bot.message_handler(func=lambda m: m.text == '💩 Наказать' and is_admin(m.from_user.id))
def punish_player(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник:')
    bot.register_next_step_handler(msg, punish_process)

punishments = [
    '💩 {nick} моет туалеты! -10 монет',
    '🤡 {nick} главный клоун! -5 монет',
    '🐸 {nick} превращён в лягушку! -15 монет',
    '🧹 {nick} убирает бота! -7 монет',
    '🍕 {nick} разносит пиццу! -12 монет',
]

def punish_process(msg):
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, '❌ Игрок не найден.')
        return
    
    punishment = random.choice(punishments).format(nick=nick)
    amount = random.randint(5, 25)
    new_balance = max(0, user['balance'] - amount)
    update_user(user['id'], balance=new_balance)
    bot.send_message(msg.chat.id, f'🔨 {punishment}\n💰 Баланс: {new_balance} монет')
    log_admin_action(msg.from_user.id, f'Наказал {nick}')

# 17. Случайный бонус
@bot.message_handler(func=lambda m: m.text == '🎁 Случайный бонус' and is_admin(m.from_user.id))
def random_bonus(msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, game_nick, balance FROM users ORDER BY RANDOM() LIMIT 1')
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if not user:
        bot.send_message(msg.chat.id, '❌ Нет игроков.')
        return
    
    user_id, nick, balance = user
    bonus = random.randint(50, 500)
    update_user(user_id, balance=balance + bonus)
    messages = [
        f'🎁 {nick} нашёл клад! +{bonus} монет! 💰',
        f'🎁 {nick} выиграл в лотерею! +{bonus} монет! 🎉',
        f'🎁 {nick} получил бонус от админа! +{bonus} монет! 👑',
    ]
    bot.send_message(msg.chat.id, random.choice(messages))
    log_admin_action(msg.from_user.id, f'Бонус {nick} +{bonus}')

# 18. Клоун-час
@bot.message_handler(func=lambda m: m.text == '🤡 Клоун-час' and is_admin(m.from_user.id))
def clown_hour(msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, game_nick FROM users')
    users = cur.fetchall()
    cur.close()
    conn.close()
    
    if not users:
        bot.send_message(msg.chat.id, '❌ Нет игроков.')
        return
    
    clown_nicks = ['🤡Клоун', '🃏Шут', '😜Смешной', '🤪Безумный', '🎪Циркач']
    
    for user_id, old_nick in users:
        new_nick = random.choice(clown_nicks) + str(random.randint(1, 999))
        update_user(user_id, game_nick=new_nick)
    
    bot.send_message(msg.chat.id, '🤡 КЛОУН-ЧАС! Все ники заменены! 🎪')
    log_admin_action(msg.from_user.id, 'Клоун-час')

# 19. Смешная рассылка
@bot.message_handler(func=lambda m: m.text == '📢 Смешная рассылка' and is_admin(m.from_user.id))
def funny_broadcast(msg):
    jokes = [
        '😂 Почему бот пошёл к психологу? У него был баг в отношениях!',
        '🤣 Что сказал сервер боту? Ты меня перегружаешь!',
        '😅 Бот стал сомелье — разбирается в багах!',
        '🤪 Бот купил новый процессор — думает медленнее!',
    ]
    joke = random.choice(jokes)
    users = get_all_users()
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f'📢 {joke}')
            sent += 1
        except:
            pass
    bot.send_message(msg.chat.id, f'✅ Отправлено {sent} пользователям!')
    log_admin_action(msg.from_user.id, 'Смешная рассылка')

# ===== ЗАПУСК =====
if __name__ == '__main__':
    print('✅ Бот запущен!')
    bot.remove_webhook()
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f'❌ Ошибка: {e}. Перезапуск...')
            time.sleep(5)
