import os
import random
import hashlib
import json
import time
from datetime import datetime, timedelta
import telebot
import psycopg2
import psycopg2.extras

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
            notifications INTEGER DEFAULT 1
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

# ===== ФУНКЦИИ БАЗЫ ДАННЫХ =====
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

def get_business_by_id(biz_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM businesses WHERE id = %s', (biz_id,))
    biz = cur.fetchone()
    cur.close()
    conn.close()
    return biz

def get_user_businesses(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM businesses WHERE owner_id = %s ORDER BY id', (user_id,))
    businesses = cur.fetchall()
    cur.close()
    conn.close()
    return businesses

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

def get_inventory(user_id):
    user = get_user(user_id)
    if not user or not user.get('inventory'):
        return []
    return json.loads(user['inventory'])

def save_inventory(user_id, inventory):
    update_user(user_id, inventory=json.dumps(inventory))

def add_item(user_id, item_id, count=1):
    inventory = get_inventory(user_id)
    for item in inventory:
        if item['id'] == item_id:
            item['count'] += count
            save_inventory(user_id, inventory)
            return
    inventory.append({'id': item_id, 'count': count})
    save_inventory(user_id, inventory)

def remove_item(user_id, item_id, count=1):
    inventory = get_inventory(user_id)
    for i, item in enumerate(inventory):
        if item['id'] == item_id:
            item['count'] -= count
            if item['count'] <= 0:
                inventory.pop(i)
            save_inventory(user_id, inventory)
            return True
    return False

def get_energy(user_id):
    user = get_user(user_id)
    return user.get('energy', 50) if user else 50

def update_energy(user_id, amount):
    user = get_user(user_id)
    if not user:
        return
    energy = max(0, min(user.get('max_energy', 50), user.get('energy', 50) + amount))
    update_user(user_id, energy=energy)
    return energy

def get_user_bonuses(user_id):
    user = get_user(user_id)
    if not user:
        return 1.0, 1.0, 0.0
    
    coin_multiplier = 1.0
    exp_multiplier = 1.0
    shop_discount = 0.0
    
    vip_level = user.get('vip_level', 0)
    if vip_level >= 1:
        coin_multiplier += 0.05
        exp_multiplier += 0.05
    if vip_level >= 2:
        coin_multiplier += 0.10
        exp_multiplier += 0.05
        shop_discount = 0.10
    if vip_level >= 3:
        coin_multiplier += 0.10
        exp_multiplier += 0.10
        shop_discount = 0.20
    if vip_level >= 4:
        coin_multiplier += 0.15
        exp_multiplier += 0.10
        shop_discount = 0.30
    if vip_level >= 5:
        coin_multiplier += 0.20
        exp_multiplier += 0.20
        shop_discount = 0.40
    
    return coin_multiplier, exp_multiplier, shop_discount

def get_subscription_status_text(user_id):
    user = get_user(user_id)
    if not user:
        return '🟡 Нет подписки'
    level = user.get('vip_level', 0)
    end = user.get('vip_end')
    if level == 0 or not end:
        return '🟡 Нет подписки'
    try:
        end_date = datetime.fromisoformat(end)
        if datetime.now() > end_date:
            return '🟡 Нет подписки'
        remaining = end_date - datetime.now()
        return f'VIP {level} — осталось {remaining.days} дн.'
    except:
        return '🟡 Нет подписки'

def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    user = get_user(user_id)
    if not user:
        return False
    return user.get('admin_level', 0) >= 1

def is_logged_in(user_id):
    user = get_user(user_id)
    return user and user['is_logged_in'] == 1

def is_banned(user_id):
    user = get_user(user_id)
    return user and user['is_banned'] == 1

# ===== СИСТЕМА УВЕДОМЛЕНИЙ =====
def notify_all_players(text, parse_mode='Markdown'):
    """Отправляет уведомление всем активным игрокам"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE is_logged_in = 1 AND notifications = 1')
    users = cur.fetchall()
    cur.close()
    conn.close()
    
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

def format_player_name(nick):
    return f'@{nick}'

# ===== КЛАВИАТУРЫ =====
auth_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
auth_keyboard.add('🔑 Войти', '✨ Зарегистрироваться')

main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_keyboard.add('👤 Профиль', '💰 Баланс')
main_keyboard.add('🎰 Играть', '📊 Топ игроков')
main_keyboard.add('🏷️ Все статусы', '🏢 Бизнесы')
main_keyboard.add('👑 Подписка', '🎒 Инвентарь')
main_keyboard.add('🛒 Магазин', '🤝 Торговля')
main_keyboard.add('🎖️ Battle Pass', '🚪 Выйти')

business_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
business_keyboard.add('🏢 Мои бизнесы', '📋 Все бизнесы')
business_keyboard.add('🔙 Назад')

shop_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
shop_keyboard.add('🍔 Еда', '⚔️ Оружие', '🛡️ Броня')
shop_keyboard.add('🎟️ Билеты', '💎 Редкие', '📜 Свитки')
shop_keyboard.add('👑 Premium', '🔙 Назад')

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
    
    user = get_user(user_id)
    if user:
        if is_logged_in(user_id):
            bot.send_message(msg.chat.id, f'👋 Снова здесь, {user["game_nick"]}!', reply_markup=main_keyboard)
        else:
            bot.send_message(msg.chat.id, f'🔐 У вас уже есть аккаунт ({user["game_nick"]}). Войдите.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '👋 Добро пожаловать! Зарегистрируйтесь или войдите.', reply_markup=auth_keyboard)

@bot.message_handler(func=lambda m: m.text == '🔑 Войти')
def login_start(msg):
    user_id = msg.from_user.id
    if not get_user(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не зарегистрированы! Нажмите «Зарегистрироваться».')
        return
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Вы заблокированы.')
        return
    if is_logged_in(user_id):
        bot.send_message(msg.chat.id, '✅ Вы уже авторизованы!', reply_markup=main_keyboard)
        return
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
    user_id = msg.from_user.id
    if get_user(user_id):
        bot.send_message(msg.chat.id, '❌ У вас уже есть аккаунт! Войдите через «Войти».')
        return
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
    update_user(user_id, game_nick=nick, password=hash_password(password), 
                reg_date=datetime.now().strftime('%d.%m.%Y %H:%M'), is_logged_in=1)
    bot.send_message(msg.chat.id, f'✅ Зарегистрирован, {nick}!', reply_markup=main_keyboard)
    
    # Уведомление всем
    notify_all_players(f'🎉 *Новый игрок*: {format_player_name(nick)} присоединился к боту!')

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
    status = get_status(user['balance'])
    sub_status = get_subscription_status_text(user_id)
    
    text = f'''
👤 **ПРОФИЛЬ**
📛 Ник: {user['game_nick']}
💰 Баланс: {user['balance']} монет
📈 Уровень: {user['level']}
⭐ Опыт: {user['exp']}/{needed}
📊 Прогресс: [{bar}]
🏷️ Статус: {status}
{sub_status}
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

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
    energy = get_energy(user_id)
    if energy < 5:
        bot.send_message(msg.chat.id, f'❌ Недостаточно энергии! Нужно 5. Сейчас: {energy}/50.')
        return
    
    update_energy(user_id, -5)
    
    coin_multiplier, exp_multiplier, _ = get_user_bonuses(user_id)
    
    win = random.choice([0, 1])
    if win:
        base_coins = 25
        base_exp = 10
        bonus_coins = int(base_coins * coin_multiplier - base_coins)
        bonus_exp = int(base_exp * exp_multiplier - base_exp)
        total_coins = base_coins + bonus_coins
        total_exp = base_exp + bonus_exp
        
        update_user(user_id, balance=user['balance'] + total_coins)
        add_exp(user_id, total_exp)
        
        text = f'🎉 **ВЫИГРЫШ!**\n💰 +{total_coins} монет\n⭐ +{total_exp} опыта'
        if bonus_coins > 0 or bonus_exp > 0:
            text += f'\n(бонус: +{bonus_coins} монет, +{bonus_exp} опыта)'
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')
        
        # Уведомление при крупном выигрыше
        if total_coins >= 50:
            notify_all_players(f'🎰 *Джекпот*: {format_player_name(user["game_nick"])} выиграл {total_coins} монет!')
    else:
        base_exp = 2
        bonus_exp = int(base_exp * exp_multiplier - base_exp)
        total_exp = base_exp + bonus_exp
        add_exp(user_id, total_exp)
        
        text = f'😢 **ПРОИГРЫШ**\n💰 -10 монет\n⭐ +{total_exp} опыта'
        if bonus_exp > 0:
            text += f' (бонус: +{bonus_exp} опыта)'
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')

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
    text = '🏆 **ТОП-10**\n\n'
    for i, (nick, balance) in enumerate(players, 1):
        text += f'{i}. {nick} — {balance} монет\n'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

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
🏷️ **ВСЕ СТАТУСЫ**
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
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ===== БИЗНЕСЫ =====
@bot.message_handler(func=lambda m: m.text == '🏢 Бизнесы')
def businesses_main(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    text = '🏢 **БИЗНЕСЫ**\nВыберите действие:'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown', reply_markup=business_keyboard)

@bot.message_handler(func=lambda m: m.text == '📋 Все бизнесы')
def show_all_businesses(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    all_biz = get_all_businesses()
    text = '📋 **ВСЕ БИЗНЕСЫ**\n\n'
    
    for biz in all_biz:
        status = '🟢 СВОБОДЕН' if biz['owner_id'] is None else f'🔒 {biz["owner_nick"]}'
        text += f"{biz['id']}. {biz['name']} — {biz['price']} монет ({biz['income']}/час) {status}\n"
    
    text += '\nВведите номер бизнеса для покупки (1-50):'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_buy_business)

def get_all_businesses():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM businesses ORDER BY id')
    businesses = cur.fetchall()
    cur.close()
    conn.close()
    return businesses

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
    
    # Уведомление всем
    notify_all_players(f'🏢 *Покупка бизнеса*: {format_player_name(user["game_nick"])} купил «{biz["name"]}» за {biz["price"]:,} монет!')

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
    
    coin_multiplier, _, _ = get_user_bonuses(user_id)
    
    text = '🏢 **МОИ БИЗНЕСЫ**\n\n'
    for biz in my_biz:
        last = datetime.fromisoformat(biz['last_collected']) if biz['last_collected'] else datetime.now()
        now = datetime.now()
        hours = (now - last).total_seconds() / 3600
        base_income = int(biz['income'] * hours) if hours > 0 else 0
        bonus_income = int(base_income * coin_multiplier - base_income)
        total_income = base_income + bonus_income
        
        text += f"{biz['id']}. {biz['name']} — {biz['income']}/час\n"
        text += f"   Накоплено: {total_income} монет (бонус: +{bonus_income})\n\n"
    
    text += 'Введите номер бизнеса для сбора дохода:'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
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
    
    coin_multiplier, _, _ = get_user_bonuses(user_id)
    
    last = datetime.fromisoformat(biz['last_collected']) if biz['last_collected'] else datetime.now()
    now = datetime.now()
    hours = (now - last).total_seconds() / 3600
    base_income = int(biz['income'] * hours)
    bonus_income = int(base_income * coin_multiplier - base_income)
    total_income = base_income + bonus_income
    
    if total_income < 1:
        bot.send_message(msg.chat.id, '⏳ Доход ещё не накопился.')
        return
    
    collect_business_income(biz_id)
    update_user(user_id, balance=get_user(user_id)['balance'] + total_income)
    
    text = f'💰 Собрано {total_income} монет с {biz["name"]}!'
    if bonus_income > 0:
        text += f'\n(база: {base_income}, бонус VIP: +{bonus_income})'
    bot.send_message(msg.chat.id, text)
    
    # Уведомление при крупном сборе
    if total_income >= 500:
        notify_all_players(f'💰 *Доход*: {format_player_name(get_user(user_id)["game_nick"])} собрал {total_income} монет с бизнесов!')

# ===== ПОДПИСКА =====
@bot.message_handler(func=lambda m: m.text == '👑 Подписка')
def subscription_menu(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    text = f'👑 **ПОДПИСКА**\n💰 Баланс: {user["balance"]} монет\n\n'
    text += f'{get_subscription_status_text(user_id)}\n\n'
    text += '📋 Купите VIP подписку:\n'
    text += '1. 🟢 VIP 1 — 500 монет (7 дней)\n'
    text += '2. 🔵 VIP 2 — 2 000 монет (14 дней)\n'
    text += '3. 🟣 VIP 3 — 5 000 монет (30 дней)\n'
    text += '4. 🔴 VIP 4 — 15 000 монет (60 дней)\n'
    text += '5. 👑 VIP 5 — 50 000 монет (90 дней)\n\n'
    text += 'Введите номер подписки для покупки (1-5):'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_buy_subscription)

def process_buy_subscription(msg):
    user_id = msg.from_user.id
    try:
        level = int(msg.text.strip())
        if level < 1 or level > 5:
            bot.send_message(msg.chat.id, '❌ Введите число от 1 до 5.')
            return
    except:
        bot.send_message(msg.chat.id, '❌ Введите номер подписки (1-5).')
        return
    
    prices = {1: 500, 2: 2000, 3: 5000, 4: 15000, 5: 50000}
    days = {1: 7, 2: 14, 3: 30, 4: 60, 5: 90}
    names = {1: 'VIP 1 🟢', 2: 'VIP 2 🔵', 3: 'VIP 3 🟣', 4: 'VIP 4 🔴', 5: 'VIP 5 👑'}
    
    user = get_user(user_id)
    if user['balance'] < prices[level]:
        bot.send_message(msg.chat.id, f'❌ Не хватает {prices[level] - user["balance"]} монет.')
        return
    
    # Проверяем текущую подписку
    current_level = user.get('vip_level', 0)
    if current_level >= level:
        bot.send_message(msg.chat.id, f'❌ У вас уже есть подписка {names[current_level]} (уровень {current_level}).')
        return
    
    update_user(user_id, balance=user['balance'] - prices[level])
    end_date = (datetime.now() + timedelta(days=days[level])).isoformat()
    update_user(user_id, vip_level=level, vip_end=end_date)
    
    bot.send_message(msg.chat.id, f'✅ Вы купили {names[level]} на {days[level]} дней!')
    
    # Уведомление всем
    notify_all_players(f'👑 *VIP*: {format_player_name(user["game_nick"])} повысил VIP до {level} уровня!')

# ===== ИНВЕНТАРЬ =====
@bot.message_handler(func=lambda m: m.text == '🎒 Инвентарь')
def inventory_menu(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    inventory = get_inventory(user_id)
    energy = get_energy(user_id)
    
    if not inventory:
        text = f'🎒 **ИНВЕНТАРЬ**\n\n⚡ Энергия: {energy}/50\n\n📦 У вас нет предметов. Купите в магазине!'
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')
        return
    
    text = f'🎒 **ИНВЕНТАРЬ**\n\n⚡ Энергия: {energy}/50\n\n📦 Ваши предметы:\n\n'
    for i, item in enumerate(inventory, 1):
        item_data = SHOP_ITEMS.get(item['id'], {})
        text += f"{i}. {item_data.get('name', 'Неизвестно')} x{item['count']}\n"
    
    text += '\nВведите номер предмета для использования:'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_use_item)

def process_use_item(msg):
    user_id = msg.from_user.id
    try:
        index = int(msg.text.strip()) - 1
    except:
        bot.send_message(msg.chat.id, '❌ Введите номер предмета.')
        return
    
    inventory = get_inventory(user_id)
    if index < 0 or index >= len(inventory):
        bot.send_message(msg.chat.id, '❌ Предмет не найден.')
        return
    
    item = inventory[index]
    item_data = SHOP_ITEMS.get(item['id'], {})
    
    if item_data.get('type') == 'food':
        energy = update_energy(user_id, item_data['effect'].get('energy', 0))
        remove_item(user_id, item['id'])
        bot.send_message(msg.chat.id, f'🍽️ Вы использовали {item_data["name"]}!\n⚡ Энергия: {energy}/50')
    elif item_data.get('id') == 100:  # Свиток повышения VIP
        use_vip_scroll(user_id)
        remove_item(user_id, 100)
    else:
        bot.send_message(msg.chat.id, f'❌ {item_data["name"]} нельзя использовать.')

def use_vip_scroll(user_id):
    user = get_user(user_id)
    current_vip = user.get('vip_level', 0)
    
    if current_vip >= 5:
        bot.send_message(user_id, '❌ Ваш VIP-уровень уже максимальный (5)!')
        return
    
    if current_vip == 0:
        bot.send_message(user_id, '❌ У вас нет активной VIP-подписки!')
        return
    
    vip_end = user.get('vip_end')
    if vip_end:
        try:
            end_date = datetime.fromisoformat(vip_end)
            if datetime.now() > end_date:
                bot.send_message(user_id, '❌ Ваша VIP-подписка истекла!')
                return
        except:
            pass
    
    new_vip_level = current_vip + 1
    update_user(user_id, vip_level=new_vip_level)
    coin_multiplier, exp_multiplier, shop_discount = get_user_bonuses(user_id)
    
    text = f"""✅ **VIP-УРОВЕНЬ ПОВЫШЕН!**
Ваш VIP-уровень: {current_vip} → **{new_vip_level}** 👑

🌟 **Ваши бонусы:**
💰 +{int((coin_multiplier-1)*100)}% к монетам
⭐ +{int((exp_multiplier-1)*100)}% к опыту
🛒 Скидка {int(shop_discount*100)}% в магазине"""
    
    bot.send_message(user_id, text, parse_mode='Markdown')
    
    # Уведомление всем
    notify_all_players(f'👑 *VIP*: {format_player_name(user["game_nick"])} повысил VIP до {new_vip_level} уровня!')

# ===== МАГАЗИН =====
SHOP_ITEMS = {
    1: {'id': 1, 'name': '🍎 Яблоко', 'price': 50, 'category': 'food', 'type': 'food', 'effect': {'energy': 10}},
    2: {'id': 2, 'name': '🍌 Банан', 'price': 80, 'category': 'food', 'type': 'food', 'effect': {'energy': 15}},
    3: {'id': 3, 'name': '🍕 Пицца', 'price': 150, 'category': 'food', 'type': 'food', 'effect': {'energy': 30}},
    4: {'id': 4, 'name': '🍔 Бургер', 'price': 200, 'category': 'food', 'type': 'food', 'effect': {'energy': 40}},
    5: {'id': 5, 'name': '⚡ Энергетик', 'price': 300, 'category': 'food', 'type': 'food', 'effect': {'energy': 50}},
    16: {'id': 16, 'name': '🎟️ Билет в казино', 'price': 100, 'category': 'ticket', 'type': 'ticket', 'effect': {'free_game': True}},
    19: {'id': 19, 'name': '💎 Алмаз', 'price': 200, 'category': 'gem', 'type': 'gem', 'effect': {'sell_price': 300}},
    100: {'id': 100, 'name': '📜 Свиток повышения VIP', 'price': 50000, 'category': 'scroll', 'type': 'scroll', 'effect': {'vip_upgrade': 1}, 'rarity': '🌟 Легендарный'},
}

@bot.message_handler(func=lambda m: m.text == '🛒 Магазин')
def shop_main(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🛒 **МАГАЗИН**\nВыберите категорию:', parse_mode='Markdown', reply_markup=shop_keyboard)

@bot.message_handler(func=lambda m: m.text in ['🍔 Еда', '🎟️ Билеты', '💎 Редкие', '📜 Свитки', '👑 Premium'])
def shop_category(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    category_map = {
        '🍔 Еда': 'food',
        '🎟️ Билеты': 'ticket',
        '💎 Редкие': 'gem',
        '📜 Свитки': 'scroll',
        '👑 Premium': 'premium',
    }
    
    category = category_map.get(msg.text)
    if not category:
        return
    
    user = get_user(user_id)
    _, _, shop_discount = get_user_bonuses(user_id)
    
    items = {k: v for k, v in SHOP_ITEMS.items() if v.get('category') == category}
    
    text = f'{msg.text}\n\n💰 Баланс: {user["balance"]} монет\n'
    if shop_discount > 0:
        text += f'🛒 Ваша скидка: {int(shop_discount*100)}%\n\n'
    else:
        text += '\n'
    
    for item_id, data in items.items():
        price = data['price']
        discount_amount = int(price * shop_discount)
        final_price = price - discount_amount
        text += f"{item_id}. {data['name']} — {final_price} монет"
        if discount_amount > 0:
            text += f" (было {price}, скидка {discount_amount})"
        text += "\n"
        if data.get('type') == 'food':
            text += f"   +{data['effect']['energy']} энергии\n"
        elif data.get('type') == 'ticket':
            text += "   Бесплатная игра\n"
        elif data.get('type') == 'gem':
            text += f"   Продать за {data['effect']['sell_price']} монет\n"
        elif data.get('type') == 'scroll':
            text += f"   {data.get('rarity', '')} Повышает VIP на +1 уровень\n"
        text += "\n"
    
    text += 'Введите номер товара для покупки:'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_shop_purchase, category)

def process_shop_purchase(msg, category):
    user_id = msg.from_user.id
    try:
        item_id = int(msg.text.strip())
        if item_id not in SHOP_ITEMS:
            bot.send_message(msg.chat.id, '❌ Товар не найден.')
            return
    except:
        bot.send_message(msg.chat.id, '❌ Введите номер товара.')
        return
    
    item_data = SHOP_ITEMS[item_id]
    if item_data.get('category') != category:
        bot.send_message(msg.chat.id, '❌ Товар не в этой категории.')
        return
    
    user = get_user(user_id)
    _, _, shop_discount = get_user_bonuses(user_id)
    
    price = item_data['price']
    discount_amount = int(price * shop_discount)
    final_price = price - discount_amount
    
    if user['balance'] < final_price:
        bot.send_message(msg.chat.id, f'❌ Не хватает {final_price - user["balance"]} монет.')
        return
    
    update_user(user_id, balance=user['balance'] - final_price)
    add_item(user_id, item_id)
    
    text = f'✅ Вы купили {item_data["name"]} за {final_price} монет!'
    if discount_amount > 0:
        text += f'\n🛒 Скидка составила {discount_amount} монет ({int(shop_discount*100)}%).'
    bot.send_message(msg.chat.id, text)
    
    # Уведомление при крупной покупке
    if final_price >= 5000:
        notify_all_players(f'🛒 *Покупка*: {format_player_name(user["game_nick"])} купил «{item_data["name"]}» за {final_price} монет!')

@bot.message_handler(func=lambda m: m.text == '🔙 Назад')
def back_to_main(msg):
    user_id = msg.from_user.id
    if is_logged_in(user_id):
        bot.send_message(msg.chat.id, '🏠 Главное меню', reply_markup=main_keyboard)
    else:
        bot.send_message(msg.chat.id, '🔐 Войдите', reply_markup=auth_keyboard)

# ===== ТОРГОВЛЯ =====
@bot.message_handler(func=lambda m: m.text == '🤝 Торговля')
def trade_menu(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add('💰 Обмен монетами', '🎒 Обмен предметами')
    keyboard.add('🔙 Назад')
    
    bot.send_message(msg.chat.id, '🤝 **ТОРГОВЛЯ**\nВыберите тип сделки:', parse_mode='Markdown', reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text == '💰 Обмен монетами')
def trade_coins(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '💰 **ОБМЕН МОНЕТАМИ**\n\nВведите ник и сумму:\nПример: @alex88 1000', parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_trade_coins)

def process_trade_coins(msg):
    user_id = msg.from_user.id
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: @ник сумма')
            return
        nick = parts[0].replace('@', '')
        amount = int(parts[1])
        
        if amount <= 0:
            bot.send_message(msg.chat.id, '❌ Сумма должна быть положительной.')
            return
        
        receiver = get_user_by_nick(nick)
        if not receiver:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        
        if receiver['id'] == user_id:
            bot.send_message(msg.chat.id, '❌ Нельзя отправить самому себе.')
            return
        
        user = get_user(user_id)
        if user['balance'] < amount:
            bot.send_message(msg.chat.id, f'❌ Недостаточно монет. Нужно {amount}, у вас {user["balance"]}.')
            return
        
        update_user(user_id, balance=user['balance'] - amount)
        update_user(receiver['id'], balance=receiver['balance'] + amount)
        
        bot.send_message(msg.chat.id, f'✅ {amount} монет отправлено {nick}!')
        bot.send_message(receiver['id'], f'📩 Вы получили {amount} монет от {user["game_nick"]}!')
        
        # Уведомление при крупном переводе
        if amount >= 5000:
            notify_all_players(f'💰 *Перевод*: {format_player_name(user["game_nick"])} отправил {amount} монет {format_player_name(nick)}!')
        
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Используйте формат: @ник сумма')

@bot.message_handler(func=lambda m: m.text == '🎒 Обмен предметами')
def trade_items(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    inventory = get_inventory(user_id)
    if not inventory:
        bot.send_message(msg.chat.id, '❌ У вас нет предметов для обмена.')
        return
    
    text = '🎒 **ОБМЕН ПРЕДМЕТАМИ**\n\nВаш инвентарь:\n'
    for i, item in enumerate(inventory, 1):
        item_data = SHOP_ITEMS.get(item['id'], {})
        text += f"{i}. {item_data.get('name', 'Неизвестно')} x{item['count']}\n"
    
    text += '\nВведите: номер предмета @ник\nПример: 1 @alex88'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_trade_items)

def process_trade_items(msg):
    user_id = msg.from_user.id
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: номер @ник')
            return
        item_index = int(parts[0]) - 1
        nick = parts[1].replace('@', '')
        
        receiver = get_user_by_nick(nick)
        if not receiver:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        
        if receiver['id'] == user_id:
            bot.send_message(msg.chat.id, '❌ Нельзя отправить самому себе.')
            return
        
        inventory = get_inventory(user_id)
        if item_index < 0 or item_index >= len(inventory):
            bot.send_message(msg.chat.id, '❌ Предмет не найден.')
            return
        
        item = inventory[item_index]
        item_data = SHOP_ITEMS.get(item['id'], {})
        
        remove_item(user_id, item['id'])
        add_item(receiver['id'], item['id'])
        
        bot.send_message(msg.chat.id, f'✅ Предмет "{item_data["name"]}" передан {nick}!')
        bot.send_message(receiver['id'], f'📦 Вы получили предмет "{item_data["name"]}" от {get_user(user_id)["game_nick"]}!')
        
        # Уведомление при передаче редкого предмета
        if item_data.get('rarity') in ['🌟 Легендарный', '👑 Мифический']:
            notify_all_players(f'🤝 *Трейд*: {format_player_name(get_user(user_id)["game_nick"])} передал «{item_data["name"]}» {format_player_name(nick)}!')
        
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Используйте формат: номер @ник')

# ===== BATTLE PASS =====
BP_MAX_LEVEL = 50
BP_EXP_PER_LEVEL = 50
BP_SEASON = 1
BP_END_DATE = "2026-09-15"

BP_REWARDS = {
    1: {'free': {'coins': 10}, 'premium': {'ticket': 1}},
    5: {'free': {'coins': 30}, 'premium': {'energy': 50}},
    10: {'free': {'coins': 100}, 'premium': {'vip_scroll': 1}},
    15: {'free': {'coins': 200}, 'premium': {'vip_3days': 1}},
    20: {'free': {'coins': 300}, 'premium': {'vip_scroll': 2}},
    25: {'free': {'coins': 500}, 'premium': {'vip_7days': 1}},
    30: {'free': {'coins': 700}, 'premium': {'vip_scroll': 3}},
    35: {'free': {'coins': 1000}, 'premium': {'vip_14days': 1}},
    40: {'free': {'coins': 1500}, 'premium': {'vip_scroll': 4}},
    45: {'free': {'coins': 2000}, 'premium': {'vip_30days': 1}},
    50: {'free': {'coins': 5000}, 'premium': {'legendary_skin': 1}},
}

def add_bp_exp(user_id, amount):
    user = get_user(user_id)
    if not user:
        return
    
    if user.get('bp_season', 0) != BP_SEASON:
        update_user(user_id, bp_level=0, bp_exp=0, bp_season=BP_SEASON)
        user = get_user(user_id)
    
    bp_exp = user.get('bp_exp', 0) + amount
    bp_level = user.get('bp_level', 0)
    
    if bp_level >= BP_MAX_LEVEL:
        return
    
    while bp_exp >= BP_EXP_PER_LEVEL and bp_level < BP_MAX_LEVEL:
        bp_exp -= BP_EXP_PER_LEVEL
        bp_level += 1
        notify_bp_level_up(user_id, bp_level)
    
    update_user(user_id, bp_level=bp_level, bp_exp=bp_exp)

def notify_bp_level_up(user_id, level):
    user = get_user(user_id)
    if not user:
        return
    
    if level % 5 == 0 or level == 50:
        notify_all_players(f'🎖️ *Battle Pass*: {format_player_name(user["game_nick"])} достиг {level} уровня!')
    
    rewards = BP_REWARDS.get(level, {})
    text = f'🎖️ **BATTLE PASS УРОВЕНЬ {level}!**\n\n'
    text += '🎁 Награды:\n'
    
    if rewards.get('free'):
        if 'coins' in rewards['free']:
            text += f'💰 +{rewards["free"]["coins"]} монет\n'
    if rewards.get('premium'):
        text += f'👑 Премиум награда доступна\n'
    
    bot.send_message(user_id, text, parse_mode='Markdown')

def collect_bp_reward(user_id, level):
    user = get_user(user_id)
    collected = json.loads(user.get('bp_rewards_collected', '[]'))
    
    if level in collected:
        return False, "❌ Награда уже получена!"
    
    rewards = BP_REWARDS.get(level, {})
    
    if rewards.get('free'):
        if 'coins' in rewards['free']:
            amount = rewards['free']['coins']
            update_user(user_id, balance=user['balance'] + amount)
    
    if rewards.get('premium') and user.get('bp_premium', 0) == 1:
        apply_premium_bp_reward(user_id, rewards['premium'])
    
    collected.append(level)
    update_user(user_id, bp_rewards_collected=json.dumps(collected))
    
    return True, "✅ Награда получена!"

def apply_premium_bp_reward(user_id, reward):
    if 'vip_scroll' in reward:
        for _ in range(reward['vip_scroll']):
            add_item(user_id, 100)
    elif 'vip_3days' in reward:
        activate_vip(user_id, 3)
    elif 'vip_7days' in reward:
        activate_vip(user_id, 7)
    elif 'vip_14days' in reward:
        activate_vip(user_id, 14)
    elif 'vip_30days' in reward:
        activate_vip(user_id, 30)
    elif 'ticket' in reward:
        add_item(user_id, 16, reward['ticket'])
    elif 'energy' in reward:
        update_energy(user_id, reward['energy'])
    elif 'legendary_skin' in reward:
        # Легендарный скин (пока просто уведомление)
        notify_all_players(f'🌟 {format_player_name(get_user(user_id)["game_nick"])} получил Легендарный скин в Battle Pass!')

def activate_vip(user_id, days):
    user = get_user(user_id)
    current_end = user.get('vip_end')
    if current_end:
        try:
            end_date = datetime.fromisoformat(current_end)
            if datetime.now() < end_date:
                end_date = end_date + timedelta(days=days)
            else:
                end_date = datetime.now() + timedelta(days=days)
        except:
            end_date = datetime.now() + timedelta(days=days)
    else:
        end_date = datetime.now() + timedelta(days=days)
    
    update_user(user_id, vip_end=end_date.isoformat())

@bot.message_handler(func=lambda m: m.text == '🎖️ Battle Pass')
def battle_pass_menu(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    bp_level = user.get('bp_level', 0)
    bp_exp = user.get('bp_exp', 0)
    
    next_level_exp = BP_EXP_PER_LEVEL
    progress = bp_exp % next_level_exp
    percent = int(progress / next_level_exp * 100) if next_level_exp > 0 else 0
    bar = '█' * (percent // 10) + '░' * (10 - (percent // 10))
    
    text = f'''🎖️ **BATTLE PASS — СЕЗОН {BP_SEASON}**

📊 Ваш уровень: {bp_level} / {BP_MAX_LEVEL}
⭐ Прогресс: [{bar}] {percent}%
⏳ До следующего уровня: {next_level_exp - progress} опыта BP
📅 Сезон заканчивается: {BP_END_DATE}

[ 📋 Все награды ]  [ 🛒 Купить Premium ]
'''
    
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton('📋 Все награды', callback_data='bp_rewards'),
        telebot.types.InlineKeyboardButton('🛒 Купить Premium', callback_data='bp_buy_premium')
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton('🎁 Забрать награду', callback_data='bp_collect')
    )
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'bp_rewards')
def bp_show_rewards(call):
    text = '🎖️ **ВСЕ НАГРАДЫ BATTLE PASS**\n\n'
    for level in range(1, BP_MAX_LEVEL + 1):
        rewards = BP_REWARDS.get(level, {})
        free_reward = rewards.get('free', {})
        premium_reward = rewards.get('premium', {})
        text += f"Уровень {level}: {free_reward} | {premium_reward}\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'bp_buy_premium')
def bp_buy_premium(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if user.get('bp_premium', 0) == 1:
        bot.answer_callback_query(call.id, '❌ У вас уже есть Premium Battle Pass!')
        return
    
    price = 5000
    if user['balance'] < price:
        bot.answer_callback_query(call.id, f'❌ Не хватает {price - user["balance"]} монет.')
        return
    
    update_user(user_id, balance=user['balance'] - price, bp_premium=1)
    bot.answer_callback_query(call.id, '✅ Premium Battle Pass активирован!')
    bot.send_message(call.message.chat.id, '👑 Теперь вы можете получать премиум-награды!')

@bot.callback_query_handler(func=lambda call: call.data == 'bp_collect')
def bp_collect_reward(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    bp_level = user.get('bp_level', 0)
    
    if bp_level == 0:
        bot.answer_callback_query(call.id, '❌ У вас ещё нет уровней.')
        return
    
    success, msg = collect_bp_reward(user_id, bp_level)
    bot.answer_callback_query(call.id, msg)

# ===== АДМИН-ПАНЕЛЬ =====
@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    user_id = msg.from_user.id
    if not is_admin(user_id):
        bot.send_message(msg.chat.id, '❌ Доступ запрещён.')
        return
    bot.send_message(msg.chat.id, '🔐 **АДМИН-ПАНЕЛЬ**', parse_mode='Markdown', reply_markup=admin_keyboard)

@bot.message_handler(func=lambda m: m.text == '⬅️ Назад' and is_admin(m.from_user.id))
def back_to_main_admin(msg):
    bot.send_message(msg.chat.id, '🏠 Главное меню', reply_markup=main_keyboard)

@bot.message_handler(func=lambda m: m.text == '📊 Статистика' and is_admin(m.from_user.id))
def stats(msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    total_users = cur.fetchone()[0]
    cur.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
    total_balance = cur.fetchone()[0]
    cur.execute('SELECT COALESCE(MAX(balance), 0) FROM users')
    max_balance = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM businesses WHERE owner_id IS NOT NULL')
    total_businesses = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    text = f'''
📊 **СТАТИСТИКА**
👥 Игроков: {total_users}
💰 Общий баланс: {total_balance:,}
🏆 Макс. баланс: {max_balance:,}
🏢 Бизнесов куплено: {total_businesses}/50
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👥 Список игроков' and is_admin(m.from_user.id))
def players_list(msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT game_nick, balance FROM users ORDER BY balance DESC LIMIT 10')
    players = cur.fetchall()
    cur.close()
    conn.close()
    text = '👥 **ТОП-10 ИГРОКОВ**\n\n'
    for i, (nick, balance) in enumerate(players, 1):
        text += f'{i}. {nick} — {balance} монет\n'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👑 Список админов' and is_admin(m.from_user.id))
def list_admins(msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT game_nick, admin_level, balance FROM users WHERE admin_level > 0 ORDER BY admin_level DESC')
    admins = cur.fetchall()
    cur.close()
    conn.close()
    
    if not admins:
        bot.send_message(msg.chat.id, '📭 Нет администраторов.')
        return
    
    text = '👑 **СПИСОК АДМИНИСТРАТОРОВ**\n\n'
    for nick, level, balance in admins:
        text += f'Уровень {level}: {nick} — {balance} монет\n'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👑 Назначить админа' and is_admin(m.from_user.id))
def promote_admin_start(msg):
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
        bot.send_message(msg.chat.id, f'✅ {nick} теперь админ уровня {level}!')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник уровень')

@bot.message_handler(func=lambda m: m.text == '📈 Изменить уровень' and is_admin(m.from_user.id))
def change_level_start(msg):
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

@bot.message_handler(func=lambda m: m.text == '🎁 Выдать опыт' and is_admin(m.from_user.id))
def give_exp_start(msg):
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
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Формат: ник опыт')

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
📋 **ИНФОРМАЦИЯ**
👤 Ник: {user['game_nick']}
🆔 ID: {user['id']}
💰 Баланс: {user['balance']} монет
📈 Уровень: {user['level']}
⭐ Опыт: {user['exp']}
👑 VIP: {user.get('vip_level', 0)}
🚫 Бан: {"Да" if user['is_banned'] else "Нет"}
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '⏳ Бан/Разбан' and is_admin(m.from_user.id))
def ban_player_start(msg):
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

@bot.message_handler(func=lambda m: m.text == '🔄 Сброс баланса' and is_admin(m.from_user.id))
def reset_balance_all(msg):
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
    else:
        bot.send_message(msg.chat.id, '❌ Отменено.')

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

@bot.message_handler(func=lambda m: m.text == '🗑️ Удалить аккаунт' and is_admin(m.from_user.id))
def delete_account_start(msg):
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

@bot.message_handler(func=lambda m: m.text == '📋 Логи админа' and is_admin(m.from_user.id))
def show_logs(msg):
    try:
        with open('admin_logs.txt', 'r') as f:
            logs = f.read().splitlines()
            last_logs = logs[-20:] if len(logs) > 20 else logs
            text = '📋 **Последние 20 действий:**\n\n' + '\n'.join(last_logs)
            bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    except:
        bot.send_message(msg.chat.id, '📭 Логов пока нет.')

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

def get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users')
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

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
