import os
import asyncio
from aiohttp import web
from dotenv import load_dotenv
import openai
import aiohttp
from pydub import AudioSegment

# Загрузка переменных окружения из .env файла
load_dotenv()

# Переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Установка API-ключа OpenAI
openai.api_key = OPENAI_API_KEY

# PROMT для OpenAI
PROMPT = (
    "Этот GPT выступает в роли профессионального создателя контента для Телеграм-канала Ассоциации застройщиков. "
    "Он создает максимально продающие посты на темы недвижимости, строительства, законодательства, инвестиций и связанных отраслей. "
)

# Создание приложения Aiohttp
app = web.Application()

async def handle_home(request):
    return web.Response(text="Сервис работает!")

async def handle_webhook(request):
    try:
        data = await request.json()
        print(f"Получены данные от Telegram: {data}")

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]

            # Проверка на текстовое сообщение
            if "text" in data["message"]:
                user_message = data["message"]["text"]
                await send_typing_action(chat_id)  # Отправка статуса "печатает"
                if user_message.lower() in ["привет", "здравствуйте", "начать"]:
                    welcome_message = (
                        "Привет! Отправь текстовое сообщение или голосовое, чтобы я помог создать уникальный контент."
                    )
                    await send_message(chat_id, welcome_message)
                else:
                    response = await generate_openai_response(user_message)
                    await send_message(chat_id, response)
            
            # Проверка на голосовое сообщение
            elif "voice" in data["message"]:
                file_id = data["message"]["voice"]["file_id"]
                file_path = await get_telegram_file_path(file_id)
                ogg_file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                text_from_audio = await transcribe_audio(ogg_file_url)
                await send_typing_action(chat_id)  # Отправка статуса "печатает"
                response = await generate_openai_response(text_from_audio)
                await send_message(chat_id, response)

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

async def send_typing_action(chat_id):
    """Отправка статуса 'печатает'."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
        payload = {"chat_id": chat_id, "action": "typing"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                print(f"Отправлен статус 'печатает': {response.status}")
    except Exception as e:
        print(f"Ошибка при отправке статуса 'печатает': {e}")

async def get_telegram_file_path(file_id):
    """Получение пути файла по file_id."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
        payload = {"file_id": file_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=payload) as response:
                result = await response.json()
                return result["result"]["file_path"]
    except Exception as e:
        print(f"Ошибка получения пути файла: {e}")
        return None

async def transcribe_audio(ogg_url):
    """Транскрипция голосового сообщения."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ogg_url) as response:
                ogg_data = await response.read()

        # Конвертация OGG в WAV
        with open("audio.ogg", "wb") as ogg_file:
            ogg_file.write(ogg_data)
        audio = AudioSegment.from_file("audio.ogg", format="ogg")
        audio.export("audio.wav", format="wav")

        # Отправка в OpenAI для транскрипции
        with open("audio.wav", "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]
    except Exception as e:
        print(f"Ошибка при транскрипции: {e}")
        return "Не удалось обработать голосовое сообщение."

async def generate_openai_response(user_message):
    """Генерация ответа через OpenAI."""
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=1,
            max_tokens=1500,
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Ошибка при обращении к OpenAI: {e}")
        return "Произошла ошибка при генерации ответа."

# Роуты приложения
app.router.add_get('/', handle_home)
app.router.add_post('/webhook', handle_webhook)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
