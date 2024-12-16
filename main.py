import os
import openai
import requests
import aiohttp
from aiohttp import web
from PIL import Image
from pydub import AudioSegment

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

openai.api_key = OPENAI_API_KEY

PROMPT = (
    "Этот GPT выступает в роли профессионального создателя контента для Телеграм-канала Ассоциации застройщиков. "
    "Он создает максимально продающие посты на темы недвижимости, строительства, законодательства, инвестиций и связанных отраслей. "
    "Контент ориентирован на привлечение внимания, удержание аудитории и стимулирование действий (например, обращения за консультацией или покупки). "
    "GPT учитывает деловой, но не формальный тон и стремится быть доступным, информативным и вовлекающим. "
    "Посты красиво оформляются с использованием эмодзи в стиле 'энергичный и современный', добавляя динамичности и вовлеченности. "
    "Например: 🏗️ для темы строительства, 🌟 для выделения преимуществ, 📲 для призывов к действию. "
    "Все посты структурированные и содержат четкие призывы к действию, информацию о контактах и гиперссылки. "
    "Если по запросу необходимо показать расчеты по квартирам, то жирным выделяются комнатность квартиры, площадь, стоимость и ежемесячный платеж по ипотечному кредиту. "
    "Эти данные всегда подаются структурировано и логично. "
    "GPT не фантазирует и создает контент исключительно на основе полученной информации. "
    "Если информации не хватает, он уточняет необходимые данные у отправителя. "
    "В конце каждого поста перед хэштегами указывается название компании 'Ассоциация застройщиков', номер телефона 8-800-550-23-93. "
    "В конце хэштеги на тему поста."
)

async def get_telegram_file_path(file_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data["result"]["file_path"]

async def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload)

async def send_typing_action(chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
    payload = {"chat_id": chat_id, "action": "typing"}
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload)

async def transcribe_audio(ogg_file_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(ogg_file_url) as resp:
            content = await resp.read()
            with open("temp_audio.ogg", "wb") as f:
                f.write(content)

    try:
        audio = AudioSegment.from_file("temp_audio.ogg", format="ogg")
        audio.export("temp_audio.wav", format="wav")
        with open("temp_audio.wav", "rb") as f:
            transcript = openai.Audio.transcribe("whisper-1", f)
        return transcript["text"]
    except Exception as e:
        print(f"Ошибка транскрипции аудио: {e}")
        return None

async def generate_openai_response(prompt):
    try:
        response = openai.Completion.create(
            engine="gpt-4",
            prompt=prompt,
            max_tokens=1500,
            temperature=1,
        )
        return response["choices"][0]["text"].strip()
    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        return "Произошла ошибка при обработке запроса."

async def handle_webhook(request):
    try:
        data = await request.json()
        print(f"Получены данные от Telegram: {data}")

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            username = data["message"]["from"]["username"]

            # Проверка на текстовое сообщение
            if "text" in data["message"]:
                user_message = data["message"]["text"]
                await send_typing_action(chat_id)

                # Добавление условий для разных пользователей
                if username == "di_agent01":
                    user_message += "\n\nНаписать в WhatsApp: wa.me/79281497703"
                elif username == "Alinalyusaya":
                    user_message += "\n\nНаписать в WhatsApp: wa.me/79281237003"
                elif username == "ElenaZelenskaya1":
                    user_message += "\n\nНаписать в WhatsApp: wa.me/79384242393"

                response = await generate_openai_response(PROMPT + "\n\n" + user_message)
                await send_message(chat_id, response)

            # Проверка на голосовое сообщение
            elif "voice" in data["message"]:
                file_id = data["message"]["voice"]["file_id"]
                file_path = await get_telegram_file_path(file_id)
                ogg_file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                text_from_audio = await transcribe_audio(ogg_file_url)
                await send_typing_action(chat_id)
                response = await generate_openai_response(PROMPT + "\n\n" + text_from_audio)
                await send_message(chat_id, response)

        return web.json_response({"status": "ok"})
    except Exception as e:
        print(f"Ошибка обработки вебхука: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def setup_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    payload = {"url": WEBHOOK_URL}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            print(f"Установлен вебхук: {await resp.text()}")

app = web.Application()
app.router.add_post("/webhook", handle_webhook)

if __name__ == "__main__":
    web.run_app(app, port=8080)
