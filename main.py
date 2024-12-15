import os
import asyncio
from aiohttp import web
from dotenv import load_dotenv
import openai
import aiohttp

# Загрузка переменных окружения из .env файла
load_dotenv()

# Переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Логи для отладки переменных окружения
print(f"TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN}")
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")
print(f"WEBHOOK_URL: {WEBHOOK_URL}")

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY or not WEBHOOK_URL:
    raise ValueError("Не удалось загрузить обязательные переменные окружения. Проверьте .env файл или настройки Render.")

# Установка API-ключа OpenAI
openai.api_key = OPENAI_API_KEY

# PROMT для OpenAI
PROMPT = (
    "Этот GPT выступает в роли профессионального создателя контента для Телеграм-канала Ассоциации застройщиков. "
    "Он создает максимально продающие посты на темы недвижимости, строительства, законодательства, инвестиций и связанных отраслей. "
    "Контент ориентирован на привлечение внимания, удержание аудитории и стимулирование действий (например, обращения за консультацией или покупки). "
    "GPT учитывает деловой, но не формальный тон и стремится быть доступным, информативным и вовлекающим. "
    "Посты красиво оформляются с использованием эмодзи в стиле \"энергичный и современный\", добавляя динамичности и вовлеченности. "
    "Например: 🌇 для темы строительства, 🌟 для выделения преимуществ, 📲 для призывов к действию. "
    "Все посты содержат четкие призывы к действию и информацию о контактах. "
    "В конце каждого поста указывается номер телефона Ассоциации застройщиков: 8-800-550-23-93 и название компании \"Ассоциация застройщиков\", "
    "которое также является гиперссылкой, ведущей на Телеграм-канал https://t.me/associationdevelopers."
)

# Создание приложения Aiohttp
app = web.Application()

async def handle_home(request):
    return web.Response(text="Сервис работает!")

async def handle_webhook(request):
    try:
        data = await request.json()
        print(f"Получены данные от Telegram: {data}")  # Отладочный лог

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_message = data["message"].get("text", "")
            print(f"Chat ID: {chat_id}, Message: {user_message}")

            if user_message.lower() in ["привет", "здравствуйте", "начать"]:
                welcome_message = (
                    "Привет, я НЕАЛЕКСЕЙ! Я ОТЛИЧНЫЙ КОНТЕНТ МЕНЕДЖЕР. "
                    "Я создам для тебя уникальные посты в Телеграм, только напиши или скажи мне информацию, которую тебе необходимо переработать для поста."
                )
                await send_message(chat_id, welcome_message)
                return web.json_response({"status": "ok"})

            # Генерация ответа через OpenAI
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=1,
                max_tokens=1500,
            )

            reply = response['choices'][0]['message']['content']
            await send_message(chat_id, reply)

        return web.json_response({"status": "ok"})

    except Exception as e:
        print(f"Ошибка обработки вебхука: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                print(f"Ответ Telegram API: {result}")
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

# Роуты приложения
app.router.add_get('/', handle_home)
app.router.add_post('/webhook', handle_webhook)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)