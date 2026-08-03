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

def get_all_businesses():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM businesses ORDER BY id')
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
    
    tier = user.get('pp_tier', 'free')
    tier_data = PP_TIERS.get(tier, {})
    coin_multiplier += tier_data.get('coin_bonus', 0)
    exp_multiplier += tier_data.get('exp_bonus', 0)
    shop_discount += tier_data.get('shop_discount', 0)
    
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

def format_player_name(nick):
    return f'@{nick}'

def notify_all_players(text, parse_mode='Markdown'):
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

def log_creator_action(action):
    with open('creator_logs.txt', 'a') as f:
        f.write(f'{datetime.now().strftime("%d.%m.%Y %H:%M")} | {action}\n')

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

business_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
business_keyboard.add('🏢 Мои бизнесы', '📋 Все бизнесы')
business_keyboard.add('🔙 Назад')

shop_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
shop_keyboard.add('🍔 Еда', '🎟️ Билеты', '💎 Редкие')
shop_keyboard.add('📜 Свитки', '👑 Premium', '🔙 Назад')

clan_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
clan_keyboard.add('📋 Список кланов', '🏰 Создать клан')
clan_keyboard.add('🔍 Найти клан', '📊 Топ кланов')
clan_keyboard.add('🔙 Назад')

clan_member_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
clan_member_keyboard.add('💬 Чат клана', '📤 Пригласить')
clan_member_keyboard.add('📊 Топ кланов', '🚪 Выйти из клана')
clan_member_keyboard.add('🔙 Назад')

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
admin_keyboard.add('📢 Смешная рассылка', '👑 Панель создателя')
admin_keyboard.add('⬅️ Назад')

creator_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
creator_keyboard.add('📦 Выдать предмет', '👑 Выдать VIP')
creator_keyboard.add('⭐ Выдать опыт', '💰 Изменить баланс')
creator_keyboard.add('👤 Удалить аккаунт', '🗑️ Удалить клан')
creator_keyboard.add('🏰 Управление кланами', '🎖️ Управление Премиум Пассом')
creator_keyboard.add('📊 Статистика сервера', '👥 Список игроков')
creator_keyboard.add('📢 Глобальная рассылка', '📝 Логи создателя')
creator_keyboard.add('💾 Экспорт БД', '🔄 Резервное копирование')
creator_keyboard.add('📤 Восстановить БД', '⬅️ Назад')

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

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

def format_reward_text(reward_dict):
    if not reward_dict:
        return '❌ Нет награды'
    
    parts = []
    for key, value in reward_dict.items():
        if key == 'coins':
            parts.append(f'💰 {value} монет')
        elif key == 'exp':
            parts.append(f'⭐ {value} опыта')
        elif key == 'ticket':
            parts.append(f'🎟️ Билет x{value}')
        elif key == 'energy':
            parts.append(f'⚡ Энергия +{value}')
        elif key == 'energy_full':
            parts.append(f'⚡ Полное восстановление энергии')
        elif key == 'pizza':
            parts.append(f'🍕 Пицца x{value}')
        elif key == 'gem':
            parts.append(f'💎 Алмаз x{value}')
        elif key == 'sword':
            parts.append(f'⚔️ Меч x{value}')
        elif key == 'vip_scroll':
            parts.append(f'📜 Свиток VIP x{value}')
        elif key == 'vip_7days':
            parts.append(f'👑 VIP на 7 дней')
        elif key == 'vip_14days':
            parts.append(f'👑 VIP на 14 дней')
        elif key == 'vip_30days':
            parts.append(f'👑 VIP на 30 дней')
        elif key == 'star_skin':
            parts.append(f'⭐ Скин «Звёздный»')
        elif key == 'legendary_skin':
            parts.append(f'🌟 Скин «Легендарный»')
        elif key == 'mythic_skin':
            parts.append(f'👑 Скин «Мифический»')
        else:
            parts.append(f'{key}: {value}')
    
    return ', '.join(parts) if parts else '❌ Нет награды'

# ============================================================
# ПРЕМИУМ ПАСС (3 УРОВНЯ)
# ============================================================

PP_MAX_LEVEL = 40
PP_EXP_PER_LEVEL = 30
PP_SEASON = 1
PP_END_DATE = "2026-10-15"

PP_TIERS = {
    'free': {'name': '🆓 Free', 'price': 0, 'coin_bonus': 0, 'exp_bonus': 0, 'shop_discount': 0, 'max_level': 20},
    'premium': {'name': '⭐ Premium', 'price': 5000, 'coin_bonus': 0.10, 'exp_bonus': 0.10, 'shop_discount': 0.10, 'max_level': 30},
    'premium_plus': {'name': '👑 Premium+', 'price': 15000, 'coin_bonus': 0.25, 'exp_bonus': 0.25, 'shop_discount': 0.20, 'max_level': 40}
}

PP_REWARDS = {
    1: {'free': {'coins': 10, 'exp': 5}, 'premium': {'ticket': 1}, 'premium_plus': {'ticket': 2}},
    2: {'free': {'coins': 15, 'exp': 8}, 'premium': {'energy': 20}, 'premium_plus': {'energy': 40}},
    3: {'free': {'coins': 20, 'exp': 10}, 'premium': {'pizza': 1}, 'premium_plus': {'pizza': 2}},
    4: {'free': {'coins': 25, 'exp': 12}, 'premium': {'energy': 30}, 'premium_plus': {'energy': 50}},
    5: {'free': {'coins': 30, 'exp': 15}, 'premium': {'gem': 1}, 'premium_plus': {'gem': 2}},
    6: {'free': {'coins': 40, 'exp': 18}, 'premium': {'ticket': 2}, 'premium_plus': {'ticket': 3}},
    7: {'free': {'coins': 50, 'exp': 20}, 'premium': {'sword': 1}, 'premium_plus': {'sword': 2}},
    8: {'free': {'coins': 60, 'exp': 25}, 'premium': {'energy_full': 1}, 'premium_plus': {'energy_full': 2}},
    9: {'free': {'coins': 70, 'exp': 30}, 'premium': {'pizza': 2}, 'premium_plus': {'pizza': 3}},
    10: {'free': {'coins': 100, 'exp': 40}, 'premium': {'vip_scroll': 1}, 'premium_plus': {'vip_scroll': 2}},
    11: {'free': {'coins': 120, 'exp': 45}, 'premium': {'ticket': 3}, 'premium_plus': {'ticket': 4}},
    12: {'free': {'coins': 150, 'exp': 50}, 'premium': {'vip_scroll': 1}, 'premium_plus': {'vip_scroll': 2}},
    13: {'free': {'coins': 180, 'exp': 55}, 'premium': {'vip_scroll': 2}, 'premium_plus': {'vip_scroll': 3}},
    14: {'free': {'coins': 200, 'exp': 60}, 'premium': {'vip_scroll': 2}, 'premium_plus': {'vip_scroll': 3}},
    15: {'free': {'coins': 300, 'exp': 70}, 'premium': {'vip_7days': 1}, 'premium_plus': {'vip_7days': 2}},
    16: {'free': {'coins': 350, 'exp': 80}, 'premium': {'vip_scroll': 3}, 'premium_plus': {'vip_scroll': 4}},
    17: {'free': {'coins': 400, 'exp': 90}, 'premium': {'vip_scroll': 3}, 'premium_plus': {'vip_scroll': 5}},
    18: {'free': {'coins': 450, 'exp': 100}, 'premium': {'vip_scroll': 4}, 'premium_plus': {'vip_scroll': 6}},
    19: {'free': {'coins': 500, 'exp': 110}, 'premium': {'vip_scroll': 4}, 'premium_plus': {'vip_scroll': 7}},
    20: {'free': {'coins': 500, 'exp': 120}, 'premium': {'star_skin': 1}, 'premium_plus': {'star_skin': 1, 'vip_scroll': 5}},
    21: {'free': {'coins': 600, 'exp': 130}, 'premium': {'vip_14days': 1}, 'premium_plus': {'vip_14days': 2}},
    22: {'free': {'coins': 700, 'exp': 140}, 'premium': {'vip_scroll': 5}, 'premium_plus': {'vip_scroll': 7}},
    23: {'free': {'coins': 800, 'exp': 150}, 'premium': {'vip_scroll': 5}, 'premium_plus': {'vip_scroll': 8}},
    24: {'free': {'coins': 900, 'exp': 160}, 'premium': {'vip_scroll': 6}, 'premium_plus': {'vip_scroll': 9}},
    25: {'free': {'coins': 1000, 'exp': 180}, 'premium': {'legendary_skin': 1}, 'premium_plus': {'legendary_skin': 1, 'vip_scroll': 5}},
    26: {'free': {'coins': 1200, 'exp': 200}, 'premium': {'vip_30days': 1}, 'premium_plus': {'vip_30days': 2}},
    27: {'free': {'coins': 1500, 'exp': 220}, 'premium': {'vip_scroll': 7}, 'premium_plus': {'vip_scroll': 10}},
    28: {'free': {'coins': 2000, 'exp': 250}, 'premium': {'vip_scroll': 8}, 'premium_plus': {'vip_scroll': 12}},
    29: {'free': {'coins': 3000, 'exp': 300}, 'premium': {'vip_scroll': 10}, 'premium_plus': {'vip_scroll': 15}},
    30: {'free': {'coins': 3000, 'exp': 300}, 'premium': {'vip_30days': 1, 'mythic_skin': 1}, 'premium_plus': {'vip_30days': 2, 'mythic_skin': 1}},
    31: {'free': {'coins': 3500, 'exp': 320}, 'premium': {'vip_scroll': 5}, 'premium_plus': {'vip_30days': 1, 'vip_scroll': 5}},
    32: {'free': {'coins': 4000, 'exp': 340}, 'premium': {'vip_scroll': 6}, 'premium_plus': {'vip_30days': 1, 'vip_scroll': 7}},
    33: {'free': {'coins': 4500, 'exp': 360}, 'premium': {'vip_scroll': 7}, 'premium_plus': {'vip_30days': 1, 'vip_scroll': 9}},
    34: {'free': {'coins': 5000, 'exp': 380}, 'premium': {'vip_scroll': 8}, 'premium_plus': {'vip_30days': 1, 'vip_scroll': 11}},
    35: {'free': {'coins': 6000, 'exp': 400}, 'premium': {'vip_30days': 1, 'vip_scroll': 5}, 'premium_plus': {'vip_30days': 2, 'vip_scroll': 10}},
    36: {'free': {'coins': 7000, 'exp': 420}, 'premium': {'vip_scroll': 10}, 'premium_plus': {'vip_30days': 2, 'vip_scroll': 12}},
    37: {'free': {'coins': 8000, 'exp': 440}, 'premium': {'vip_scroll': 12}, 'premium_plus': {'vip_30days': 2, 'vip_scroll': 15}},
    38: {'free': {'coins': 9000, 'exp': 460}, 'premium': {'vip_scroll': 15}, 'premium_plus': {'vip_30days': 2, 'vip_scroll': 18}},
    39: {'free': {'coins': 10000, 'exp': 480}, 'premium': {'vip_scroll': 18}, 'premium_plus': {'vip_30days': 2, 'vip_scroll': 20}},
    40: {'free': {'coins': 15000, 'exp': 500}, 'premium': {'vip_30days': 2, 'mythic_skin': 1}, 'premium_plus': {'vip_30days': 3, 'mythic_skin': 1}},
}

def get_pp_tier(user_id):
    user = get_user(user_id)
    if not user:
        return 'free'
    return user.get('pp_tier', 'free')

def get_pp_max_level(user_id):
    tier = get_pp_tier(user_id)
    return PP_TIERS.get(tier, {}).get('max_level', 20)

def get_pp_rewards(level):
    return PP_REWARDS.get(level, {'free': {'coins': 10, 'exp': 5}, 'premium': {}, 'premium_plus': {}})

def add_pp_exp(user_id, amount):
    user = get_user(user_id)
    if not user:
        return
    
    if user.get('pp_season', 0) != PP_SEASON:
        update_user(user_id, pp_level=0, pp_exp=0, pp_season=PP_SEASON)
        user = get_user(user_id)
    
    max_level = get_pp_max_level(user_id)
    pp_exp = user.get('pp_exp', 0) + amount
    pp_level = user.get('pp_level', 0)
    
    if pp_level >= max_level:
        return
    
    while pp_exp >= PP_EXP_PER_LEVEL and pp_level < max_level:
        pp_exp -= PP_EXP_PER_LEVEL
        pp_level += 1
        notify_pp_level_up(user_id, pp_level)
    
    update_user(user_id, pp_level=pp_level, pp_exp=pp_exp)

def notify_pp_level_up(user_id, level):
    user = get_user(user_id)
    if not user:
        return
    
    if level % 5 == 0 or level == 40:
        notify_all_players(f'🎖️ *Премиум Пасс*: {format_player_name(user["game_nick"])} достиг {level} уровня!')
    
    rewards = PP_REWARDS.get(level, {})
    text = f'🎖️ **ПРЕМИУМ ПАСС УРОВЕНЬ {level}!**\n\n'
    text += '🎁 Награды:\n'
    
    if rewards.get('free'):
        text += f'🆓 +{rewards["free"].get("coins", 0)} монет, +{rewards["free"].get("exp", 0)} опыта\n'
    if rewards.get('premium'):
        text += f'⭐ Премиум: +{format_reward_text(rewards["premium"])}\n'
    if rewards.get('premium_plus'):
        text += f'👑 Premium+: +{format_reward_text(rewards["premium_plus"])}\n'
    
    bot.send_message(user_id, text, parse_mode='Markdown')

def collect_pp_reward(user_id, level):
    user = get_user(user_id)
    collected = json.loads(user.get('pp_rewards_collected', '[]'))
    
    if level in collected:
        return False, "❌ Награда уже получена!"
    
    rewards = PP_REWARDS.get(level, {})
    tier = get_pp_tier(user_id)
    
    if rewards.get('free'):
        if 'coins' in rewards['free']:
            update_user(user_id, balance=user['balance'] + rewards['free']['coins'])
        if 'exp' in rewards['free']:
            add_exp(user_id, rewards['free']['exp'])
    
    if tier in ['premium', 'premium_plus'] and rewards.get('premium'):
        apply_pp_premium_reward(user_id, rewards['premium'])
    
    if tier == 'premium_plus' and rewards.get('premium_plus'):
        apply_pp_premium_reward(user_id, rewards['premium_plus'])
    
    collected.append(level)
    update_user(user_id, pp_rewards_collected=json.dumps(collected))
    
    return True, "✅ Награда получена!"

def apply_pp_premium_reward(user_id, reward):
    if isinstance(reward, dict):
        for key, value in reward.items():
            if key == 'vip_scroll':
                for _ in range(value):
                    add_item(user_id, 100)
            elif key == 'vip_7days':
                activate_vip(user_id, 7)
            elif key == 'vip_14days':
                activate_vip(user_id, 14)
            elif key == 'vip_30days':
                activate_vip(user_id, 30)
            elif key == 'ticket':
                add_item(user_id, 16, value)
            elif key == 'energy':
                update_energy(user_id, value)
            elif key == 'star_skin':
                update_user(user_id, pp_skin='⭐ Звёздный')
                notify_all_players(f'⭐ {format_player_name(get_user(user_id)["game_nick"])} получил скин «Звёздный»!')
            elif key == 'legendary_skin':
                update_user(user_id, pp_skin='🌟 Легендарный')
                notify_all_players(f'🌟 {format_player_name(get_user(user_id)["game_nick"])} получил скин «Легендарный»!')
            elif key == 'mythic_skin':
                update_user(user_id, pp_skin='👑 Мифический')
                notify_all_players(f'👑 {format_player_name(get_user(user_id)["game_nick"])} получил скин «Мифический»!')

# ============================================================
# БЭКАП И ВОССТАНОВЛЕНИЕ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '💾 Экспорт БД' and is_admin(m.from_user.id))
def export_database(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '⏳ Создаю дамп базы данных...')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT id, game_nick, balance, level, exp, reg_date, 
                   is_logged_in, is_banned, role, admin_level, 
                   vip_level, vip_end, pp_level, pp_tier
            FROM users
        ''')
        users = cur.fetchall()
        
        filename = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('ID;Ник;Баланс;Уровень;Опыт;Регистрация;Логин;Бан;Роль;Admin_Level;VIP;VIP_End;PP_Level;PP_Tier\n')
            for user in users:
                f.write(f"{user[0]};{user[1]};{user[2]};{user[3]};{user[4]};{user[5]};{user[6]};{user[7]};{user[8]};{user[9]};{user[10]};{user[11]};{user[12]};{user[13]}\n")
        
        cur.close()
        conn.close()
        
        with open(filename, 'rb') as f:
            bot.send_document(msg.chat.id, f, caption='📊 Дамп базы данных (CSV)')
        
        os.remove(filename)
        log_creator_action(f'Экспорт БД: {filename}')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка экспорта: {e}')

@bot.message_handler(func=lambda m: m.text == '🔄 Резервное копирование' and is_admin(m.from_user.id))
def backup_database(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '⏳ Создаю резервную копию...')
    
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'version': '1.0',
            'users': [],
            'businesses': [],
            'clans': []
        }
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute('SELECT * FROM users')
        users = cur.fetchall()
        for user in users:
            data['users'].append(dict(user))
        
        cur.execute('SELECT * FROM businesses')
        businesses = cur.fetchall()
        for biz in businesses:
            data['businesses'].append(dict(biz))
        
        cur.execute('SELECT * FROM clans')
        clans = cur.fetchall()
        for clan in clans:
            data['clans'].append(dict(clan))
        
        cur.close()
        conn.close()
        
        filename = f'backup_full_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        with open(filename, 'rb') as f:
            bot.send_document(msg.chat.id, f, caption='🔄 Полная резервная копия (JSON)')
        
        os.remove(filename)
        log_creator_action(f'Резервное копирование: {filename}')
        
        text = f"""✅ **Резервная копия создана!**

📊 **Статистика:**
👥 Пользователей: {len(data['users'])}
🏢 Бизнесов: {len(data['businesses'])}
🏰 Кланов: {len(data['clans'])}

📅 Создано: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка резервного копирования: {e}')

@bot.message_handler(func=lambda m: m.text == '📤 Восстановить БД' and is_admin(m.from_user.id))
def restore_database_start(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '⚠️ **ВНИМАНИЕ!**\n\nЭто действие перезапишет все данные в базе.\n\nОтправьте JSON-файл с резервной копией:')
    bot.register_next_step_handler(msg, process_restore_database)

def process_restore_database(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    if not msg.document:
        bot.send_message(msg.chat.id, '❌ Отправьте JSON-файл.')
        return
    
    if msg.document.file_name and not msg.document.file_name.endswith('.json'):
        bot.send_message(msg.chat.id, '❌ Файл должен быть в формате .json')
        return
    
    try:
        file_info = bot.get_file(msg.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        data = json.loads(downloaded_file)
        
        if 'version' not in data:
            bot.send_message(msg.chat.id, '❌ Неверный формат файла.')
            return
        
        bot.send_message(msg.chat.id, '⏳ Восстанавливаю данные...')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('DELETE FROM users')
        cur.execute('DELETE FROM businesses')
        cur.execute('DELETE FROM clans')
        cur.execute('DELETE FROM clan_members')
        
        for user in data['users']:
            cur.execute('''
                INSERT INTO users (id, game_nick, password, balance, level, exp, 
                                  reg_date, is_logged_in, is_banned, role, 
                                  admin_level, vip_level, vip_end, pp_level, 
                                  pp_exp, pp_tier)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (user['id'], user['game_nick'], user['password'], user['balance'],
                  user['level'], user['exp'], user['reg_date'], user['is_logged_in'],
                  user['is_banned'], user['role'], user['admin_level'], user['vip_level'],
                  user['vip_end'], user['pp_level'], user['pp_exp'], user['pp_tier']))
        
        for biz in data['businesses']:
            cur.execute('''
                INSERT INTO businesses (id, name, category, price, income, cooldown,
                                       owner_id, owner_nick, last_collected)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (biz['id'], biz['name'], biz['category'], biz['price'], biz['income'],
                  biz['cooldown'], biz['owner_id'], biz['owner_nick'], biz['last_collected']))
        
        for clan in data['clans']:
            cur.execute('''
                INSERT INTO clans (id, name, leader_id, level, bank, created_at,
                                  member_count, rating)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (clan['id'], clan['name'], clan['leader_id'], clan['level'],
                  clan['bank'], clan['created_at'], clan['member_count'], clan['rating']))
        
        conn.commit()
        cur.close()
        conn.close()
        
        bot.send_message(msg.chat.id, f'✅ База данных восстановлена!\n📅 Дата: {data["timestamp"]}')
        log_creator_action(f'Восстановление БД из {msg.document.file_name}')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка восстановления: {e}')

# ============================================================
# АВТОРИЗАЦИЯ
# ============================================================

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
    notify_all_players(f'🎉 *Новый игрок*: {format_player_name(nick)} присоединился к боту!')

@bot.message_handler(func=lambda m: m.text == '🚪 Выйти')
def logout(msg):
    update_user(msg.from_user.id, is_logged_in=0)
    bot.send_message(msg.chat.id, '👋 Выход.', reply_markup=auth_keyboard)

# ============================================================
# ПРОФИЛЬ, БАЛАНС, ИГРА, ТОП, СТАТУСЫ
# ============================================================

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
    clan = get_user_clan(user_id)
    
    text = f"""
👤 **ПРОФИЛЬ**
📛 Ник: {user['game_nick']}
💰 Баланс: {user['balance']} монет
📈 Уровень: {user['level']}
⭐ Опыт: {user['exp']}/{needed}
📊 Прогресс: [{bar}]
🏷️ Статус: {status}
{sub_status}
"""
    if clan:
        text += f"🏰 Клан: {clan['name']} ({user.get('clan_role', 'участник')})"
    if user.get('pp_skin'):
        text += f"\n🎨 Скин: {user['pp_skin']}"
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💰 Баланс')
def balance(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    user = get_user(user_id)
    bot.send_message(msg.chat.id, f'💰 Баланс: {user["balance"]} монет')

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
        add_pp_exp(user_id, 5)
        
        text = f'🎉 **ВЫИГРЫШ!**\n💰 +{total_coins} монет\n⭐ +{total_exp} опыта'
        if bonus_coins > 0 or bonus_exp > 0:
            text += f'\n(бонус: +{bonus_coins} монет, +{bonus_exp} опыта)'
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')
        
        if total_coins >= 50:
            notify_all_players(f'🎰 *Джекпот*: {format_player_name(user["game_nick"])} выиграл {total_coins} монет!')
    else:
        base_exp = 2
        bonus_exp = int(base_exp * exp_multiplier - base_exp)
        total_exp = base_exp + bonus_exp
        add_exp(user_id, total_exp)
        add_pp_exp(user_id, 2)
        
        text = f'😢 **ПРОИГРЫШ**\n💰 -10 монет\n⭐ +{total_exp} опыта'
        if bonus_exp > 0:
            text += f' (бонус: +{bonus_exp} опыта)'
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')

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
    text = f"""
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
"""
    if next_data:
        threshold, name = next_data
        text += f'До {name}: {threshold - balance} монет'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ============================================================
# БИЗНЕСЫ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🏢 Бизнесы')
def businesses_main(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    bot.send_message(msg.chat.id, '🏢 **БИЗНЕСЫ**\nВыберите действие:', parse_mode='Markdown', reply_markup=business_keyboard)

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
    add_pp_exp(user_id, 3)
    
    text = f'💰 Собрано {total_income} монет с {biz["name"]}!'
    if bonus_income > 0:
        text += f'\n(база: {base_income}, бонус VIP: +{bonus_income})'
    bot.send_message(msg.chat.id, text)
    
    if total_income >= 500:
        notify_all_players(f'💰 *Доход*: {format_player_name(get_user(user_id)["game_nick"])} собрал {total_income} монет с бизнесов!')

# ============================================================
# ПОДПИСКА
# ============================================================

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
    
    current_level = user.get('vip_level', 0)
    if current_level >= level:
        bot.send_message(msg.chat.id, f'❌ У вас уже есть подписка {names[current_level]} (уровень {current_level}).')
        return
    
    update_user(user_id, balance=user['balance'] - prices[level])
    end_date = (datetime.now() + timedelta(days=days[level])).isoformat()
    update_user(user_id, vip_level=level, vip_end=end_date)
    
    bot.send_message(msg.chat.id, f'✅ Вы купили {names[level]} на {days[level]} дней!')
    notify_all_players(f'👑 *VIP*: {format_player_name(user["game_nick"])} повысил VIP до {level} уровня!')

# ============================================================
# ИНВЕНТАРЬ
# ============================================================

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
    
    text = f"✅ **VIP-УРОВЕНЬ ПОВЫШЕН!**\nВаш VIP-уровень: {current_vip} → **{new_vip_level}** 👑\n\n🌟 **Ваши бонусы:**\n💰 +{int((coin_multiplier-1)*100)}% к монетам\n⭐ +{int((exp_multiplier-1)*100)}% к опыту\n🛒 Скидка {int(shop_discount*100)}% в магазине"
    
    bot.send_message(user_id, text, parse_mode='Markdown')
    notify_all_players(f'👑 *VIP*: {format_player_name(user["game_nick"])} повысил VIP до {new_vip_level} уровня!')

# ============================================================
# МАГАЗИН
# ============================================================

SHOP_ITEMS = {
    1: {'id': 1, 'name': '🍎 Яблоко', 'price': 50, 'category': 'food', 'type': 'food', 'effect': {'energy': 10}},
    2: {'id': 2, 'name': '🍌 Банан', 'price': 80, 'category': 'food', 'type': 'food', 'effect': {'energy': 15}},
    3: {'id': 3, 'name': '🍕 Пицца', 'price': 150, 'category': 'food', 'type': 'food', 'effect': {'energy': 30}},
    4: {'id': 4, 'name': '🍔 Бургер', 'price': 200, 'category': 'food', 'type': 'food', 'effect': {'energy': 40}},
    5: {'id': 5, 'name': '⚡ Энергетик', 'price': 300, 'category': 'food', 'type': 'food', 'effect': {'energy': 50}},
    16: {'id': 16, 'name': '🎟️ Билет в казино', 'price': 100, 'category': 'ticket', 'type': 'ticket', 'effect': {'free_game': True}},
    19: {'id': 19, 'name': '💎 Алмаз', 'price': 200, 'category': 'gem', 'type': 'gem', 'effect': {'sell_price': 300}},
    100: {'id': 100, 'name': '📜 Свиток повышения VIP', 'price': 50000, 'category': 'scroll', 'type': 'scroll', 'effect': {'vip_upgrade': 1}, 'rarity': '🌟 Легендарный'},
    200: {'id': 200, 'name': '🟢 VIP 1 (7 дней)', 'price': 500, 'category': 'premium', 'type': 'vip', 'effect': {'vip_level': 1, 'days': 7}},
    201: {'id': 201, 'name': '🔵 VIP 2 (14 дней)', 'price': 2000, 'category': 'premium', 'type': 'vip', 'effect': {'vip_level': 2, 'days': 14}},
    202: {'id': 202, 'name': '🟣 VIP 3 (30 дней)', 'price': 5000, 'category': 'premium', 'type': 'vip', 'effect': {'vip_level': 3, 'days': 30}},
    203: {'id': 203, 'name': '🔴 VIP 4 (60 дней)', 'price': 15000, 'category': 'premium', 'type': 'vip', 'effect': {'vip_level': 4, 'days': 60}},
    204: {'id': 204, 'name': '👑 VIP 5 (90 дней)', 'price': 50000, 'category': 'premium', 'type': 'vip', 'effect': {'vip_level': 5, 'days': 90}},
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
        elif data.get('type') == 'vip':
            text += f"   VIP {data['effect']['vip_level']} на {data['effect']['days']} дней\n"
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
    
    if final_price >= 5000:
        notify_all_players(f'🛒 *Покупка*: {format_player_name(user["game_nick"])} купил «{item_data["name"]}» за {final_price} монет!')
    
    if item_data.get('type') == 'vip':
        vip_level = item_data['effect']['vip_level']
        days = item_data['effect']['days']
        end_date = (datetime.now() + timedelta(days=days)).isoformat()
        update_user(user_id, vip_level=vip_level, vip_end=end_date)
        bot.send_message(msg.chat.id, f'✅ VIP {vip_level} активирован на {days} дней!')
        notify_all_players(f'👑 *VIP*: {format_player_name(user["game_nick"])} купил VIP {vip_level}!')
        return

# ============================================================
# ПРЕМИУМ ПАСС (ОБРАБОТЧИКИ)
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🎖️ Премиум Пасс')
def premium_pass_menu(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    pp_level = user.get('pp_level', 0)
    pp_exp = user.get('pp_exp', 0)
    tier = get_pp_tier(user_id)
    max_level = get_pp_max_level(user_id)
    
    next_level_exp = PP_EXP_PER_LEVEL
    progress = pp_exp % next_level_exp
    percent = int(progress / next_level_exp * 100) if next_level_exp > 0 else 0
    bar = '█' * (percent // 10) + '░' * (10 - (percent // 10))
    
    tier_data = PP_TIERS.get(tier, {})
    
    text = f"""🎖️ **ПРЕМИУМ ПАСС — СЕЗОН {PP_SEASON}**

📊 Ваш уровень: {pp_level} / {max_level}
⭐ Прогресс: [{bar}] {percent}%
🎯 Уровень Пасса: {tier_data.get('name', '🆓 Free')}

🌟 **Бонусы:**
💰 +{int(tier_data.get('coin_bonus', 0)*100)}% к монетам
⭐ +{int(tier_data.get('exp_bonus', 0)*100)}% к опыту
🛒 Скидка {int(tier_data.get('shop_discount', 0)*100)}% в магазине

🎁 Награды на этом уровне:
"""
    
    rewards = PP_REWARDS.get(pp_level + 1, {})
    if rewards.get('free'):
        text += f'🆓 +{rewards["free"].get("coins", 0)} монет, +{rewards["free"].get("exp", 0)} опыта\n'
    if rewards.get('premium'):
        text += f'⭐ +{format_reward_text(rewards["premium"])}\n'
    if rewards.get('premium_plus'):
        text += f'👑 Premium+: +{format_reward_text(rewards["premium_plus"])}\n'
    
    text += f"""
⏳ До следующего уровня: {next_level_exp - progress} опыта
📅 Сезон заканчивается: {PP_END_DATE}
"""
    
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        telebot.types.InlineKeyboardButton('📋 Все награды', callback_data='pp_rewards'),
        telebot.types.InlineKeyboardButton('🛒 Купить Premium', callback_data='pp_buy_premium')
    )
    keyboard.add(
        telebot.types.InlineKeyboardButton('👑 Купить Premium+', callback_data='pp_buy_premium_plus'),
        telebot.types.InlineKeyboardButton('🎁 Забрать награду', callback_data='pp_collect')
    )
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'pp_rewards')
def pp_show_rewards(call):
    text = '🎖️ **ВСЕ НАГРАДЫ ПРЕМИУМ ПАССА**\n\n'
    
    for level in range(1, PP_MAX_LEVEL + 1):
        rewards = PP_REWARDS.get(level, {})
        free = rewards.get('free', {})
        premium = rewards.get('premium', {})
        premium_plus = rewards.get('premium_plus', {})
        
        free_text = format_reward_text(free)
        premium_text = format_reward_text(premium)
        premium_plus_text = format_reward_text(premium_plus)
        
        text += f"**Уровень {level}:**\n"
        text += f"  🆓 {free_text}\n"
        text += f"  ⭐ {premium_text}\n"
        text += f"  👑 {premium_plus_text}\n\n"
        
        if level % 10 == 0:
            text += '━━━━━━━━━━━━━━━━━━━━━\n\n'
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'pp_buy_premium')
def pp_buy_premium(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    tier = get_pp_tier(user_id)
    if tier in ['premium', 'premium_plus']:
        bot.answer_callback_query(call.id, '❌ У вас уже есть Premium или Premium+!')
        return
    
    price = PP_TIERS['premium']['price']
    if user['balance'] < price:
        bot.answer_callback_query(call.id, f'❌ Не хватает {price - user["balance"]} монет.')
        return
    
    update_user(user_id, balance=user['balance'] - price, pp_tier='premium')
    bot.answer_callback_query(call.id, '✅ Premium активирован!')
    bot.send_message(call.message.chat.id, '⭐ **PREMIUM АКТИВИРОВАН!**\n\n💰 +10% к монетам\n⭐ +10% к опыту\n🛒 Скидка 10% в магазине\n📊 Открыто до 30 уровня!')
    notify_all_players(f'⭐ {format_player_name(user["game_nick"])} купил Премиум Пасс Premium!')

@bot.callback_query_handler(func=lambda call: call.data == 'pp_buy_premium_plus')
def pp_buy_premium_plus(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    tier = get_pp_tier(user_id)
    if tier == 'premium_plus':
        bot.answer_callback_query(call.id, '❌ У вас уже есть Premium+!')
        return
    
    price = PP_TIERS['premium_plus']['price']
    if user['balance'] < price:
        bot.answer_callback_query(call.id, f'❌ Не хватает {price - user["balance"]} монет.')
        return
    
    update_user(user_id, balance=user['balance'] - price, pp_tier='premium_plus')
    bot.answer_callback_query(call.id, '✅ Premium+ активирован!')
    bot.send_message(call.message.chat.id, '👑 **PREMIUM+ АКТИВИРОВАН!**\n\n💰 +25% к монетам\n⭐ +25% к опыту\n🛒 Скидка 20% в магазине\n📊 Открыто до 40 уровня!')
    notify_all_players(f'👑 {format_player_name(user["game_nick"])} купил Премиум Пасс Premium+!')

@bot.callback_query_handler(func=lambda call: call.data == 'pp_collect')
def pp_collect_reward(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    pp_level = user.get('pp_level', 0)
    
    if pp_level == 0:
        bot.answer_callback_query(call.id, '❌ У вас ещё нет уровней.')
        return
    
    success, msg = collect_pp_reward(user_id, pp_level)
    bot.answer_callback_query(call.id, msg)
    if success:
        bot.send_message(call.message.chat.id, f'✅ {msg}')

# ============================================================
# ТОРГОВЛЯ
# ============================================================

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
        
        if item_data.get('rarity') in ['🌟 Легендарный', '👑 Мифический']:
            notify_all_players(f'🤝 *Трейд*: {format_player_name(get_user(user_id)["game_nick"])} передал «{item_data["name"]}» {format_player_name(nick)}!')
        
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Используйте формат: номер @ник')

# ============================================================
# КЛАНЫ
# ============================================================

def create_clan(leader_id, name):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT id FROM clans WHERE name = %s', (name,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return False, "❌ Клан с таким названием уже существует!"
    
    cur.execute('''
        INSERT INTO clans (name, leader_id, created_at)
        VALUES (%s, %s, %s)
    ''', (name, leader_id, datetime.now().strftime('%d.%m.%Y')))
    clan_id = cur.lastrowid
    
    cur.execute('''
        INSERT INTO clan_members (user_id, clan_id, role, joined_at)
        VALUES (%s, %s, %s, %s)
    ''', (leader_id, clan_id, 'leader', datetime.now().strftime('%d.%m.%Y %H:%M')))
    
    update_user(leader_id, clan_id=clan_id, clan_role='leader')
    conn.commit()
    cur.close()
    conn.close()
    return True, f"✅ Клан «{name}» успешно создан!"

def get_clan(clan_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM clans WHERE id = %s', (clan_id,))
    clan = cur.fetchone()
    cur.close()
    conn.close()
    return clan

def get_clan_by_name(name):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM clans WHERE name = %s', (name,))
    clan = cur.fetchone()
    cur.close()
    conn.close()
    return clan

def get_clan_members(clan_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT u.id as user_id, u.game_nick, cm.role, cm.joined_at 
        FROM clan_members cm 
        JOIN users u ON cm.user_id = u.id 
        WHERE cm.clan_id = %s 
        ORDER BY 
            CASE cm.role 
                WHEN 'leader' THEN 1 
                WHEN 'deputy' THEN 2 
                ELSE 3 
            END
    ''', (clan_id,))
    members = cur.fetchall()
    cur.close()
    conn.close()
    return members

def get_user_clan(user_id):
    user = get_user(user_id)
    if not user or not user.get('clan_id'):
        return None
    return get_clan(user['clan_id'])

def add_clan_member(user_id, clan_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO clan_members (user_id, clan_id, role, joined_at)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, clan_id, 'member', datetime.now().strftime('%d.%m.%Y %H:%M')))
    conn.commit()
    cur.close()
    conn.close()
    update_user(user_id, clan_id=clan_id, clan_role='member')
    update_clan_member_count(clan_id)

def remove_clan_member(user_id, clan_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM clan_members WHERE user_id = %s AND clan_id = %s', (user_id, clan_id))
    conn.commit()
    cur.close()
    conn.close()
    update_user(user_id, clan_id=None, clan_role=None)
    update_clan_member_count(clan_id)

def update_clan_member_count(clan_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM clan_members WHERE clan_id = %s', (clan_id,))
    count = cur.fetchone()[0]
    cur.execute('UPDATE clans SET member_count = %s WHERE id = %s', (count, clan_id))
    conn.commit()
    cur.close()
    conn.close()

def get_all_clans():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM clans ORDER BY rating DESC, member_count DESC')
    clans = cur.fetchall()
    cur.close()
    conn.close()
    return clans

def get_clan_rating(clan_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT COALESCE(SUM(u.balance), 0) 
        FROM clan_members cm 
        JOIN users u ON cm.user_id = u.id 
        WHERE cm.clan_id = %s
    ''', (clan_id,))
    total_balance = cur.fetchone()[0]
    
    cur.execute('UPDATE clans SET rating = %s WHERE id = %s', (total_balance, clan_id))
    conn.commit()
    cur.close()
    conn.close()
    return total_balance

@bot.message_handler(func=lambda m: m.text == '🏰 Кланы')
def clans_main(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    clan = get_user_clan(user_id)
    
    if clan:
        members = get_clan_members(clan['id'])
        rating = get_clan_rating(clan['id'])
        
        text = f"🏰 **КЛАН: {clan['name']}**\n\n"
        text += f"👥 Участников: {clan['member_count']}\n"
        text += f"💰 Банк клана: {clan['bank']} монет\n"
        text += f"🏆 Рейтинг: {rating} монет\n"
        text += f"📅 Создан: {clan['created_at']}\n\n"
        text += "👑 Лидер: "
        
        for member in members:
            if member['role'] == 'leader':
                text += f"@{member['game_nick']}\n"
        
        bot.send_message(msg.chat.id, text, parse_mode='Markdown', reply_markup=clan_member_keyboard)
    else:
        text = f"🏰 **КЛАНЫ**\n\n💰 Ваш баланс: {user['balance']} монет\n📋 У вас нет клана.\n\nВы можете:\n1. Создать свой клан за 10 000 монет\n2. Вступить в существующий клан"
        bot.send_message(msg.chat.id, text, parse_mode='Markdown', reply_markup=clan_keyboard)

@bot.message_handler(func=lambda m: m.text == '🏰 Создать клан')
def create_clan_start(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    if user.get('clan_id'):
        bot.send_message(msg.chat.id, '❌ Вы уже состоите в клане!')
        return
    
    if user['balance'] < 10000:
        bot.send_message(msg.chat.id, f'❌ Недостаточно монет! Нужно 10 000, у вас {user["balance"]}.')
        return
    
    bot.send_message(msg.chat.id, '🏰 **СОЗДАНИЕ КЛАНА**\n\nСтоимость: 10 000 монет\n\nВведите название клана (от 3 до 20 символов):', parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_create_clan)

def process_create_clan(msg):
    user_id = msg.from_user.id
    name = msg.text.strip()
    
    if len(name) < 3 or len(name) > 20:
        bot.send_message(msg.chat.id, '❌ Название должно быть от 3 до 20 символов.')
        return
    
    if get_clan_by_name(name):
        bot.send_message(msg.chat.id, '❌ Клан с таким названием уже существует!')
        return
    
    user = get_user(user_id)
    if user['balance'] < 10000:
        bot.send_message(msg.chat.id, '❌ Недостаточно монет!')
        return
    
    update_user(user_id, balance=user['balance'] - 10000)
    success, msg_text = create_clan(user_id, name)
    bot.send_message(msg.chat.id, msg_text)
    
    if success:
        notify_all_players(f'🏰 *Новый клан*: «{name}» создан лидером {format_player_name(user["game_nick"])}!')

@bot.message_handler(func=lambda m: m.text == '📋 Список кланов')
def list_clans(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    clans = get_all_clans()
    if not clans:
        bot.send_message(msg.chat.id, '📭 Кланов пока нет. Создайте первый!')
        return
    
    text = '🏰 **СПИСОК КЛАНОВ**\n\n'
    for i, clan in enumerate(clans[:20], 1):
        text += f"{i}. **{clan['name']}** — {clan['member_count']} участников\n"
        text += f"   💰 Рейтинг: {clan['rating']} монет\n"
    
    text += '\nВведите название клана для вступления:'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_join_clan)

def process_join_clan(msg):
    user_id = msg.from_user.id
    name = msg.text.strip()
    
    user = get_user(user_id)
    if user.get('clan_id'):
        bot.send_message(msg.chat.id, '❌ Вы уже состоите в клане!')
        return
    
    clan = get_clan_by_name(name)
    if not clan:
        bot.send_message(msg.chat.id, '❌ Клан не найден.')
        return
    
    add_clan_member(user_id, clan['id'])
    bot.send_message(msg.chat.id, f'✅ Вы вступили в клан «{clan["name"]}»!')
    notify_all_players(f'🏰 {format_player_name(user["game_nick"])} вступил в клан «{clan["name"]}»!')

@bot.message_handler(func=lambda m: m.text == '📊 Топ кланов')
def top_clans(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    clans = get_all_clans()
    if not clans:
        bot.send_message(msg.chat.id, '📭 Кланов пока нет.')
        return
    
    text = '🏆 **ТОП-10 КЛАНОВ**\n\n'
    for i, clan in enumerate(clans[:10], 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        text += f"{medal} **{clan['name']}** — {clan['member_count']} участников\n"
        text += f"   💰 {clan['rating']} монет\n"
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💬 Чат клана')
def clan_chat(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    if not user.get('clan_id'):
        bot.send_message(msg.chat.id, '❌ Вы не состоите в клане!')
        return
    
    clan = get_clan(user['clan_id'])
    bot.send_message(msg.chat.id, f'💬 **ЧАТ КЛАНА {clan["name"]}**\n\nНапишите сообщение для отправки в чат:', parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_clan_chat)

def process_clan_chat(msg):
    user_id = msg.from_user.id
    text = msg.text.strip()
    
    user = get_user(user_id)
    if not user.get('clan_id'):
        bot.send_message(msg.chat.id, '❌ Вы не состоите в клане!')
        return
    
    clan = get_clan(user['clan_id'])
    members = get_clan_members(user['clan_id'])
    
    sent = 0
    for member in members:
        try:
            bot.send_message(member['user_id'], f'💬 [{clan["name"]}] @{user["game_nick"]}: {text}')
            sent += 1
        except:
            pass
    
    bot.send_message(msg.chat.id, f'✅ Сообщение отправлено {sent} участникам клана!')

@bot.message_handler(func=lambda m: m.text == '🚪 Выйти из клана')
def leave_clan(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Войдите.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    if not user.get('clan_id'):
        bot.send_message(msg.chat.id, '❌ Вы не состоите в клане!')
        return
    
    clan = get_clan(user['clan_id'])
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM clan_members WHERE user_id = %s AND clan_id = %s AND role = %s', 
                (user_id, user['clan_id'], 'leader'))
    is_leader = cur.fetchone() is not None
    cur.close()
    conn.close()
    
    if is_leader:
        members = get_clan_members(user['clan_id'])
        if len(members) > 1:
            for member in members:
                if member['role'] != 'leader':
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute('UPDATE clan_members SET role = %s WHERE user_id = %s AND clan_id = %s', 
                                ('leader', member['user_id'], user['clan_id']))
                    conn.commit()
                    cur.close()
                    conn.close()
                    update_user(member['user_id'], clan_role='leader')
                    bot.send_message(member['user_id'], f'👑 Вы стали новым лидером клана «{clan["name"]}»!')
                    break
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('DELETE FROM clans WHERE id = %s', (user['clan_id'],))
            cur.execute('DELETE FROM clan_members WHERE clan_id = %s', (user['clan_id'],))
            conn.commit()
            cur.close()
            conn.close()
            bot.send_message(msg.chat.id, f'🗑️ Клан «{clan["name"]}» удалён.')
            update_user(user_id, clan_id=None, clan_role=None)
            return
    
    remove_clan_member(user_id, user['clan_id'])
    bot.send_message(msg.chat.id, f'✅ Вы вышли из клана «{clan["name"]}».')

# ============================================================
# АДМИН-ПАНЕЛЬ
# ============================================================

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

@bot.message_handler(func=lambda m: m.text == '🔙 Назад')
def back_to_main(msg):
    user_id = msg.from_user.id
    if is_logged_in(user_id):
        bot.send_message(msg.chat.id, '🏠 Главное меню', reply_markup=main_keyboard)
    else:
        bot.send_message(msg.chat.id, '🔐 Войдите', reply_markup=auth_keyboard)

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
    
    text = f"""
📊 **СТАТИСТИКА**
👥 Игроков: {total_users}
💰 Общий баланс: {total_balance:,}
🏆 Макс. баланс: {max_balance:,}
🏢 Бизнесов куплено: {total_businesses}/50
"""
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
    text = f"""
📋 **ИНФОРМАЦИЯ**
👤 Ник: {user['game_nick']}
🆔 ID: {user['id']}
💰 Баланс: {user['balance']} монет
📈 Уровень: {user['level']}
⭐ Опыт: {user['exp']}
👑 VIP: {user.get('vip_level', 0)}
🚫 Бан: {"Да" if user['is_banned'] else "Нет"}
"""
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

@bot.message_handler(func=lambda m: m.text == '👑 Панель создателя' and is_admin(m.from_user.id))
def creator_panel_from_admin(msg):
    creator_panel(msg)

@bot.message_handler(commands=['creator'])
def creator_panel(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    text = """👑 **ПАНЕЛЬ СОЗДАТЕЛЯ**

Добро пожаловать, Создатель! 👋

🔐 Доступны все функции управления:

📦 Выдать предмет
👑 Выдать VIP
⭐ Выдать опыт
💰 Изменить баланс
👤 Удалить аккаунт
🗑️ Удалить клан
🏰 Управление кланами
🎖️ Управление Премиум Пассом
📊 Статистика сервера
👥 Список игроков
📢 Глобальная рассылка
📝 Логи создателя
💾 Экспорт БД
🔄 Резервное копирование
📤 Восстановить БД
⬅️ Назад

Выберите действие:"""
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown', reply_markup=creator_keyboard)

# ============================================================
# КОМАНДЫ СОЗДАТЕЛЯ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '📦 Выдать предмет' and is_admin(m.from_user.id))
def give_item_start(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    text = '📦 **ВЫДАТЬ ПРЕДМЕТ**\n\nСписок предметов:\n'
    for item_id, data in SHOP_ITEMS.items():
        text += f"{item_id}. {data['name']}\n"
    
    text += '\nВведите: @ник номер_предмета количество\nПример: @alex88 100 1'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_give_item)

def process_give_item(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        parts = msg.text.split()
        if len(parts) != 3:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: @ник номер_предмета количество')
            return
        
        nick = parts[0].replace('@', '')
        item_id = int(parts[1])
        count = int(parts[2])
        
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        
        if item_id not in SHOP_ITEMS:
            bot.send_message(msg.chat.id, '❌ Предмет не найден.')
            return
        
        if count <= 0:
            bot.send_message(msg.chat.id, '❌ Количество должно быть больше 0.')
            return
        
        item_data = SHOP_ITEMS[item_id]
        
        if item_data.get('type') == 'vip':
            vip_level = item_data['effect']['vip_level']
            days = item_data['effect']['days']
            end_date = (datetime.now() + timedelta(days=days)).isoformat()
            update_user(user['id'], vip_level=vip_level, vip_end=end_date)
            bot.send_message(msg.chat.id, f'✅ {nick} получил VIP {vip_level} на {days} дней!')
            bot.send_message(user['id'], f'👑 Вы получили VIP {vip_level} на {days} дней от создателя!')
            return
        
        add_item(user['id'], item_id, count)
        bot.send_message(msg.chat.id, f'✅ {nick} получил {item_data["name"]} x{count}!')
        bot.send_message(user['id'], f'📦 Вы получили {item_data["name"]} x{count} от создателя!')
        log_creator_action(f'Выдал {item_data["name"]} x{count} игроку {nick}')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка: {e}')

@bot.message_handler(func=lambda m: m.text == '👑 Выдать VIP' and is_admin(m.from_user.id))
def give_vip_start(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    text = """👑 **ВЫДАТЬ VIP**

Введите: @ник уровень_вип (1-5) количество_дней
Пример: @alex88 3 30

Уровни VIP:
1 - VIP 1 (бонус 5%)
2 - VIP 2 (бонус 10%)
3 - VIP 3 (бонус 20%)
4 - VIP 4 (бонус 30%)
5 - VIP 5 (бонус 50%)"""
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_give_vip)

def process_give_vip(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        parts = msg.text.split()
        if len(parts) != 3:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: @ник уровень_вип (1-5) количество_дней')
            return
        
        nick = parts[0].replace('@', '')
        vip_level = int(parts[1])
        days = int(parts[2])
        
        if vip_level < 1 or vip_level > 5:
            bot.send_message(msg.chat.id, '❌ Уровень VIP должен быть от 1 до 5.')
            return
        
        if days <= 0:
            bot.send_message(msg.chat.id, '❌ Количество дней должно быть больше 0.')
            return
        
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        
        end_date = (datetime.now() + timedelta(days=days)).isoformat()
        update_user(user['id'], vip_level=vip_level, vip_end=end_date)
        
        bot.send_message(msg.chat.id, f'✅ {nick} получил VIP {vip_level} на {days} дней!')
        bot.send_message(user['id'], f'👑 Вы получили VIP {vip_level} на {days} дней от создателя!')
        log_creator_action(f'Выдал VIP {vip_level} на {days} дней игроку {nick}')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка: {e}')

@bot.message_handler(func=lambda m: m.text == '⭐ Выдать опыт' and is_admin(m.from_user.id))
def give_exp_creator_start(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '⭐ **ВЫДАТЬ ОПЫТ**\n\nВведите: @ник количество_опыта\nПример: @alex88 100', parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_give_exp_creator)

def process_give_exp_creator(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: @ник количество_опыта')
            return
        
        nick = parts[0].replace('@', '')
        amount = int(parts[1])
        
        if amount <= 0:
            bot.send_message(msg.chat.id, '❌ Опыт должен быть больше 0.')
            return
        
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        
        add_exp(user['id'], amount)
        bot.send_message(msg.chat.id, f'✅ {nick} получил {amount} опыта!')
        bot.send_message(user['id'], f'⭐ Вы получили {amount} опыта от создателя!')
        log_creator_action(f'Выдал {amount} опыта игроку {nick}')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка: {e}')

@bot.message_handler(func=lambda m: m.text == '💰 Изменить баланс' and is_admin(m.from_user.id))
def change_balance_start(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '💰 **ИЗМЕНИТЬ БАЛАНС**\n\nВведите: @ник сумма\nПример: @alex88 +1000 или @alex88 -500', parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_change_balance)

def process_change_balance(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
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
        
        new_balance = user['balance'] + amount
        if new_balance < 0:
            new_balance = 0
        
        update_user(user['id'], balance=new_balance)
        
        text = f'✅ Баланс {nick} изменён на {new_balance} монет!'
        if amount > 0:
            text += f' (+{amount})'
        else:
            text += f' ({amount})'
        
        bot.send_message(msg.chat.id, text)
        bot.send_message(user['id'], f'💰 Ваш баланс изменён создателем на {new_balance} монет!')
        log_creator_action(f'Изменил баланс {nick} на {new_balance} ({amount})')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка: {e}')

@bot.message_handler(func=lambda m: m.text == '🏰 Управление кланами' and is_admin(m.from_user.id))
def manage_clans_start(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    clans = get_all_clans()
    if not clans:
        bot.send_message(msg.chat.id, '📭 Нет кланов для управления.')
        return
    
    text = '🏰 **УПРАВЛЕНИЕ КЛАНАМИ**\n\n'
    for i, clan in enumerate(clans, 1):
        text += f"{i}. **{clan['name']}** — {clan['member_count']} участников\n"
    
    text += '\nВведите номер клана для удаления:'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_delete_clan_admin)

def process_delete_clan_admin(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        index = int(msg.text.strip()) - 1
    except:
        bot.send_message(msg.chat.id, '❌ Введите номер клана.')
        return
    
    clans = get_all_clans()
    if index < 0 or index >= len(clans):
        bot.send_message(msg.chat.id, '❌ Клан не найден.')
        return
    
    clan = clans[index]
    bot.send_message(msg.chat.id, f'✏️ Введите причину удаления клана «{clan["name"]}»:')
    bot.register_next_step_handler(msg, process_delete_clan_reason, clan)

def process_delete_clan_reason(msg, clan):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    reason = msg.text.strip()
    if not reason:
        reason = 'Причина не указана'
    
    clan_id = clan['id']
    clan_name = clan['name']
    members = get_clan_members(clan_id)
    
    for member in members:
        try:
            bot.send_message(member['user_id'], f'🗑️ **Клан «{clan_name}» удалён администратором!**\n\n📝 Причина: {reason}')
        except:
            pass
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM clan_members WHERE clan_id = %s', (clan_id,))
    cur.execute('DELETE FROM clans WHERE id = %s', (clan_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    for member in members:
        try:
            update_user(member['user_id'], clan_id=None, clan_role=None)
        except:
            pass
    
    notify_all_players(f'🗑️ *Клан «{clan_name}» удалён администратором!*\n📝 Причина: {reason}')
    bot.send_message(msg.chat.id, f'✅ Клан «{clan_name}» удалён!\n📝 Причина: {reason}')
    log_creator_action(f'Удалил клан {clan_name} (причина: {reason})')

@bot.message_handler(func=lambda m: m.text == '🎖️ Управление Премиум Пассом' and is_admin(m.from_user.id))
def manage_pp_start(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    text = """🎖️ **УПРАВЛЕНИЕ ПРЕМИУМ ПАССОМ**

1️⃣ Выдать Free Пасс (@ник)
2️⃣ Выдать Premium Пасс (@ник)
3️⃣ Выдать Premium+ Пасс (@ник)
4️⃣ Сбросить прогресс (@ник)

Введите номер и ник:
Пример: 2 @alex88"""
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_manage_pp)

def process_manage_pp(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: номер @ник')
            return
        
        action = int(parts[0])
        nick = parts[1].replace('@', '')
        
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, '❌ Игрок не найден.')
            return
        
        if action == 1:
            update_user(user['id'], pp_tier='free', pp_level=0, pp_exp=0)
            bot.send_message(msg.chat.id, f'✅ {nick} получил Free Пасс!')
        elif action == 2:
            update_user(user['id'], pp_tier='premium', pp_level=0, pp_exp=0)
            bot.send_message(msg.chat.id, f'✅ {nick} получил Premium Пасс!')
        elif action == 3:
            update_user(user['id'], pp_tier='premium_plus', pp_level=0, pp_exp=0)
            bot.send_message(msg.chat.id, f'✅ {nick} получил Premium+ Пасс!')
        elif action == 4:
            update_user(user['id'], pp_level=0, pp_exp=0, pp_rewards_collected='[]')
            bot.send_message(msg.chat.id, f'✅ Прогресс {nick} сброшен!')
        else:
            bot.send_message(msg.chat.id, '❌ Неверный номер действия.')
        
        log_creator_action(f'Управление Премиум Пассом: {nick} (действие {action})')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка: {e}')

@bot.message_handler(func=lambda m: m.text == '📊 Статистика сервера' and is_admin(m.from_user.id))
def creator_stats(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT COUNT(*) FROM users')
        total_users = cur.fetchone()[0]
        
        cur.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
        total_balance = cur.fetchone()[0]
        
        cur.execute('SELECT COALESCE(MAX(balance), 0) FROM users')
        max_balance = cur.fetchone()[0]
        
        cur.execute('SELECT COALESCE(AVG(balance), 0) FROM users')
        avg_balance = round(cur.fetchone()[0], 1)
        
        cur.execute('SELECT COUNT(*) FROM users WHERE vip_level > 0')
        vip_users = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM businesses WHERE owner_id IS NOT NULL')
        bought_businesses = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM users WHERE pp_tier = %s', ('premium',))
        premium_users = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM users WHERE pp_tier = %s', ('premium_plus',))
        premium_plus_users = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM clans')
        total_clans = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        text = f"""📊 **СТАТИСТИКА СЕРВЕРА**

👥 **Игроки:**
• Всего: {total_users}
• С VIP: {vip_users}

💰 **Экономика:**
• Общий баланс: {total_balance:,}
• Макс. баланс: {max_balance:,}
• Средний баланс: {avg_balance}

🏢 **Бизнесы:**
• Куплено: {bought_businesses}/50

🎖️ **Премиум Пасс:**
• Premium: {premium_users}
• Premium+: {premium_plus_users}

🏰 **Кланы:**
• Всего кланов: {total_clans}

📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка: {e}')

@bot.message_handler(func=lambda m: m.text == '👥 Список игроков' and is_admin(m.from_user.id))
def creator_player_list(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT game_nick, balance, level, vip_level, admin_level FROM users ORDER BY balance DESC')
    players = cur.fetchall()
    cur.close()
    conn.close()
    
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    
    text = '👥 **СПИСОК ИГРОКОВ**\n\n'
    for i, (nick, balance, level, vip, admin) in enumerate(players, 1):
        vip_emoji = ' 👑' if vip > 0 else ''
        admin_emoji = ' ⭐' if admin > 0 else ''
        text += f"{i}. {nick} — {balance} монет (ур. {level}){vip_emoji}{admin_emoji}\n"
        if i % 20 == 0:
            text += '\nПоказаны первые 20 игроков.'
            break
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📢 Глобальная рассылка' and is_admin(m.from_user.id))
def global_broadcast_start(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    bot.send_message(msg.chat.id, '📢 **ГЛОБАЛЬНАЯ РАССЫЛКА**\n\nВведите текст для отправки ВСЕМ игрокам:', parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_global_broadcast)

def process_global_broadcast(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    text = msg.text
    users = get_all_users()
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f'📢 *ГЛОБАЛЬНОЕ СООБЩЕНИЕ ОТ СОЗДАТЕЛЯ*\n\n{text}', parse_mode='Markdown')
            sent += 1
        except:
            pass
    
    bot.send_message(msg.chat.id, f'✅ Сообщение отправлено {sent} пользователям!')
    log_creator_action(f'Глобальная рассылка: {text[:50]}...')

@bot.message_handler(func=lambda m: m.text == '📝 Логи создателя' and is_admin(m.from_user.id))
def creator_logs(msg):
    user_id = msg.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(msg.chat.id, '❌ Только для создателя!')
        return
    
    try:
        with open('creator_logs.txt', 'r') as f:
            logs = f.read().splitlines()
            last_logs = logs[-30:] if len(logs) > 30 else logs
            text = '📝 **ПОСЛЕДНИЕ 30 ДЕЙСТВИЙ СОЗДАТЕЛЯ**\n\n' + '\n'.join(last_logs)
            bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    except:
        bot.send_message(msg.chat.id, '📭 Логов пока нет.')

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == '__main__':
    print('✅ Бот запущен!')
    bot.remove_webhook()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f'❌ Сетевая ошибка: {e}. Перезапуск через 10 секунд...')
            time.sleep(10)
        except Exception as e:
            print(f'❌ Ошибка: {e}. Перезапуск через 5 секунд...')
            time.sleep(5)
