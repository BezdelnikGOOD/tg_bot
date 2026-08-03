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
    
    # Таблица пользователей
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
            role TEXT DEFAULT 'user'
        )
    ''')
    
    # Таблица бизнесов (глобальная)
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
    
    # Проверяем, есть ли бизнесы
    cur.execute('SELECT COUNT(*) FROM businesses')
    count = cur.fetchone()[0]
    
    if count == 0:
        # Вставляем 50 бизнесов
        businesses = [
            # ЕДА
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
            # ТОРГОВЛЯ
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
            # ПРОИЗВОДСТВО
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
            # РАЗВЛЕЧЕНИЯ
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
            # МЕГА-БИЗНЕСЫ
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

# ===== ФУНКЦИИ РАБОТЫ С БД =====
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

# ===== КЛАВИАТУРЫ =====
auth_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
auth_keyboard.add('🔑 Войти', '✨ Зарегистрироваться')

main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_keyboard.add('👤 Профиль', '💰 Баланс')
main_keyboard.add('🎰 Играть', '📊 Топ игроков')
main_keyboard.add('🏷️ Все статусы', '🏢 Бизнесы')
main_keyboard.add('🚪 Выйти')

admin_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
admin_keyboard.add('📊 Статистика', '👥 Список игроков')
admin_keyboard.add('➕ Выдать монеты', '➖ Забрать монеты')
admin_keyboard.add('📢 Рассылка', '⬅️ Назад')

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_admin(user_id):
    return user_id == ADMIN_ID

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
    status = '👑 Админ' if is_admin(user_id) else get_status(user['balance'])
    text = f'''
👤 ПРОФИЛЬ
Ник: {user['game_nick']}
Баланс: {user['balance']} монет
Уровень: {user['level']}
Опыт: {user['exp']}/{needed}
Прогресс: [{bar}]
Статус: {status}
'''
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
def businesses_menu(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    my_biz = get_user_businesses(user_id)
    all_biz = get_all_businesses()
    
    text = f'🏢 БИЗНЕСЫ\n💰 Баланс: {user["balance"]} монет\n\n'
    text += '📋 Категории:\n'
    text += '🍔 Еда (1-10) | 🛍️ Торговля (11-20)\n'
    text += '🏭 Производство (21-30) | 🎮 Развлечения (31-40)\n'
    text += '🌌 Мега-бизнесы (41-50)\n\n'
    text += f'🏢 Мои бизнесы: {len(my_biz)}\n'
    
    if my_biz:
        total_income = sum(b['income'] for b in my_biz)
        text += f'💰 Доход в час: {total_income} монет\n'
    
    text += '\nВведите номер бизнеса для покупки (1-50):'
    bot.send_message(msg.chat.id, text)
    bot.register_next_step_handler(msg, business_action)

def business_action(msg):
    user_id = msg.from_user.id
    try:
        biz_id = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, '❌ Введите номер от 1 до 50.')
        return
    
    biz = get_business_by_id(biz_id)
    if not biz:
        bot.send_message(msg.chat.id, '❌ Бизнес не найден.')
        return
    
    user = get_user(user_id)
    
    if biz['owner_id'] is None:
        # Бизнес свободен
        if user['balance'] < biz['price']:
            bot.send_message(msg.chat.id, f'❌ Не хватает {biz["price"] - user["balance"]} монет.')
            return
        # Покупка
        update_user(user_id, balance=user['balance'] - biz['price'])
        buy_business(biz_id, user_id, user['game_nick'])
        bot.send_message(msg.chat.id, f'✅ Вы купили {biz["name"]}! Доход: {biz["income"]} монет в час.')
        
        # Уведомление всем админам
        if is_admin(user_id):
            bot.send_message(ADMIN_ID, f'👑 {user["game_nick"]} купил {biz["name"]}!')
        
        return
    
    elif biz['owner_id'] == user_id:
        # Сбор дохода
        if biz['last_collected']:
            last = datetime.fromisoformat(biz['last_collected'])
            now = datetime.now()
            hours = (now - last).total_seconds() / 3600
            income = int(biz['income'] * hours)
            if income < 1:
                bot.send_message(msg.chat.id, '⏳ Слишком рано. Доход ещё не накопился.')
                return
            collect_business_income(biz_id)
            update_user(user_id, balance=user['balance'] + income)
            bot.send_message(msg.chat.id, f'💰 Собрано {income} монет с {biz["name"]}!')
        else:
            collect_business_income(biz_id)
            bot.send_message(msg.chat.id, f'✅ Начало сбора дохода с {biz["name"]}!')
    else:
        bot.send_message(msg.chat.id, f'🔒 {biz["name"]} принадлежит {biz["owner_nick"]}')

# ===== АДМИН-ПАНЕЛЬ =====
@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, '❌ Доступ запрещён.')
        return
    bot.send_message(msg.chat.id, '🔐 Админ-панель', reply_markup=admin_keyboard)

@bot.message_handler(func=lambda m: m.text == '⬅️ Назад' and is_admin(m.from_user.id))
def back_to_main(msg):
    bot.send_message(msg.chat.id, '🏠 Главное меню', reply_markup=main_keyboard)

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

@bot.message_handler(func=lambda m: m.text == '➕ Выдать монеты' and is_admin(m.from_user.id))
def give_coins_start(msg):
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
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник сумма')

@bot.message_handler(func=lambda m: m.text == '➖ Забрать монеты' and is_admin(m.from_user.id))
def take_coins_start(msg):
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
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник сумма')

@bot.message_handler(func=lambda m: m.text == '📢 Рассылка' and is_admin(m.from_user.id))
def broadcast_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите текст:')
    bot.register_next_step_handler(msg, broadcast_process)

def broadcast_process(msg):
    text = msg.text
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users')
    users = cur.fetchall()
    cur.close()
    conn.close()
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f'📢 {text}')
            sent += 1
        except:
            pass
    bot.send_message(msg.chat.id, f'✅ Отправлено {sent} пользователям.')

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
