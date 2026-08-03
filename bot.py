import os
import random
import hashlib
from datetime import datetime
import telebot
import psycopg2
import psycopg2.extras

# ===== КОНФИГ (ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ) =====
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("❌ Токен не найден! Добавьте переменную окружения TOKEN")

ADMIN_ID = int(os.getenv('ADMIN_ID', 6573154279))
bot = telebot.TeleBot(TOKEN)

# ===== ПОДКЛЮЧЕНИЕ К POSTGRESQL =====
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не найден! Добавьте переменную окружения")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ===== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ =====
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS users')
    cur.execute('''
        CREATE TABLE users (
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
    conn.commit()
    cur.close()
    conn.close()
    print('✅ Таблица users создана')

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

def get_top_players(limit=10):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT game_nick, balance, level FROM users WHERE is_banned = 0 ORDER BY balance DESC LIMIT %s', (limit,))
    players = cur.fetchall()
    cur.close()
    conn.close()
    return players

def get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users')
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

def get_stats():
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
    cur.execute('SELECT COALESCE(AVG(level), 0) FROM users')
    avg_level = round(cur.fetchone()[0], 1)
    cur.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
    banned_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total_users, total_balance, max_balance, avg_balance, avg_level, banned_count

def user_exists(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE id = %s', (user_id,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists

def is_logged_in(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT is_logged_in FROM users WHERE id = %s', (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result and result[0] == 1

def is_banned(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT is_banned FROM users WHERE id = %s', (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result and result[0] == 1

def is_admin_by_nick(nick):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, role FROM users WHERE game_nick = %s', (nick,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user and (user[0] == ADMIN_ID or user[1] == 'admin')

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

def log_admin_action(user_id, action):
    with open('admin_logs.txt', 'a') as f:
        f.write(f'{datetime.now().strftime("%d.%m.%Y %H:%M")} | Админ ID: {user_id} | {action}\n')

# ===== КЛАВИАТУРЫ =====
auth_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
auth_keyboard.add('🔑 Войти', '✨ Зарегистрироваться')

main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_keyboard.add('👤 Профиль', '💰 Баланс')
main_keyboard.add('🎰 Играть', '📊 Топ игроков')
main_keyboard.add('🏷️ Все статусы', '🚪 Выйти')

admin_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
admin_keyboard.add('📊 Статистика', '👥 Список игроков')
admin_keyboard.add('👑 Назначить админа', '📈 Изменить уровень')
admin_keyboard.add('➕ Выдать монеты', '➖ Забрать монеты')
admin_keyboard.add('🎁 Выдать опыт', '🔍 Найти игрока')
admin_keyboard.add('⏳ Бан/Разбан', '🔄 Сброс баланса')
admin_keyboard.add('📢 Рассылка', '🗑️ Удалить аккаунт')
admin_keyboard.add('📋 Логи админа', '⬅️ Назад')

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_progress_bar(exp, level):
    needed = level * 50
    filled = min(exp, needed)
    percent = int((filled / needed) * 10) if needed > 0 else 0
    bar = '█' * percent + '░' * (10 - percent)
    return bar, filled, needed

def get_status(balance):
    if balance >= 100000:
        return '🌟 Легенда', balance, 999999999
    elif balance >= 50000:
        return '💵 Миллионер', 50000, 100000
    elif balance >= 10000:
        return '🏰 Барон', 10000, 50000
    elif balance >= 5000:
        return '🏦 Инвестор', 5000, 10000
    elif balance >= 1000:
        return '👑 Магнат', 1000, 5000
    elif balance >= 500:
        return '💎 Богач', 500, 1000
    elif balance >= 200:
        return '💰 Середняк', 200, 500
    elif balance >= 50:
        return '🪙 Новичок', 50, 200
    elif balance >= 1:
        return '🕊️ Бедняга', 1, 50
    else:
        return '💀 Банкрот', 0, 1

def get_next_status(balance):
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
    for i, (threshold, _) in enumerate(statuses):
        if balance < threshold:
            return statuses[i]
    return None

# ===== АВТОРИЗАЦИЯ =====
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Ваш аккаунт заблокирован. Обратитесь к администратору.')
        return
    if user_exists(user_id):
        if is_logged_in(user_id):
            bot.send_message(msg.chat.id, f'👋 Снова здесь, {msg.from_user.first_name or "Игрок"}!', reply_markup=main_keyboard)
        else:
            bot.send_message(msg.chat.id, '🔐 Вы не авторизованы. Войдите или зарегистрируйтесь.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '👋 Добро пожаловать! Для начала зарегистрируйтесь или войдите.', reply_markup=auth_keyboard)

@bot.message_handler(func=lambda m: m.text == '🔑 Войти')
def login_start(msg):
    user_id = msg.from_user.id
    if not user_exists(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не зарегистрированы. Нажмите "✨ Зарегистрироваться"')
        return
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Ваш аккаунт заблокирован.')
        return
    if is_logged_in(user_id):
        bot.send_message(msg.chat.id, '✅ Вы уже авторизованы!', reply_markup=main_keyboard)
        return
    bot.send_message(msg.chat.id, '🔐 Введите ваш игровой ник:')
    bot.register_next_step_handler(msg, login_nick)

def login_nick(msg):
    nick = msg.text.strip()
    user_id = msg.from_user.id
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, '❌ Игрок с таким ником не найден.')
        return
    bot.send_message(msg.chat.id, '🔑 Введите пароль:')
    bot.register_next_step_handler(msg, login_password, nick)

def login_password(msg, nick):
    password = msg.text.strip()
    user_id = msg.from_user.id
    hashed = hash_password(password)
    user = get_user_by_nick(nick)
    if not user or user['password'] != hashed:
        bot.send_message(msg.chat.id, '❌ Неверный пароль. Попробуйте ещё раз.')
        return
    if user['is_banned']:
        bot.send_message(msg.chat.id, '🚫 Ваш аккаунт заблокирован.')
        return
    update_user(user_id, is_logged_in=1)
    bot.send_message(msg.chat.id, f'✅ Добро пожаловать, {nick}!', reply_markup=main_keyboard)

@bot.message_handler(func=lambda m: m.text == '✨ Зарегистрироваться')
def register_start(msg):
    bot.send_message(msg.chat.id, '📝 Придумайте игровой ник (от 3 до 15 символов, без пробелов):')
    bot.register_next_step_handler(msg, register_nick)

def register_nick(msg):
    nick = msg.text.strip()
    if len(nick) < 3 or len(nick) > 15 or ' ' in nick:
        bot.send_message(msg.chat.id, '❌ Ник должен быть от 3 до 15 символов без пробелов. Попробуйте ещё раз:')
        bot.register_next_step_handler(msg, register_nick)
        return
    if get_user_by_nick(nick):
        bot.send_message(msg.chat.id, '❌ Этот ник уже занят. Придумайте другой:')
        bot.register_next_step_handler(msg, register_nick)
        return
    bot.send_message(msg.chat.id, '🔑 Придумайте пароль (минимум 6 символов):')
    bot.register_next_step_handler(msg, register_password, nick)

def register_password(msg, nick):
    password = msg.text.strip()
    if len(password) < 6:
        bot.send_message(msg.chat.id, '❌ Пароль должен быть минимум 6 символов. Попробуйте ещё раз:')
        bot.register_next_step_handler(msg, register_password, nick)
        return
    bot.send_message(msg.chat.id, '🔁 Повторите пароль:')
    bot.register_next_step_handler(msg, register_password_confirm, nick, password)

def register_password_confirm(msg, nick, password):
    confirm = msg.text.strip()
    if confirm != password:
        bot.send_message(msg.chat.id, '❌ Пароли не совпадают. Попробуйте ещё раз:')
        bot.register_next_step_handler(msg, register_password_confirm, nick, password)
        return
    user_id = msg.from_user.id
    hashed = hash_password(password)
    create_user(user_id, nick, hashed)
    update_user(user_id, is_logged_in=1)
    bot.send_message(msg.chat.id, f'✅ Поздравляю, {nick}! Ты зарегистрирован и авторизован.', reply_markup=main_keyboard)

@bot.message_handler(func=lambda m: m.text == '🚪 Выйти')
def logout(msg):
    user_id = msg.from_user.id
    update_user(user_id, is_logged_in=0)
    bot.send_message(msg.chat.id, '👋 Вы вышли из аккаунта.', reply_markup=auth_keyboard)

# ===== ПРОФИЛЬ =====
@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Ваш аккаунт заблокирован.')
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
    
    if is_admin(user_id) or user['role'] == 'admin':
        status = '👑 Главный Администратор'
    else:
        status, _, _ = get_status(balance)
    
    bar, filled, needed = get_progress_bar(exp, level)
    
    text = f'''
╔═══════════════════════════════════╗
║          ✦  👤 ПРОФИЛЬ  ✦          ║
╠═══════════════════════════════════╣
║                                   ║
║   📛 Ник: {game_nick}
║   🔖 Юзернейм: {display_username}
║   💰 Баланс: {balance:,} монет
║   📈 Уровень: {level}
║   ⭐ Опыт: {exp} / {needed}
║   📊 Прогресс: [{bar}]
║   📅 В игре с: {reg_date}
║                                   ║
║   🏷️ Статус: {status}
║                                   ║
╚═══════════════════════════════════╝
'''
    bot.send_message(msg.chat.id, text)

# ===== БАЛАНС =====
@bot.message_handler(func=lambda m: m.text == '💰 Баланс')
def balance(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Ваш аккаунт заблокирован.')
        return
    user = get_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    bot.send_message(msg.chat.id, f'💰 Твой баланс: {user["balance"]:,} монет')

# ===== ИГРА =====
@bot.message_handler(func=lambda m: m.text == '🎰 Играть')
def game(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Ваш аккаунт заблокирован.')
        return
    user = get_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    balance = user['balance']
    if balance < 10:
        bot.send_message(msg.chat.id, '❌ Не хватает 10 монет!')
        return
    update_user(user_id, balance=balance - 10)
    win = random.choice([0, 1])
    if win:
        update_user(user_id, balance=balance - 10 + 25)
        level_up, new_level = add_exp(user_id, 10)
        result_text = '🎉 Ты выиграл! +25 монет, +10 опыта'
        if level_up:
            result_text += f'\n🎉 УРОВЕНЬ ПОВЫШЕН! Твой уровень: {new_level}'
    else:
        level_up, new_level = add_exp(user_id, 2)
        result_text = '😢 Ты проиграл. -10 монет, +2 опыта'
        if level_up:
            result_text += f'\n🎉 УРОВЕНЬ ПОВЫШЕН! Твой уровень: {new_level}'
    
    user = get_user(user_id)
    result_text += f'\n💰 Баланс: {user["balance"]}'
    bot.send_message(msg.chat.id, result_text)

# ===== ТОП =====
@bot.message_handler(func=lambda m: m.text == '📊 Топ игроков')
def top_players(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Ваш аккаунт заблокирован.')
        return
    players = get_top_players(10)
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    text = '🏆 ТОП-10 ПО БАЛАНСУ\n\n'
    for i, (game_nick, balance, level) in enumerate(players, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        admin_tag = ' 👑' if is_admin_by_nick(game_nick) else ''
        text += f'{medal} {game_nick} — {balance:,} монет (уровень {level}){admin_tag}\n'
    bot.send_message(msg.chat.id, text)

# ===== ВСЕ СТАТУСЫ =====
@bot.message_handler(func=lambda m: m.text == '🏷️ Все статусы')
def all_statuses(msg):
    user_id = msg.from_user.id
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    if is_banned(user_id):
        bot.send_message(msg.chat.id, '🚫 Ваш аккаунт заблокирован.')
        return
    user = get_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    balance = user['balance']
    
    text = '''
╔═══════════════════════════════════╗
║       ✦  🏷️ СТАТУСЫ  ✦           ║
╠═══════════════════════════════════╣
║                                   ║
║   💀 Банкрот             0        ║
║   🕊️ Бедняга          1 – 49     ║
║   🪙 Новичок          50 – 199   ║
║   💰 Середняк        200 – 499   ║
║   💎 Богач           500 – 999   ║
║   👑 Магнат        1,000 – 4,999 ║
║   🏦 Инвестор      5,000 – 9,999 ║
║   🏰 Барон        10,000 – 49,999║
║   💵 Миллионер    50,000 – 99,999║
║   🌟 Легенда       100,000+      ║
║                                   ║
╠═══════════════════════════════════╣
'''
    
    if is_admin(user_id) or user['role'] == 'admin':
        text += '   👑 Главный Администратор\n'
    
    current_status, threshold, next_threshold = get_status(balance)
    next_status_data = get_next_status(balance)
    
    if next_status_data:
        next_threshold, next_status_name = next_status_data
        remaining = next_threshold - balance
        progress = int((balance - threshold) / (next_threshold - threshold) * 100) if next_threshold > threshold else 0
        bar = '█' * (progress // 10) + '░' * (10 - (progress // 10))
        text += f'''   📌 Твой статус: {current_status}
   📈 До "{next_status_name}": {remaining} монет
   📊 Прогресс: [{bar}] {progress}%
'''
    else:
        text += f'''   📌 Твой статус: {current_status}
   👑 Ты достиг максимального статуса!
   📊 Прогресс: [██████████] 100%
'''
    
    text += '╚═══════════════════════════════════╝'
    bot.send_message(msg.chat.id, text)

# ===== АДМИН-ПАНЕЛЬ =====
@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    user_id = msg.from_user.id
    if not is_admin(user_id):
        bot.send_message(msg.chat.id, '❌ Доступ запрещён.')
        return
    bot.send_message(msg.chat.id, '🔐 Админ-панель\nВыберите действие:', reply_markup=admin_keyboard)

@bot.message_handler(func=lambda m: m.text == '⬅️ Назад' and is_admin(m.from_user.id))
def back_to_main(msg):
    bot.send_message(msg.chat.id, '🏠 Главное меню', reply_markup=main_keyboard)

# 1. Статистика
@bot.message_handler(func=lambda m: m.text == '📊 Статистика' and is_admin(m.from_user.id))
def stats(msg):
    total_users, total_balance, max_balance, avg_balance, avg_level, banned_count = get_stats()
    text = f'''
📊 СТАТИСТИКА СЕРВЕРА

👥 Всего игроков: {total_users}
🚫 Заблокировано: {banned_count}
💰 Общий баланс: {total_balance:,}
🏆 Макс. баланс: {max_balance:,}
📈 Средний баланс: {avg_balance}
📈 Средний уровень: {avg_level}

📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}
'''
    bot.send_message(msg.chat.id, text)
    log_admin_action(msg.from_user.id, 'Просмотр статистики')

# 2. Список игроков
@bot.message_handler(func=lambda m: m.text == '👥 Список игроков' and is_admin(m.from_user.id))
def players_list(msg):
    players = get_top_players(10)
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    text = '🏆 ТОП-10 ИГРОКОВ\n\n'
    for i, (game_nick, balance, level) in enumerate(players, 1):
        admin_tag = ' 👑' if is_admin_by_nick(game_nick) else ''
        text += f'{i}. {game_nick} — {balance:,} монет (уровень {level}){admin_tag}\n'
    bot.send_message(msg.chat.id, text)
    log_admin_action(msg.from_user.id, 'Просмотр списка игроков')

# 3. Назначить админа
@bot.message_handler(func=lambda m: m.text == '👑 Назначить админа' and is_admin(m.from_user.id))
def promote_admin_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник игрока, которого хотите сделать админом:')
    bot.register_next_step_handler(msg, promote_admin_process)

def promote_admin_process(msg):
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, f'❌ Игрок {nick} не найден.')
        return
    update_user(user['id'], role='admin')
    bot.send_message(msg.chat.id, f'✅ {nick} теперь администратор! 👑')
    log_admin_action(msg.from_user.id, f'Назначил админа: {nick}')

# 4. Найти игрока
@bot.message_handler(func=lambda m: m.text == '🔍 Найти игрока' and is_admin(m.from_user.id))
def find_player_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник или ID игрока:')
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
        bot.send_message(msg.chat.id, f'❌ Игрок "{query}" не найден.')
        return
    text = f'''
📋 ИНФОРМАЦИЯ ОБ ИГРОКЕ

👤 Ник: {user['game_nick']}
🆔 ID: {user['id']}
💰 Баланс: {user['balance']} монет
📈 Уровень: {user['level']}
⭐ Опыт: {user['exp']}
👑 Роль: {user['role']}
🚫 Бан: {"Да" if user['is_banned'] else "Нет"}
📅 Регистрация: {user['reg_date']}
'''
    bot.send_message(msg.chat.id, text)
    log_admin_action(msg.from_user.id, f'Поиск игрока: {query}')

# 5. Изменить уровень
@bot.message_handler(func=lambda m: m.text == '📈 Изменить уровень' and is_admin(m.from_user.id))
def change_level_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник и новый уровень через пробел:\nПример: Алексей 5')
    bot.register_next_step_handler(msg, change_level_process)

def change_level_process(msg):
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: ник уровень')
            return
        nick = parts[0]
        new_level = int(parts[1])
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, f'❌ Игрок {nick} не найден.')
            return
        update_user(user['id'], level=new_level)
        bot.send_message(msg.chat.id, f'✅ Уровень {nick} изменён на {new_level}')
        log_admin_action(msg.from_user.id, f'Изменил уровень {nick} на {new_level}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Используйте: ник уровень')

# 6. Выдать монеты
@bot.message_handler(func=lambda m: m.text == '➕ Выдать монеты' and is_admin(m.from_user.id))
def give_coins_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник и сумму через пробел:\nПример: Алексей 100')
    bot.register_next_step_handler(msg, give_coins_process)

def give_coins_process(msg):
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: ник сумма')
            return
        nick = parts[0]
        amount = int(parts[1])
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, f'❌ Игрок {nick} не найден.')
            return
        update_user(user['id'], balance=user['balance'] + amount)
        bot.send_message(msg.chat.id, f'✅ {nick} получил {amount} монет.')
        log_admin_action(msg.from_user.id, f'Выдал {amount} монет игроку {nick}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Используйте: ник 100')

# 7. Забрать монеты
@bot.message_handler(func=lambda m: m.text == '➖ Забрать монеты' and is_admin(m.from_user.id))
def take_coins_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник и сумму для списания:\nПример: Алексей 50')
    bot.register_next_step_handler(msg, take_coins_process)

def take_coins_process(msg):
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат.')
            return
        nick = parts[0]
        amount = int(parts[1])
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, f'❌ Игрок {nick} не найден.')
            return
        new_balance = user['balance'] - amount
        if new_balance < 0:
            new_balance = 0
        update_user(user['id'], balance=new_balance)
        bot.send_message(msg.chat.id, f'✅ У {nick} списано {amount} монет. Баланс: {new_balance}')
        log_admin_action(msg.from_user.id, f'Списал {amount} монет у игрока {nick}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Используйте: ник 50')

# 8. Выдать опыт
@bot.message_handler(func=lambda m: m.text == '🎁 Выдать опыт' and is_admin(m.from_user.id))
def give_exp_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник и количество опыта через пробел:\nПример: Алексей 50')
    bot.register_next_step_handler(msg, give_exp_process)

def give_exp_process(msg):
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: ник опыт')
            return
        nick = parts[0]
        amount = int(parts[1])
        user = get_user_by_nick(nick)
        if not user:
            bot.send_message(msg.chat.id, f'❌ Игрок {nick} не найден.')
            return
        add_exp(user['id'], amount)
        bot.send_message(msg.chat.id, f'✅ {nick} получил {amount} опыта.')
        log_admin_action(msg.from_user.id, f'Выдал {amount} опыта игроку {nick}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Используйте: ник 50')

# 9. Бан/Разбан
@bot.message_handler(func=lambda m: m.text == '⏳ Бан/Разбан' and is_admin(m.from_user.id))
def ban_player_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник игрока для бана или разбана:')
    bot.register_next_step_handler(msg, ban_player_process)

def ban_player_process(msg):
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, f'❌ Игрок {nick} не найден.')
        return
    new_status = 0 if user['is_banned'] else 1
    status_text = 'забанен' if new_status == 1 else 'разбанен'
    update_user(user['id'], is_banned=new_status)
    bot.send_message(msg.chat.id, f'✅ {nick} {status_text}!')
    log_admin_action(msg.from_user.id, f'{status_text.capitalize()} игрок {nick}')

# 10. Сброс баланса
@bot.message_handler(func=lambda m: m.text == '🔄 Сброс баланса' and is_admin(m.from_user.id))
def reset_balance_all(msg):
    bot.send_message(msg.chat.id, '⚠️ ВНИМАНИЕ! Вы действительно хотите обнулить баланс ВСЕМ игрокам?\nНапишите ДА для подтверждения.')
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
        log_admin_action(msg.from_user.id, 'Сбросил баланс всем игрокам')
    else:
        bot.send_message(msg.chat.id, '❌ Операция отменена.')

# 11. Рассылка
@bot.message_handler(func=lambda m: m.text == '📢 Рассылка' and is_admin(m.from_user.id))
def broadcast_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите текст для рассылки:')
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
            bot.send_message(user[0], f'📢 Сообщение от админа:\n\n{text}')
            sent += 1
        except:
            pass
    bot.send_message(msg.chat.id, f'✅ Рассылка завершена. Отправлено {sent} пользователям.')
    log_admin_action(msg.from_user.id, f'Рассылка: "{text[:30]}..."')

# 12. Удалить аккаунт
@bot.message_handler(func=lambda m: m.text == '🗑️ Удалить аккаунт' and is_admin(m.from_user.id))
def delete_account_start(msg):
    bot.send_message(msg.chat.id, '⚠️ Введите ник игрока для ПОЛНОГО УДАЛЕНИЯ аккаунта:\n(Это действие необратимо!)')
    bot.register_next_step_handler(msg, delete_account_process)

def delete_account_process(msg):
    nick = msg.text.strip()
    user = get_user_by_nick(nick)
    if not user:
        bot.send_message(msg.chat.id, f'❌ Игрок {nick} не найден.')
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM users WHERE game_nick = %s', (nick,))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(msg.chat.id, f'🗑️ Аккаунт {nick} удалён.')
    log_admin_action(msg.from_user.id, f'Удалил аккаунт {nick}')

# 13. Логи админа
@bot.message_handler(func=lambda m: m.text == '📋 Логи админа' and is_admin(m.from_user.id))
def show_logs(msg):
    try:
        with open('admin_logs.txt', 'r') as f:
            logs = f.read().splitlines()
            last_logs = logs[-20:] if len(logs) > 20 else logs
            text = '📋 Последние 20 действий админа:\n\n' + '\n'.join(last_logs)
            bot.send_message(msg.chat.id, text)
    except:
        bot.send_message(msg.chat.id, '📭 Логов пока нет.')

# ===== ЗАПУСК =====
if __name__ == '__main__':
    import signal
    import sys
    
    def shutdown_handler(signum, frame):
        print('🛑 Завершаем работу...')
        bot.remove_webhook()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    print('✅ Бот запущен!')
    print('📁 База данных: PostgreSQL (Railway)')
    bot.remove_webhook()
    
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f'❌ Ошибка: {e}. Перезапуск через 5 секунд...')
            import time
            time.sleep(5)
