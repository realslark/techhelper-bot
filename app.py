import telebot
from groq import Groq
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Ключи из Secrets Replit (безопасно)
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
GROQ_API_KEY = os.environ['GROQ_API_KEY']

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# Словарь для хранения истории чата по пользователям (для контекста LLM)
chat_histories = {}

# Приветственное сообщение (адаптировано под сотрудников и стиль Яндекс)
WELCOME_MESSAGE = (
    "Привет! Я TechHelper, твой ИИ-помощник по техпроблемам в компании на базе LLM. 🔧\n"
    "Я помогу сотрудникам быстро разобраться с любыми IT-задачами — от тормозящего ноута до глючной почты. "
    "Опиши проблему или выбери категорию ниже, и давай разберём по шагам! 😊 "
    "P.S. Ответы генерируются уникально, с учётом нашего чата — если не поможет, пиши в IT-отдел."
)

# Системный промпт для LLM (стиль Яндекс: дружелюбный, с эмодзи, юмором, шагами; фокус на сотрудниках)
SYSTEM_PROMPT = (
    "Ты — TechHelper, крутой ИИ-спец по техподдержке в компании, в стиле Яндекс (дружелюбный, разговорный, с эмодзи и юмором). "
    "Твоя цель: помогать сотрудникам с ЛЮБЫМИ техническими проблемами (ПК, софт, сеть, гаджеты, офисное оборудование). "
    "Анализируй описание, предлагай простые шаги (в списке), уточняй детали (модель, ОС, симптомы). "
    "Добавляй юмор или аналогии для 'Вау!'-эффекта, например: 'Это как кофе без кофеина — давай добавим энергии! 😅'. "
    "Будь empathetic, всегда задавай вопросы для уточнения. Генерируй уникально, без шаблонов. "
    "Держи ответы краткими (до 200 слов). Если проблема сложная, посоветуй обратиться в IT-отдел. "
    "Используй контекст чата для персонализации."
)

# Функция для создания клавиатуры с кнопками
def get_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row_width = 2
    keyboard.add(
        InlineKeyboardButton("ПК/Ноутбук", callback_data="category_pc"),
        InlineKeyboardButton("Софт/Приложения", callback_data="category_software"),
        InlineKeyboardButton("Сеть/Интернет", callback_data="category_network"),
        InlineKeyboardButton("Гаджеты/Девайсы", callback_data="category_gadgets"),
        InlineKeyboardButton("Другое (опиши)", callback_data="category_other")
    )
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, WELCOME_MESSAGE, reply_markup=get_keyboard())
    chat_histories[message.chat.id] = []  # Инициализируем историю

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    # Определяем сообщение на основе кнопки (добавляем в контекст)
    if call.data == "category_pc":
        user_input = "Проблема с ПК или ноутбуком. Уточни детали."
    elif call.data == "category_software":
        user_input = "Проблема с софтом или приложениями. Что именно глючит?"
    elif call.data == "category_network":
        user_input = "Проблема с сетью или интернетом. Расскажи симптомы."
    elif call.data == "category_gadgets":
        user_input = "Проблема с гаджетами (смартфон, принтер и т.д.). Опиши."
    elif call.data == "category_other":
        user_input = "Другая проблема. Расскажи подробнее."

    # Добавляем в историю как сообщение пользователя
    chat_histories[chat_id].append({"role": "user", "content": user_input})

    # Генерируем ответ через LLM
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_histories[chat_id][-10:]
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama3-70b-8192",
            temperature=0.7,
            max_tokens=300
        )
        bot_reply = response.choices[0].message.content.strip()

        # Добавляем в историю
        chat_histories[chat_id].append({"role": "assistant", "content": bot_reply})

        # Отправляем ответ с клавиатурой (если нужно продолжить)
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, bot_reply, reply_markup=get_keyboard())
    except Exception as e:
        bot.send_message(chat_id, "Ой, что-то пошло не так. Опиши проблему текстом? 😅")
        print(f"Error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    # Добавляем сообщение пользователя в историю
    chat_histories[chat_id].append({"role": "user", "content": message.text})

    # Формируем сообщения для LLM
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_histories[chat_id][-10:]

    # Запрос к LLM
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama3-70b-8192",
            temperature=0.7,
            max_tokens=300
        )
        bot_reply = response.choices[0].message.content.strip()

        # Добавляем в историю
        chat_histories[chat_id].append({"role": "assistant", "content": bot_reply})

        # Отправляем ответ с клавиатурой
        bot.reply_to(message, bot_reply, reply_markup=get_keyboard())
    except Exception as e:
        bot.reply_to(message, "Ой, что-то пошло не так. Опиши проблему еще раз? 😅")
        print(f"Error: {e}")

# Запуск бота
if __name__ == '__main__':
    bot.infinity_polling()
