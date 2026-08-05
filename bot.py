import os
import random
import time
from datetime import datetime
import telebot
import psycopg2
import psycopg2.extras
from zoneinfo import ZoneInfo

# ===== КОНФИГ =====
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("❌ Токен не найден!")

ADMIN_ID = int(os.getenv('ADMIN_ID', 6573154279))
bot = telebot.TeleBot(TOKEN)

# ===== ЧАСОВОЙ ПОЯС ЕКБ =====
TIMEZONE = ZoneInfo('Asia/Yekaterinburg')

def get_current_time():
    return datetime.now(TIMEZONE)

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
            name TEXT UNIQUE,
            trophies INTEGER DEFAULT 0,
            reg_date TEXT,
            is_logged_in INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()
    print('✅ База данных готова')

init_db()

# ============================================================
# ФУНКЦИИ БД
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
        conn.close()

def get_user_by_name(name):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM users WHERE name = %s', (name,))
        user = cur.fetchone()
        cur.close()
        return user
    finally:
        conn.close()

def create_user(user_id, name):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO users (id, name, reg_date, is_logged_in)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, name, get_current_time().strftime('%d.%m.%Y %H:%M'), 1))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f'❌ Ошибка создания: {e}')
        return False
    finally:
        conn.close()

def update_user(user_id, **kwargs):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        for key, value in kwargs.items():
            cur.execute(f'UPDATE users SET {key} = %s WHERE id = %s', (value, user_id))
        conn.commit()
        cur.close()
    finally:
        conn.close()

def is_logged_in(user_id):
    user = get_user(user_id)
    return user and user['is_logged_in'] == 1

def user_exists(user_id):
    return get_user(user_id) is not None

def is_admin(user_id):
    return user_id == ADMIN_ID

# ============================================================
# КЛАВИАТУРЫ
# ============================================================

auth_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
auth_keyboard.add('🔑 Войти', '📝 Регистрация')

main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_keyboard.add('👤 Профиль', '🏆 Трофеи')
main_keyboard.add('🎰 Слоты', '👑 Панель создателя')
main_keyboard.add('🚪 Выйти')

# ============================================================
# РЕГИСТРАЦИЯ
# ============================================================

@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    
    if user_exists(user_id):
        if is_logged_in(user_id):
            user = get_user(user_id)
            bot.send_message(msg.chat.id, f'👋 Снова здесь, {user["name"]}!', reply_markup=main_keyboard)
        else:
            bot.send_message(msg.chat.id, '🔐 Вы не авторизованы. Войдите или зарегистрируйтесь.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '👋 Добро пожаловать! Зарегистрируйтесь или войдите.', reply_markup=auth_keyboard)

@bot.message_handler(func=lambda m: m.text == '📝 Регистрация')
def register_start(msg):
    user_id = msg.from_user.id
    
    if user_exists(user_id):
        bot.send_message(msg.chat.id, '❌ У вас уже есть аккаунт! Войдите через "Войти".')
        return
    
    bot.send_message(msg.chat.id, '📝 Придумайте имя (от 3 до 15 символов, без пробелов):')
    bot.register_next_step_handler(msg, process_register)

def process_register(msg):
    user_id = msg.from_user.id
    name = msg.text.strip()
    
    if len(name) < 3 or len(name) > 15:
        bot.send_message(msg.chat.id, '❌ Имя должно быть от 3 до 15 символов. Попробуйте ещё:')
        bot.register_next_step_handler(msg, process_register)
        return
    
    if ' ' in name:
        bot.send_message(msg.chat.id, '❌ Имя не должно содержать пробелов. Попробуйте ещё:')
        bot.register_next_step_handler(msg, process_register)
        return
    
    if get_user_by_name(name):
        bot.send_message(msg.chat.id, f'❌ Имя "{name}" уже занято. Придумайте другое:')
        bot.register_next_step_handler(msg, process_register)
        return
    
    if create_user(user_id, name):
        bot.send_message(msg.chat.id, f'✅ Добро пожаловать, {name}! Вы зарегистрированы.', reply_markup=main_keyboard)
    else:
        bot.send_message(msg.chat.id, '❌ Ошибка регистрации. Попробуйте позже.')

# ============================================================
# АВТОРИЗАЦИЯ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🔑 Войти')
def login_start(msg):
    user_id = msg.from_user.id
    
    if not user_exists(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не зарегистрированы. Нажмите "Регистрация".')
        return
    
    if is_logged_in(user_id):
        bot.send_message(msg.chat.id, '✅ Вы уже авторизованы!', reply_markup=main_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🔐 Введите ваше имя:')
    bot.register_next_step_handler(msg, process_login)

def process_login(msg):
    user_id = msg.from_user.id
    name = msg.text.strip()
    
    user = get_user_by_name(name)
    if not user:
        bot.send_message(msg.chat.id, '❌ Пользователь с таким именем не найден.')
        return
    
    if user['id'] != user_id:
        bot.send_message(msg.chat.id, '❌ Это имя принадлежит другому игроку.')
        return
    
    update_user(user_id, is_logged_in=1)
    bot.send_message(msg.chat.id, f'✅ Добро пожаловать, {name}!', reply_markup=main_keyboard)

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
    
    user = get_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    text = f'''
╔═══════════════════════════════════╗
║          ✦  👤 ПРОФИЛЬ  ✦          ║
╠═══════════════════════════════════╣
║                                   ║
║   📛 Имя: {user['name']}
║   🏆 Трофеи: {user['trophies']}
║   📅 В игре с: {user['reg_date']}
║                                   ║
╚═══════════════════════════════════╝
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ============================================================
# ТРОФЕИ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🏆 Трофеи')
def trophies(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    user = get_user(user_id)
    if not user:
        bot.send_message(msg.chat.id, '❌ Ошибка. Попробуйте /start')
        return
    
    text = f'''
🏆 **ТВОИ ТРОФЕИ**

Имя: {user['name']}
Трофеи: {user['trophies']}

🎯 Продолжай играть в слоты, чтобы зарабатывать трофеи!
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ============================================================
# ИГРЫ — СЛОТЫ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '🎰 Слоты')
def slots(msg):
    user_id = msg.from_user.id
    
    if not is_logged_in(user_id):
        bot.send_message(msg.chat.id, '❌ Вы не авторизованы.', reply_markup=auth_keyboard)
        return
    
    bot.send_message(msg.chat.id, '🎰 **СЛОТЫ**\n\nВведите ставку (от 10 до 100 монет):')
    bot.register_next_step_handler(msg, process_slots)

def process_slots(msg):
    user_id = msg.from_user.id
    
    try:
        bet = int(msg.text.strip())
        if bet < 10 or bet > 100:
            bot.send_message(msg.chat.id, '❌ Ставка от 10 до 100 монет.')
            return
    except:
        bot.send_message(msg.chat.id, '❌ Введите число.')
        return
    
    symbols = ['🍒', '🍋', '🍊', '💎', '7️⃣']
    result = [random.choice(symbols) for _ in range(3)]
    
    msg1 = bot.send_message(msg.chat.id, '🎰 Крутим...')
    time.sleep(1)
    bot.edit_message_text(f'🎰 {result[0]} ❓ ❓', msg.chat.id, msg1.message_id)
    time.sleep(0.5)
    bot.edit_message_text(f'🎰 {result[0]} {result[1]} ❓', msg.chat.id, msg1.message_id)
    time.sleep(0.5)
    bot.edit_message_text(f'🎰 {result[0]} {result[1]} {result[2]}', msg.chat.id, msg1.message_id)
    
    win = 0
    if result[0] == result[1] == result[2]:
        if result[0] == '7️⃣':
            win = bet * 50
        elif result[0] == '💎':
            win = bet * 20
        else:
            win = bet * 10
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        win = bet * 2
    
    user = get_user(user_id)
    
    if win > 0:
        trophies_gain = 10
        update_user(user_id, trophies=user['trophies'] + trophies_gain)
        text = f'🎉 **ВЫИГРЫШ!**\n{result[0]} {result[1]} {result[2]}\n💰 +{win} монет\n🏆 +{trophies_gain} трофеев'
    else:
        trophies_loss = -5
        new_trophies = max(0, user['trophies'] + trophies_loss)
        update_user(user_id, trophies=new_trophies)
        text = f'😢 **ПРОИГРЫШ**\n{result[0]} {result[1]} {result[2]}\n💰 -{bet} монет\n🏆 {trophies_loss} трофеев'
    
    bot.edit_message_text(text, msg.chat.id, msg1.message_id)

# ============================================================
# ПАНЕЛЬ СОЗДАТЕЛЯ
# ============================================================

@bot.message_handler(func=lambda m: m.text == '👑 Панель создателя')
def creator_panel(msg):
    user_id = msg.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(msg.chat.id, '❌ Доступ запрещён.')
        return
    
    text = '''
👑 **ПАНЕЛЬ СОЗДАТЕЛЯ**

Выберите действие:

1️⃣ ✏️ Изменить ник
2️⃣ 🏆 Изменить трофеи

Введите номер:
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_creator_choice)

def process_creator_choice(msg):
    user_id = msg.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(msg.chat.id, '❌ Доступ запрещён.')
        return
    
    try:
        choice = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, '❌ Введите 1 или 2.')
        return
    
    if choice == 1:
        bot.send_message(msg.chat.id, '✏️ **ИЗМЕНИТЬ НИК**\n\nВведите: старый_ник новый_ник\nПример: Алексей Алекс', parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_change_nick)
    elif choice == 2:
        bot.send_message(msg.chat.id, '🏆 **ИЗМЕНИТЬ ТРОФЕИ**\n\nВведите: имя количество\nПример: Алексей +50', parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_change_trophies)
    else:
        bot.send_message(msg.chat.id, '❌ Введите 1 или 2.')

# ============================================================
# ИЗМЕНИТЬ НИК
# ============================================================

def process_change_nick(msg):
    user_id = msg.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(msg.chat.id, '❌ Доступ запрещён.')
        return
    
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: старый_ник новый_ник')
            return
        
        old_name = parts[0]
        new_name = parts[1]
        
        user = get_user_by_name(old_name)
        if not user:
            bot.send_message(msg.chat.id, f'❌ Игрок "{old_name}" не найден.')
            return
        
        if get_user_by_name(new_name):
            bot.send_message(msg.chat.id, f'❌ Имя "{new_name}" уже занято.')
            return
        
        update_user(user['id'], name=new_name)
        bot.send_message(msg.chat.id, f'✅ Имя "{old_name}" изменено на "{new_name}"!')
        bot.send_message(user['id'], f'✏️ Ваше имя изменено с "{old_name}" на "{new_name}" создателем!')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка: {e}')

# ============================================================
# ИЗМЕНИТЬ ТРОФЕИ
# ============================================================

def process_change_trophies(msg):
    user_id = msg.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(msg.chat.id, '❌ Доступ запрещён.')
        return
    
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: имя количество')
            return
        
        name = parts[0]
        amount = int(parts[1])
        
        user = get_user_by_name(name)
        if not user:
            bot.send_message(msg.chat.id, f'❌ Игрок "{name}" не найден.')
            return
        
        new_trophies = max(0, user['trophies'] + amount)
        update_user(user['id'], trophies=new_trophies)
        
        text = f'✅ Трофеи "{name}" изменены: {user["trophies"]} → {new_trophies}'
        if amount > 0:
            text += f' (+{amount})'
        else:
            text += f' ({amount})'
        
        bot.send_message(msg.chat.id, text)
        bot.send_message(user['id'], f'🏆 Ваши трофеи изменены создателем: {new_trophies}')
        
    except Exception as e:
        bot.send_message(msg.chat.id, f'❌ Ошибка: {e}')

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == '__main__':
    print('✅ Бот запущен!')
    print(f'🕐 Часовой пояс: Екатеринбург (UTC+5)')
    print(f'👑 Создатель: {ADMIN_ID}')
    bot.remove_webhook()
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f'❌ Ошибка: {e}. Перезапуск через 5 секунд...')
            time.sleep(5)