
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

# ===== БАЗА ДАННЫХ (С ПОДДЕРЖКОЙ VOLUME) =====
DB_PATH = os.getenv('DB_PATH', 'data/db.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    game_nick TEXT,
    balance INTEGER DEFAULT 0,
    reg_date TEXT,
    ref_code TEXT,
    ref_by INTEGER DEFAULT 0,
    ref_count INTEGER DEFAULT 0,
    ref_earned INTEGER DEFAULT 0
)''')
conn.commit()

cur.execute('SELECT id, game_nick FROM users WHERE game_nick IS NULL OR game_nick = ""')
old_users = cur.fetchall()
for user_id, _ in old_users:
    cur.execute('UPDATE users SET game_nick = ? WHERE id = ?', (f'user{user_id}', user_id))
conn.commit()

try:
    cur.execute('ALTER TABLE users ADD COLUMN ref_code TEXT')
except:
    pass
try:
    cur.execute('ALTER TABLE users ADD COLUMN ref_by INTEGER DEFAULT 0')
except:
    pass
try:
    cur.execute('ALTER TABLE users ADD COLUMN ref_count INTEGER DEFAULT 0')
except:
    pass
try:
    cur.execute('ALTER TABLE users ADD COLUMN ref_earned INTEGER DEFAULT 0')
except:
    pass
conn.commit()

# ===== КЛАВИАТУРЫ =====
keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
keyboard.add('👤 Профиль', '💰 Баланс')
keyboard.add('🔗 Рефералы', '📊 Топ игроков')

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
    
    if ' ' in game_nick:
        bot.send_message(msg.chat.id, '❌ Ник не должен содержать пробелов. Попробуй ещё:')
        bot.register_next_step_handler(msg, set_nick, ref_param)
        return
    
    cur.execute('SELECT id FROM users WHERE game_nick = ?', (game_nick,))
    if cur.fetchone():
        bot.send_message(msg.chat.id, '❌ Этот ник уже занят. Придумай другой:')
        bot.register_next_step_handler(msg, set_nick, ref_param)
        return
    
    user_id = msg.from_user.id
    ref_code = generate_ref_code()
    ref_by = 0
    
    if ref_param:
        cur.execute('SELECT id FROM users WHERE ref_code = ?', (ref_param,))
        ref_user = cur.fetchone()
        if ref_user:
            ref_by = ref_user[0]
            cur.execute('UPDATE users SET ref_count = ref_count + 1, balance = balance + 50 WHERE id = ?', (ref_by,))
            conn.commit()
            bot.send_message(ref_by, f'🎉 *Новый реферал!*\n{msg.from_user.username or "Без юза"} присоединился.\n💰 +50 монет.', parse_mode='Markdown')
    
    cur.execute('''INSERT INTO users (id, game_nick, balance, ref_code, ref_by, reg_date) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, game_nick, 0, ref_code, ref_by, datetime.now().strftime('%d.%m.%Y %H:%M')))
    conn.commit()
    
    ref_text = f'\n👤 Пригласил: @{game_nick}' if ref_by else ''
    text = f'''✅ *Добро пожаловать!*

📛 Твой игровой ник: {game_nick}
📌 Твой код: `{ref_code}`
🔗 Ссылка: `https://t.me/{bot.get_me().username}?start={ref_code}`
{ref_text}

💡 Приглашай друзей и получай 50 монет за каждого!'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown', reply_markup=keyboard)

# ===== ПРОФИЛЬ =====
@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(msg):
    user_id = msg.from_user.id
    cur.execute('SELECT game_nick, balance, reg_date FROM users WHERE id = ?', (user_id,))
    result = cur.fetchone()
    if not result:
        bot.send_message(msg.chat.id, '❌ Сначала зарегистрируйся: /start')
        return
    game_nick, balance, reg_date = result
    
    username = msg.from_user.username
    display_username = f'@{username}' if username else 'Нет юза'
    
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
        bot.send_message(msg.chat.id, '❌ Сначала зарегистрируйся: /start')
        return
    bot.send_message(msg.chat.id, f'💰 Твой баланс: {result[0]:,} монет')

# ===== РЕФЕРАЛЫ =====
@bot.message_handler(func=lambda m: m.text == '🔗 Рефералы')
def refs(msg):
    user_id = msg.from_user.id
    cur.execute('SELECT ref_code, ref_count, ref_earned FROM users WHERE id = ?', (user_id,))
    data = cur.fetchone()
    if not data:
        bot.send_message(msg.chat.id, '❌ Сначала зарегистрируйся: /start')
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
    cur.execute('SELECT game_nick, balance FROM users ORDER BY balance DESC LIMIT 10')
    players = cur.fetchall()
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    text = '🏆 *ТОП-10 ИГРОКОВ*\n\n'
    for i, (game_nick, balance) in enumerate(players, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        text += f'{medal} {game_nick} — {balance:,} монет\n'
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
    
    text = f'''
📊 *СТАТИСТИКА СЕРВЕРА*

👥 Всего игроков: {total_users}
💰 Общий баланс: {total_balance:,}
🏆 Макс. баланс: {max_balance:,}
📈 Средний баланс: {avg_balance}

📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}
'''
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👥 Список игроков' and is_admin(m.from_user.id))
def players_list(msg):
    cur.execute('SELECT game_nick, balance FROM users ORDER BY balance DESC LIMIT 10')
    players = cur.fetchall()
    if not players:
        bot.send_message(msg.chat.id, '📭 Нет игроков.')
        return
    text = '🏆 *ТОП-10 ИГРОКОВ*\n\n'
    for i, (game_nick, balance) in enumerate(players, 1):
        text += f'{i}. {game_nick} — {balance:,} монет\n'
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
    print('✅ Бот запущен!')
    bot.remove_webhook()
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f'❌ Ошибка: {e}. Перезапуск через 5 секунд...')
            import time
            time.sleep(5)