import os
import asyncio
from aiohttp import web
from dotenv import load_dotenv
import openai
import aiohttp
from pydub import AudioSegment
from asyncio import Event

# Загрузка переменных окружения из .env файла
load_dotenv()

# Переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHAT_ID = os.getenv('CHAT_ID')  # Идентификатор чата на OpenAI
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Установка API-ключа OpenAI
openai.api_key = OPENAI_API_KEY

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

            if "voice" in data["message"]:
                file_id = data["message"]["voice"]["file_id"]
                file_path = await get_file_path(file_id)

                if file_path:
                    audio_content = await download_file(file_path)
                    transcript = await process_audio(audio_content)

                    if transcript:
                        response = await generate_openai_response(transcript)
                    else:
                        response = "Не удалось обработать голосовое сообщение."

                    await send_message(chat_id, response)

            elif "text" in data["message"]:
                user_message = data["message"]["text"]
                stop_event = Event()
                typing_task = asyncio.create_task(send_typing_action_while_processing(chat_id, stop_event))

                try:
                    response = await generate_openai_response(user_message)
                    await send_message(chat_id, response)
                finally:
                    stop_event.set()
                    await typing_task

        return web.json_response({"status": "ok"})
    except Exception as e:
        print(f"Ошибка обработки вебхука: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def get_file_path(file_id):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.json()
                print(f"Ответ Telegram API для getFile: {result}")
                return result['result']['file_path']
    except Exception as e:
        print(f"Ошибка при получении пути файла: {e}")
        return None

async def download_file(file_path):
    try:
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                return await response.read()
    except Exception as e:
        print(f"Ошибка при скачивании файла: {e}")
        return None

async def process_audio(audio_content):
    try:
        temp_file = "temp_audio.ogg"
        with open(temp_file, "wb") as f:
            f.write(audio_content)

        audio = AudioSegment.from_file(temp_file, format="ogg")
        wav_file = "temp_audio.wav"
        audio.export(wav_file, format="wav")

        transcript = "Голосовое сообщение успешно преобразовано."
        return transcript
    except Exception as e:
        print(f"Ошибка при обработке аудио: {e}")
        return None
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(wav_file):
            os.remove(wav_file)

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

async def send_typing_action_while_processing(chat_id, stop_event):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
        payload = {"chat_id": chat_id, "action": "typing"}
        async with aiohttp.ClientSession() as session:
            while not stop_event.is_set():
                async with session.post(url, json=payload) as response:
                    await asyncio.sleep(5)
    except Exception as e:
        print(f"Ошибка в send_typing_action_while_processing: {e}")

async def generate_openai_response(user_message):
    try:
        # Запрос к OpenAI для существующего чата
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"Chat ID: {CHAT_ID}"},  # Уточнение для логирования
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
