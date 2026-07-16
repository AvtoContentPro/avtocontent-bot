import telebot
import hashlib
import re
import json
import os
from telebot import types

# ================= НАСТРОЙКИ =================
BOT_TOKEN = '8963563380:AAFtz7s_m2F1sIy6PdHQPM2EoObyqH77eow'
ADMIN_ID = 882052180

# Реквизиты для оплаты
CARD_BYN = "9112 3880 5148 9123"  # Сбербанк РБ (BYN)
YOOMONEY = "410011672400844"  # ЮMoney (RUB)
USDT_TRC20 = "TVqWh48Kxok9tF3bRjdukyYe2MsCSwxjvX"  # Bybit TRC20

# Цены
PRICES = {
    'stockhunter': {
        'byn': '35 BYN',
        'rub': '990₽',
        'usdt': '12 USDT',
        'name': 'StockHunter Pro+'
    },
    'audiovoice': {
        'byn': '35 BYN',
        'rub': '990₽',
        'usdt': '12 USDT',
        'name': 'AudioVoicePro'
    },
    'package': {
        'byn': '60 BYN',
        'rub': '1690₽',
        'usdt': '20 USDT',
        'name': 'ПАКЕТ ОБЕИХ'
    }
}

# Секретные фразы (ДОЛЖНЫ СОВПАДАТЬ С main.js!)
SECRETS = {
    'stockhunter': 'OlgaStockHunter2026Secret',
    'audiovoice': 'OlgaAudioVoice2026Secret' 
}
# =============================================

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}
pending_orders = {}
DB_FILE = 'issued_keys.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_key(hwid, secret):
    clean_hwid = re.sub(r'[^a-zA-Z0-9]', '', hwid)
    hash_str = hashlib.sha256((clean_hwid + secret).encode('utf-8')).hexdigest()
    key = hash_str[:16].upper()
    return f"{key[0:4]}-{key[4:8]}-{key[8:12]}-{key[12:16]}"

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(" StockHunter Pro+"),
               types.KeyboardButton("🎤 AudioVoicePro"),
               types.KeyboardButton("🎁 ПАКЕТ ОБЕИХ"))
    
    bot.send_message(message.chat.id, 
        "👋 Привет! Я бот AvtoContentPro.\n\n"
        "Выберите программу для покупки:", 
        reply_markup=markup)
    user_states[message.chat.id] = 'choosing_product'

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'choosing_product')
def choose_product(message):
    text = message.text
    product_key = None
    
    if "StockHunter" in text: 
        product_key = 'stockhunter'
    elif "AudioVoice" in text: 
        product_key = 'audiovoice'
    elif "ПАКЕТ" in text: 
        product_key = 'package'
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите программу из меню.")
        return

    pending_orders[message.chat.id] = {'product': product_key}
    user_states[message.chat.id] = 'waiting_hwid'
    
    bot.send_message(message.chat.id, 
        f"✅ Вы выбрали: {PRICES[product_key]['name']}\n\n"
        "Теперь отправьте мне ваш HWID (уникальный код компьютера).\n"
        "Его можно скопировать в окне активации программы.",
        reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'waiting_hwid')
def get_hwid(message):
    hwid = message.text.strip()
    if len(hwid) < 10:
        bot.send_message(message.chat.id, "⚠️ HWID слишком короткий. Проверьте правильность.")
        return

    order = pending_orders[message.chat.id]
    order['hwid'] = hwid
    
    # Генерируем ключи
    keys = {}
    if order['product'] == 'package':
        keys['StockHunter Pro+'] = generate_key(hwid, SECRETS['stockhunter'])
        keys['AudioVoicePro'] = generate_key(hwid, SECRETS['audiovoice'])
    elif order['product'] == 'stockhunter':
        keys['StockHunter Pro+'] = generate_key(hwid, SECRETS['stockhunter'])
    elif order['product'] == 'audiovoice':
        keys['AudioVoicePro'] = generate_key(hwid, SECRETS['audiovoice'])
        
    order['keys'] = keys
    
    # Формируем сообщение с реквизитами
    payment_msg = (
        f"✅ <b>HWID принят!</b>\n\n"
        f"💳 <b>ВЫБЕРИТЕ СПОСОБ ОПЛАТЫ:</b>\n\n"
        
        f"<b>1️ Беларусь (BYN) — Сбербанк РБ:</b>\n"
        f"Карта: <code>{CARD_BYN}</code>\n"
        f"Сумма: <b>{PRICES[order['product']]['byn']}</b>\n\n"
        
        f"<b>2️⃣ Россия (RUB):</b>\n"
        f"Карта: <code>{CARD_BYN}</code>\n"
        f"ЮMoney: <code>{YOOMONEY}</code>\n"
        f"Сумма: <b>{PRICES[order['product']]['rub']}</b>\n\n"
        
        f"<b>3️⃣ USDT TRC20 (международная оплата):</b>\n"
        f"Кошелёк: <code>{USDT_TRC20}</code>\n"
        f"Сумма: <b>{PRICES[order['product']]['usdt']}</b>\n"
        f"⚠️ Комиссия сети: ~1 USDT (оплачиваете отдельно)\n\n"
        
        f"📸 <b>ПОСЛЕ ОПЛАТЫ:</b>\n"
        f"Отправьте скриншот или чек об оплате в ответ на это сообщение.\n"
        f"Я проверю и выдам ключи активации!"
    )
    
    bot.send_message(message.chat.id, payment_msg, parse_mode='HTML')
    
    # Отправляем уведомление админу
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"confirm_{message.chat.id}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_{message.chat.id}")
    )
    
    bot.send_message(ADMIN_ID, 
        f"🔔 <b>Новый заказ!</b>\n\n"
        f"👤 Пользователь: @{message.from_user.username} (ID: {message.chat.id})\n"
        f"📦 Товар: {PRICES[order['product']]['name']}\n"
        f"💰 Сумма: {PRICES[order['product']]['byn']} / {PRICES[order['product']]['rub']} / {PRICES[order['product']]['usdt']}\n"
        f"🔑 HWID: <code>{hwid}</code>",
        parse_mode='HTML', reply_markup=markup)
    
    user_states[message.chat.id] = 'waiting_payment'

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'waiting_payment')
def wait_payment(message):
    # Сохраняем скриншот/чек от пользователя
    bot.send_message(message.chat.id, "📸 Чек получен! Ожидайте подтверждения администратора...")
    
    # Пересылаем чек админу
    if message.photo:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    elif message.document:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    else:
        bot.send_message(ADMIN_ID, 
            f"📨 <b>Пользователь {message.from_user.first_name} отправил подтверждение:</b>\n"
            f"<code>{message.text}</code>",
            parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: True)
def admin_callback(call):
    chat_id = int(call.data.split('_')[1])
    
    if chat_id not in pending_orders:
        bot.answer_callback_query(call.id, "Заказ не найден.")
        return

    order = pending_orders[chat_id]
    
    if call.data.startswith('confirm_'):
        # Формируем текст с ключами
        keys_text = ""
        for prod, key in order['keys'].items():
            keys_text += f"🔹 {prod}: <code>{key}</code>\n"
        
        bot.send_message(chat_id, 
            f"✅ <b>Оплата подтверждена!</b>\n\n"
            f"<b>Ваши ключи активации:</b>\n"
            f"{keys_text}\n"
            f"⚠️ <b>Сохраните ключи!</b> Они привязаны к вашему HWID.\n"
            f"Вставьте ключ в программу и нажмите 'Активировать'.",
            parse_mode='HTML')
            
        # Сохраняем в базу
        db = load_db()
        db[str(chat_id)] = order
        save_db(db)
        
        bot.send_message(chat_id, "Спасибо за покупку! Приятного пользования 🎉")
        bot.answer_callback_query(call.id, "Ключи выданы!")
        
    elif call.data.startswith('cancel_'):
        bot.send_message(chat_id, "❌ Заказ отменен администратором.")
        bot.answer_callback_query(call.id, "Заказ отменен.")
        
    del pending_orders[chat_id]

print("✅ Бот AvtoContentPro запущен в облаке!")
bot.infinity_polling()