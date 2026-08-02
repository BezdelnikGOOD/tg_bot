import os
import sqlite3
import random
import string
from datetime import datetime
import telebot

# ===== КОНФИГ (ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ) =====
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("❌ Токен не найден! Добавьте переменную окружения TOKEN")

ADMIN_ID = int(os.getenv('ADMIN_ID', 6573154279))
bot = telebot.TeleBot(TOKEN)

# ===== БАЗА ДАННЫХ (СОХРАНЯЕТСЯ В VOLUME) =====
# Если Volume не подключён — создаётся в папке data автоматически
DB_PATH = os.getenv('DB_PATH', 'data/db.db')

# Создаём папку data, если её нет
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Подключаемся к базе
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

# ===== СОЗДАЁМ ТАБЛИЦУ, ЕСЛИ ЕЁ НЕТ =====
cur.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    game_nick TEXT,
    balance INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    reg_date TEXT,
    ref_code TEXT,
    ref_by INTEGER DEFAULT 0,
    ref_count INTEGER DEFAULT 0,
    ref_earned INTEGER DEFAULT 0,
    last_daily TEXT
)''')
conn.commit()

# Исправляем старые записи (если game_nick пустой)
cur.execute('SELECT id, game_nick FROM users WHERE game_nick IS NULL OR game_nick = ""')
old_users = cur.fetchall()
for user_id, _ in old_users:
    cur.execute('UPDATE users SET game_nick = ? WHERE id = ?', (f'user{user_id}', user_id))
conn.commit()

# Добавляем недостающие колонки (если их нет)
for col in ['ref_code', 'ref_by', 'ref_count', 'ref_earned', 'last_daily']:
    try:
        cur.execute(f'ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT 0')
        conn.commit()
    except:
        pass

# ===== КЛАВИАТУРЫ =====
keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
keyboard.add('👤 Профиль', '💰 Баланс')
keyboard.add('🔗 Рефералы', '📊 Топ игроков')
keyboard.add('🎁 Ежедневный бонус', '🎰 Играть')

admin_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
admin_keyboard.add('📊 Статистика', '👥 Список игроков')
admin_keyboard.add('➕ Выдать монеты', '➖ Забрать монеты')
admin_keyboard.add('📢 Рассылка', '⬅️ Назад')

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def generate_ref_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))

def is_admin(user_id):
    return user_id == ADMIN_ID

def add_exp(user_id, amount):
    cur.execute('SELECT exp, level FROM users WHERE id = ?', (user_id,))
    exp, level = cur.fetchone()
    new_exp = exp + amount
    level_up = False
    while new_exp >= level * 50:
        new_exp -= level * 50
        level += 1
        level_up = True
        cur.execute('UPDATE users SET balance = balance + 50 WHERE id = ?', (user_id,))
    cur.execute('UPDATE users SET exp = ?, level = ? WHERE id = ?', (new_exp, level, user_id))
    conn.commit()
    return level_up, level

def get_progress_bar(exp, level):
    needed = level * 50
    filled = min(exp, needed)
    percent = int((filled / needed) * 10) if needed > 0 else 0
    bar = '█' * percent + '░' * (10 - percent)
    return bar, filled, needed

# ===== РЕГИСТРАЦИЯ =====
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    cur.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    
    if cur.fetchone():
        bot.send_message(msg.chat.id, f'👋 Снова здесь, {msg.from_user.first_name or "Игрок"}!', reply_markup=keyboard)
        return
    
    ref_param = None
    if ' ' in msg.text:
        ref_param = msg.text.split()[1]
    
    bot.send_message(msg.chat.id, '✏️ Придумай свой игровой ник (без пробелов):')
    bot.register_next_step_handler(msg, set_nick, ref_param)

def set_nick(msg, ref_param=None):
    game_nick = msg.text.strip()
    user_id = msg.from_user.id
    
    if ' ' in game_nick:
        bot.send_message(msg.chat.id, '❌ Ник не должен содержать пробелов. Попробуй ещё:')
        bot.register_next_step_handler(msg, set_nick, ref_param)
        return
    
    cur.execute('SELECT id FROM users WHERE game_nick = ?', (game_nick,))
    if cur.fetchone():
        bot.send_message(msg.chat.id, '❌ Этот ник уже занят. Придумай другой:')
        bot.register_next_step_handler(msg, set_nick, ref_param)
        return
    
    ref_code = generate_ref_code()
    ref_by = 0
    
    if ref_param:
        cur.execute('SELECT id FROM users WHERE ref_code = ?', (ref_param,))
        ref_user = cur.fetchone()
        if ref_user:
            ref_by = ref_user[0]
            cur.execute('UPDATE users SET ref_count = ref_count + 1, balance = balance + 50 WHERE id = ?', (ref_by,))
            conn.commit()
            add_exp(ref_by, 10)
            bot.send_message(ref_by, f'🎉 *Новый реферал!*\n{msg.from_user.username or "Без юза"} присоединился.\n💰 +50 монет, +10 опыта.', parse_mode='Markdown')
    
    cur.execute('''INSERT INTO users (id, game_nick, balance, reg_date, ref_code, ref_by) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, game_nick, 0, datetime.now().strftime('%d.%m.%Y %H:%M'), ref_code, ref_by))
    conn.commit()
    
    # Проверяем, что пользователь сохранился
    cur.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    if not cur.fetchone():
        bot.send_message(msg.chat.id, '❌ Ошибка сохранения! Попробуй ещё раз /start')
        return
    
    ref_text = f'\n👤 Пригласил: @{game_nick}' if ref_by else ''
    text = f'''✅ *Добро пожаловать!*

📛 Твой игровой ник: {game_nick}
📌 Твой код: `{ref_code}`
🔗 Ссылка: `https://t.me/{bot.get_me().username}?start={ref_code}`
{ref_text}

💡 Приглашай друзей и получай 50 монет и 10 опыта за каждого!'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown', reply_markup=keyboard)

# ===== ПРОФИЛЬ =====
@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(msg):
    user_id = msg.from_user.id
    cur.execute('SELECT game_nick, balance, level, exp, reg_date FROM users WHERE id = ?', (user_id,))
    result = cur.fetchone()
    if not result:
        bot.send_message(msg.chat.id, '❌ Ты не зарегистрирован! Напиши /start')
        return
    game_nick, balance, level, exp, reg_date = result
    
    username = msg.from_user.username
    display_username = f'@{username}' if username else 'Нет юза'
    
    bar, filled, needed = get_progress_bar(exp, level)
    
    if balance >= 100000:
        status = '🌟 Легенда'
    elif balance >= 50000:
        status = '💵 Миллионер'
    elif balance >= 10000:
        status = '🏰 Барон'
    elif balance >= 5000:
        status = '🏦 Инвестор'
    elif balance >= 1000:
        status = '👑 Магнат'
    elif balance >= 500:
        status = '💎 Богач'
    elif balance >= 200:
        status = '💰 Середняк'
    elif balance >= 50:
        status = '🪙 Новичок'
    elif balance >= 1:
        status = '🕊️ Бедняга'
    else:
        status = '💀 Банкрот'
    
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
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ===== БАЛАНС =====
@bot.message_handler(func=lambda m: m.text == '💰 Баланс')
def balance(msg):
    user_id = msg.from_user.id
    cur.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
    result = cur.fetchone()
    if not result:
        bot.send_message(msg.chat.id, '❌ Ты не зарегистрирован! Напиши /start')
        return
    bot.send_message(msg.chat.id, f'💰 Твой баланс: {result[0]:,} монет')

# ===== ЕЖЕДНЕВНЫЙ БОНУС =====
@bot.message_handler(func=lambda m: m.text == '🎁 Ежедневный бонус')
def daily_bonus(msg):
    user_id = msg.from_user.id
    cur.execute('SELECT last_daily FROM users WHERE id = ?', (user_id,))
    result = cur.fetchone()
    if not result:
        bot.send_message(msg.chat.id, '❌ Ты не зарегистрирован! Напиши /start')
        return
    last = result[0]
    today = datetime.now().strftime('%Y-%m-%d')
    if last == today:
        bot.send_message(msg.chat.id, '❌ Ты уже забирал бонус сегодня! Возвращайся завтра.')
        return
    bonus = random.randint(10, 40)
    cur.execute('UPDATE users SET balance = balance + ?, last_daily = ? WHERE id = ?', (bonus, today, user_id))
    conn.commit()
    level_up, new_level = add_exp(user_id, 5)
    text = f'🎁 Ты получил {bonus} монет и 5 опыта!'
    if level_up:
        text += f'\n🎉 УРОВЕНЬ ПОВЫШЕН! Твой уровень: {new_level}'
    bot.send_message(msg.chat.id, text)

# ===== ИГРА (орёл/решка) =====
@bot.message_handler(func=lambda m: m.text == '🎰 Играть')
def game(msg):
    user_id = msg.from_user.id
    cur.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
    result = cur.fetchone()
    if not result:
        bot.send_message(msg.chat.id, '❌ Ты не зарегистрирован! Напиши /start')
        return
    balance = result[0]
    if balance < 10:
        bot.send_message(msg.chat.id, '❌ Не хватает 10 монет!')
        return
    cur.execute('UPDATE users SET balance = balance - 10 WHERE id = ?', (user_id,))
    win = random.choice([0, 1])
    if win:
        cur.execute('UPDATE users SET balance = balance + 25 WHERE id = ?', (user_id,))
        conn.commit()
        level_up, new_level = add_exp(user_id, 10)
        result_text = '🎉 Ты выиграл! +25 монет, +10 опыта'
        if level_up:
            result_text += f'\n🎉 УРОВЕНЬ ПОВЫШЕН! Твой уровень: {new_level}'
    else:
        conn.commit()
        level_up, new_level = add_exp(user_id, 2)
        result_text = '😢 Ты проиграл. -10 монет, +2 опыта'
        if level_up:
            result_text += f'\n🎉 УРОВЕНЬ ПОВЫШЕН! Твой уровень: {new_level}'
    
    cur.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
    new_balance = cur.fetchone()[0]
    result_text += f'\n💰 Баланс: {new_balance}'
    bot.send_message(msg.chat.id, result_text)

# ===== РЕФЕРАЛЫ =====
@bot.message_handler(func=lambda m: m.text == '🔗 Рефералы')
def refs(msg):
    user_id = msg.from_user.id
    cur.execute('SELECT ref_code, ref_count, ref_earned FROM users WHERE id = ?', (user_id,))
    data = cur.fetchone()
    if not data:
        bot.send_message(msg.chat.id, '❌ Ты не зарегистрирован! Напиши /start')
        return
    ref_code, ref_count, ref_earned = data
    username = bot.get_me().username
    
    if ref_count >= 50:
        status = '👑 Легендарный пригласитель'
    elif ref_count >= 25:
        status = '💎 Мастер рефералов'
    elif ref_count >= 10:
        status = '🏆 Опытный'
    elif ref_count >= 5:
        status = '⭐ Активный'
    elif ref_count >= 1:
        status = '🟢 Начинающий'
    else:
        status = '⚪ Нет рефералов'
    
    text = f'''
╔═══════════════════════════════════╗
║        ✦  🔗 РЕФЕРАЛЫ  ✦          ║
╠═══════════════════════════════════╣
║                                   ║
║   📌 Твой код: `{ref_code}`
║   🔗 Ссылка: `https://t.me/{username}?start={ref_code}`
║                                   ║
║   👥 Приглашено: {ref_count} чел.
║   💰 Заработано: {ref_earned} монет
║   📊 Статус: {status}
║                                   ║
╚═══════════════════════════════════╝
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ===== ТОП ИГРОКОВ =====
@bot.message_handler(func=lambda m: m.text == '📊 Топ игроков')
def top_players(msg):
    cur.execute('SELECT game_nick, balance, level FROM users ORDER BY balance DESC LIMIT 10')
    players = cur.fetchall()
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    text = '🏆 *ТОП-10 ПО БАЛАНСУ*\n\n'
    for i, (game_nick, balance, level) in enumerate(players, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        text += f'{medal} {game_nick} — {balance:,} монет (уровень {level})\n'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# ===== АДМИН-ПАНЕЛЬ =====
@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, '❌ Доступ запрещён.')
        return
    bot.send_message(msg.chat.id, '🔐 *Админ-панель*\nВыберите действие:', 
                     parse_mode='Markdown', reply_markup=admin_keyboard)

@bot.message_handler(func=lambda m: m.text == '⬅️ Назад' and is_admin(m.from_user.id))
def back_to_main(msg):
    bot.send_message(msg.chat.id, '🏠 Главное меню', reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text == '📊 Статистика' and is_admin(m.from_user.id))
def stats(msg):
    cur.execute('SELECT COUNT(*) FROM users')
    total_users = cur.fetchone()[0]
    cur.execute('SELECT SUM(balance) FROM users')
    total_balance = cur.fetchone()[0] or 0
    cur.execute('SELECT MAX(balance) FROM users')
    max_balance = cur.fetchone()[0] or 0
    cur.execute('SELECT AVG(balance) FROM users')
    avg_balance = round(cur.fetchone()[0] or 0, 1)
    cur.execute('SELECT AVG(level) FROM users')
    avg_level = round(cur.fetchone()[0] or 0, 1)
    
    text = f'''
📊 *СТАТИСТИКА СЕРВЕРА*

👥 Всего игроков: {total_users}
💰 Общий баланс: {total_balance:,}
🏆 Макс. баланс: {max_balance:,}
📈 Средний баланс: {avg_balance}
📈 Средний уровень: {avg_level}

📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👥 Список игроков' and is_admin(m.from_user.id))
def players_list(msg):
    cur.execute('SELECT game_nick, balance, level FROM users ORDER BY balance DESC LIMIT 10')
    players = cur.fetchall()
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    text = '🏆 *ТОП-10 ИГРОКОВ*\n\n'
    for i, (game_nick, balance, level) in enumerate(players, 1):
        text += f'{i}. {game_nick} — {balance:,} монет (уровень {level})\n'
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '➕ Выдать монеты' and is_admin(m.from_user.id))
def give_coins_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник и сумму через пробел:\nПример: `Алексей 100`', parse_mode='Markdown')
    bot.register_next_step_handler(msg, give_coins_process)

def give_coins_process(msg):
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат. Нужно: `ник сумма`')
            return
        game_nick = parts[0]
        amount = int(parts[1])
        cur.execute('SELECT id FROM users WHERE game_nick = ?', (game_nick,))
        if not cur.fetchone():
            bot.send_message(msg.chat.id, f'❌ Игрок {game_nick} не найден.')
            return
        cur.execute('UPDATE users SET balance = balance + ? WHERE game_nick = ?', (amount, game_nick))
        conn.commit()
        bot.send_message(msg.chat.id, f'✅ {game_nick} получил {amount} монет.')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка. Используйте: `ник 100`')

@bot.message_handler(func=lambda m: m.text == '➖ Забрать монеты' and is_admin(m.from_user.id))
def take_coins_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите ник и сумму для списания:\nПример: `Алексей 50`')
    bot.register_next_step_handler(msg, take_coins_process)

def take_coins_process(msg):
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            bot.send_message(msg.chat.id, '❌ Неверный формат.')
            return
        game_nick = parts[0]
        amount = int(parts[1])
        cur.execute('SELECT balance FROM users WHERE game_nick = ?', (game_nick,))
        user = cur.fetchone()
        if not user:
            bot.send_message(msg.chat.id, f'❌ Игрок {game_nick} не найден.')
            return
        new_balance = user[0] - amount
        if new_balance < 0:
            new_balance = 0
        cur.execute('UPDATE users SET balance = ? WHERE game_nick = ?', (new_balance, game_nick))
        conn.commit()
        bot.send_message(msg.chat.id, f'✅ У {game_nick} списано {amount} монет. Баланс: {new_balance}')
    except:
        bot.send_message(msg.chat.id, '❌ Ошибка.')

@bot.message_handler(func=lambda m: m.text == '📢 Рассылка' and is_admin(m.from_user.id))
def broadcast_start(msg):
    bot.send_message(msg.chat.id, '✏️ Введите текст для рассылки:')
    bot.register_next_step_handler(msg, broadcast_process)

def broadcast_process(msg):
    text = msg.text
    cur.execute('SELECT id FROM users')
    users = cur.fetchall()
    if not users:
        bot.send_message(msg.chat.id, '❌ Нет пользователей.')
        return
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f'📢 *Сообщение от админа:*\n\n{text}', parse_mode='Markdown')
            sent += 1
        except:
            pass
    bot.send_message(msg.chat.id, f'✅ Рассылка завершена. Отправлено {sent} пользователям.')

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
    print(f'📁 База данных: {DB_PATH}')
    bot.remove_webhook()
    
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f'❌ Ошибка: {e}. Перезапуск через 5 секунд...')
            import time
            time.sleep(5)
