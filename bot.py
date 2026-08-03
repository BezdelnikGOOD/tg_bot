import os
import random
import hashlib
import time
from datetime import datetime
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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ===== ИНИЦИАЛИЗАЦИЯ =====
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
                secret_items INTEGER DEFAULT 0
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
main_keyboard.add('📊 Топ игроков', '🎁 Кейсы')
main_keyboard.add('🏆 Топ кейсов', '⭐ Топ секретов')
main_keyboard.add('🚪 Выйти')

creator_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
creator_keyboard.add('💰 Изменить баланс', '👤 Удалить аккаунт')
creator_keyboard.add('📊 Статистика сервера', '👥 Список игроков')
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
    reg_date = datetime.now().strftime('%d.%m.%Y %H:%M')
    
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
# ПРОФИЛЬ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    username = msg.from_user.username
    display_username = f'@{username}' if username else 'Нет юза'
    
    text = f'''
👤 ПРОФИЛЬ

📛 Ник: {user['game_nick']}
🔖 Юзернейм: {display_username}
💰 Баланс: {user['balance']} монет
🎁 Открыто кейсов: {user.get('cases_opened', 0)}
⭐ Секретных предметов: {user.get('secret_items', 0)}
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
# КЕЙСЫ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🎁 Кейсы')
def cases_menu(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_cached_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    text = f'''
🎁 **КЕЙСЫ**

💰 Ваш баланс: {user['balance']} монет

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
    
    bot.send_message(msg.chat.id, text, parse_mode='Markdown', reply_markup=keyboard)

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
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=keyboard)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_buy')
def cancel_buy(call):
    bot.edit_message_text('❌ Покупка отменена.', call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

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
    
    update_user(user_id, balance=user['balance'] - case['price'])
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    msg1 = bot.send_message(call.message.chat.id, f'🎁 ОТКРЫТИЕ КЕЙСА...\n\nВы выбрали: {case["emoji"]} {case["name"]} кейс\n💰 Стоимость: {case["price"]} монет')
    time.sleep(1.5)
    bot.delete_message(call.message.chat.id, msg1.message_id)
    
    msg2 = bot.send_message(call.message.chat.id, '🌀 Крутим...')
    time.sleep(1.5)
    bot.delete_message(call.message.chat.id, msg2.message_id)
    
    total_chance = sum(r['chance'] for r in case['rewards'])
    rand = random.random() * total_chance
    cumulative = 0
    selected_reward = case['rewards'][-1]
    
    for reward in case['rewards']:
        cumulative += reward['chance']
        if rand <= cumulative:
            selected_reward = reward
            break
    
    # Увеличиваем счётчик открытых кейсов
    update_user(user_id, cases_opened=user.get('cases_opened', 0) + 1)
    
    if selected_reward['type'] == 'coins':
        amount = random.randint(selected_reward['min'], selected_reward['max'])
        update_user(user_id, balance=user['balance'] - case['price'] + amount)
        
        text = f'''
🎁 ОТКРЫТИЕ КЕЙСА... ✅

💰 ВЫПАЛО: {amount} монет!

📦 Ваш баланс: {user['balance'] - case['price'] + amount} монет
📊 Всего открыто: {user.get('cases_opened', 0) + 1} кейсов
'''
        bot.send_message(call.message.chat.id, text)
    
    elif selected_reward['type'] == 'secret_jackpot':
        amount = selected_reward['min']
        update_user(user_id, balance=user['balance'] - case['price'] + amount)
        # Увеличиваем счётчик секретных предметов
        update_user(user_id, secret_items=user.get('secret_items', 0) + 1)
        
        text = f'''
⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️
🎉 СЕКРЕТНЫЙ ДЖЕКПОТ!
⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️

💰 +{amount} монет!

Поздравляю! Ты сорвал джекпот! 🍀
📊 Всего открыто: {user.get('cases_opened', 0) + 1} кейсов
⭐ Всего секретов: {user.get('secret_items', 0) + 1}
'''
        bot.send_message(call.message.chat.id, text)
    
    bot.answer_callback_query(call.id)

# ============================================================
# ТОП ПО ОТКРЫТИЮ КЕЙСОВ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🏆 Топ кейсов')
def top_cases(msg):
    user_id = msg.from_user.id
    
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
# ТОП ПО СЕКРЕТНЫМ ПРЕДМЕТАМ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '⭐ Топ секретов')
def top_secrets(msg):
    user_id = msg.from_user.id
    
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
    bot.remove_webhook()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f'❌ Ошибка: {e}. Перезапуск через 5 секунд...')
            time.sleep(5)