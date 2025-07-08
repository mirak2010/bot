import os
import re
import random
import requests

from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# Load environment variables
# Change this path if your .env file is not in the same folder as this script
load_dotenv()  # or load_dotenv(dotenv_path="/absolute/path/to/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
POSTER_TOKEN = os.getenv("POSTER_TOKEN")
POSTER_DOMAIN = "coffee-n-1.joinposter.com"

# Debug print to verify .env loading
print("BOT_TOKEN:", BOT_TOKEN)
print("POSTER_TOKEN:", POSTER_TOKEN)

# Check for required tokens
if not BOT_TOKEN or not POSTER_TOKEN:
    raise Exception("❌ BOT_TOKEN or POSTER_TOKEN not set in .env file or environment.")

# States
LANG, MENU, NAME, SURNAME, PHONE, VERIFY_CODE, GENDER, SIGN_PHONE, SIGN_VERIFY = range(9)

user_lang = {}
verification_data = {}

# Language texts
def get_text(key, lang):
    texts = {
        'welcome': {'uz': "🇺🇿 Coffee Way sodiqlik dasturiga xush kelibsiz!", 'ru': "🇷🇺 Добро пожаловать в программу лояльности Coffee Way!"},
        'menu': {'uz': "👇 Tanlang:", 'ru': "👇 Выберите опцию:"},
        'ask_name': {'uz': "👤 Ismingizni kiriting:", 'ru': "👤 Введите ваше имя:"},
        'ask_surname': {'uz': "👥 Familiyangizni kiriting:", 'ru': "👥 Введите вашу фамилию:"},
        'ask_phone': {'uz': "📞 Telefon raqamingizni +998 bilan kiriting:", 'ru': "📞 Введите ваш номер телефона начиная с +998:"},
        'invalid_phone': {'uz': "❌ Telefon raqami noto‘g‘ri. +998 bilan kiriting.", 'ru': "❌ Неверный номер. Начните с +998."},
        'duplicate_phone': {'uz': "❌ Bu raqam allaqachon ro'yxatdan o'tgan.", 'ru': "❌ Этот номер уже зарегистрирован."},
        'sent_code': {'uz': "✅ Tasdiqlash kodi: {}. Iltimos, kiriting.", 'ru': "✅ Код подтверждения: {}. Пожалуйста, введите его."},
        'wrong_code': {'uz': "❌ Kod noto‘g‘ri. Qolgan urinishlar: {}", 'ru': "❌ Неверный код. Осталось попыток: {}"},
        'too_many_attempts': {'uz': "❌ 3 marta noto‘g‘ri urinish. Qaytadan urinib ko‘ring.", 'ru': "❌ 3 неверные попытки. Попробуйте снова."},
        'ask_gender': {'uz': "🚻 Jinsingizni tanlang:", 'ru': "🚻 Выберите ваш пол:"},
        'thanks': {'uz': "🎉 Ro‘yxatdan o‘tganingiz uchun rahmat!", 'ru': "🎉 Спасибо за регистрацию!"},
        'not_registered': {'uz': "❌ Siz ro'yxatdan o'tmagansiz.", 'ru': "❌ Вы не зарегистрированы."},
        'bonus_balance': {'uz': "💰 Bonus balans: {} so'm", 'ru': "💰 Бонусный баланс: {} сум"}
    }
    return texts[key][lang]

gender_options = {'uz': ['Erkak', 'Ayol'], 'ru': ['Мужчина', 'Женщина']}

# --- Conversation handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇺🇿 O'zbek"], ["🇷🇺 Русский"]]
    await update.message.reply_text("🇺🇿 Iltimos, tilni tanlang:\n🇷🇺 Пожалуйста, выберите язык:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True))
    return LANG

async def select_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    if text == "🇺🇿 O'zbek":
        user_lang[user_id] = 'uz'
    elif text == "🇷🇺 Русский":
        user_lang[user_id] = 'ru'
    else:
        return LANG

    lang = user_lang[user_id]
    keyboard = [["💳 Ro'yxatdan o'tish" if lang == 'uz' else "💳 Регистрация"],
                ["🔑 Kirish" if lang == 'uz' else "🔑 Войти"]]
    await update.message.reply_text(get_text('welcome', lang))
    await update.message.reply_text(get_text('menu', lang), reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return MENU

async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang[update.effective_user.id]
    text = update.message.text
    if text in ["💳 Ro'yxatdan o'tish", "💳 Регистрация"]:
        await update.message.reply_text(get_text('ask_name', lang), reply_markup=ReplyKeyboardRemove())
        return NAME
    elif text in ["🔑 Kirish", "🔑 Войти"]:
        await update.message.reply_text(get_text('ask_phone', lang), reply_markup=ReplyKeyboardRemove())
        return SIGN_PHONE
    return MENU

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    lang = user_lang[update.effective_user.id]
    await update.message.reply_text(get_text('ask_surname', lang))
    return SURNAME

async def get_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['surname'] = update.message.text
    lang = user_lang[update.effective_user.id]
    await update.message.reply_text(get_text('ask_phone', lang))
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    lang = user_lang[update.effective_user.id]
    if not re.match(r'^\+998\d{9}$', phone):
        await update.message.reply_text(get_text('invalid_phone', lang))
        return PHONE

    cleaned_phone = phone.replace('+', '').replace(' ', '')
    url = f"https://{POSTER_DOMAIN}/api/clients.getClients?token={POSTER_TOKEN}&phone={cleaned_phone}"
    response = requests.get(url).json()
    if "response" in response and response['response']:
        await update.message.reply_text(get_text('duplicate_phone', lang))
        return PHONE

    context.user_data['phone'] = phone
    code = str(random.randint(100000, 999999))
    verification_data[update.effective_user.id] = {'code': code, 'attempts': 0}
    await update.message.reply_text(get_text('sent_code', lang).format(code))
    return VERIFY_CODE

async def verify_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang[user_id]
    entered = update.message.text.strip()
    data = verification_data.get(user_id)
    if not data:
        return ConversationHandler.END

    if entered == data['code']:
        del verification_data[user_id]
        buttons = [[KeyboardButton(g)] for g in gender_options[lang]]
        await update.message.reply_text(get_text('ask_gender', lang),
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True))
        return GENDER
    else:
        data['attempts'] += 1
        if data['attempts'] >= 3:
            del verification_data[user_id]
            await update.message.reply_text(get_text('too_many_attempts', lang))
            return ConversationHandler.END
        else:
            await update.message.reply_text(get_text('wrong_code', lang).format(3 - data['attempts']))
            return VERIFY_CODE

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.strip()
    lang = user_lang[update.effective_user.id]
    if gender not in gender_options[lang]:
        await update.message.reply_text(get_text('ask_gender', lang))
        return GENDER

    client_sex = '1' if gender in ['Erkak', 'Мужчина'] else '2'
    phone = context.user_data['phone'].replace('+', '').replace(' ', '')

    payload = {
        'client_name': context.user_data['name'],
        'client_surname': context.user_data['surname'],
        'phone': phone,
        'client_sex': client_sex,
        'client_groups_id_client': '2',
        'loyalty_type': '1'
    }
    url = f"https://{POSTER_DOMAIN}/api/clients.createClient?token={POSTER_TOKEN}"
    response = requests.post(url, data=payload).json()

    if "response" in response:
        await update.message.reply_text(get_text('thanks', lang))
        await show_balance(update, lang, phone)
    else:
        await update.message.reply_text("❌ Ro'yxatdan o'tishda xatolik.")
    return ConversationHandler.END

async def sign_in_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    lang = user_lang[update.effective_user.id]
    if not re.match(r'^\+998\d{9}$', phone):
        await update.message.reply_text(get_text('invalid_phone', lang))
        return SIGN_PHONE

    cleaned_phone = phone.replace('+', '').replace(' ', '')
    code = str(random.randint(100000, 999999))
    verification_data[update.effective_user.id] = {'code': code, 'attempts': 0, 'phone': cleaned_phone}
    await update.message.reply_text(get_text('sent_code', lang).format(code))
    return SIGN_VERIFY

async def sign_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang[user_id]
    entered = update.message.text.strip()
    data = verification_data.get(user_id)
    if not data:
        return ConversationHandler.END

    if entered == data['code']:
        cleaned_phone = data['phone']
        await show_balance(update, lang, cleaned_phone)
        del verification_data[user_id]
        return ConversationHandler.END
    else:
        data['attempts'] += 1
        if data['attempts'] >= 3:
            del verification_data[user_id]
            await update.message.reply_text(get_text('too_many_attempts', lang))
            return ConversationHandler.END
        else:
            await update.message.reply_text(get_text('wrong_code', lang).format(3 - data['attempts']))
            return SIGN_VERIFY

async def show_balance(update: Update, lang, cleaned_phone):
    url = f"https://{POSTER_DOMAIN}/api/clients.getClients?token={POSTER_TOKEN}&phone={cleaned_phone}"
    response = requests.get(url).json()
    if "response" in response and response['response']:
        client = response['response'][0]
        bonus = int(client.get('bonus', '0')) // 100
        await update.message.reply_text(get_text('bonus_balance', lang).format(bonus),
                                        reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True))
    else:
        await update.message.reply_text(get_text('not_registered', lang))

# --- Main Bot Execution ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_lang)],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_choice)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_surname)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            VERIFY_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_code)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            SIGN_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sign_in_phone)],
            SIGN_VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sign_verify)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == '__main__':
    main()
