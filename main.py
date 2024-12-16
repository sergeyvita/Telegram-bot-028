import os
import asyncio
from aiohttp import web
from dotenv import load_dotenv
import openai
import aiohttp
from pydub import AudioSegment
from PIL import Image
import pytesseract

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
    "Ты создаешь продающие посты для Telegram, посвященные продаже квартир в новостройках города Краснодара и Краснодарского края от агентства недвижимости 'Ассоциация застройщиков'. "
    "Каждый пост должен быть ярким, динамичным, структурированным, с акцентом на ключевые моменты. "
    "Используй эмодзи для привлечения внимания, выделяй важное жирным шрифтом. "
    "Если включаешь расчеты (например, стоимость квартиры, процентная ставка по ипотеке, ежемесячный платеж), выводи данные в формате, где каждая цифра находится на отдельной строке для удобства. "
    "Если речь идет об ипотеке, квартирах в новостройках или жилых комплексах, в самом конце поста добавляй призыв связаться с Ассоциацией застройщиков по телефону 8-800-550-23-93. "
    "Заканчивай посты тематическими хэштегами."
)

# Указываем путь к tesseract.exe, если используется Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
                        "Привет! Отправь текстовое сообщение, голосовое или фото, чтобы я помог создать уникальный контент."
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

            # Проверка на фото
            elif "photo" in data["message"]:
                file_id = data["message"]["photo"][-1]["file_id"]
                file_path = await get_telegram_file_path(file_id)
                photo_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                text_from_image = await extract_text_from_image(photo_url)
                if text_from_image:
                    response = f"Распознанный текст с изображения:\n{text_from_image}"
                else:
                    response = "Не удалось распознать текст на изображении."
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

async def extract_text_from_image(image_url):
    """Извлечение текста с изображения."""
    try:
        print(f"Попытка загрузить изображение с URL: {image_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    print(f"Изображение загружено: размер {len(image_data)} байт")
                else:
                    print(f"Ошибка при загрузке изображения: HTTP {response.status}")
                    return None

        image_path = "image.jpg"
        with open(image_path, "wb") as img_file:
            img_file.write(image_data)

        print(f"Изображение сохранено по пути: {image_path}")

        # Открываем изображение и выводим информацию о нём
        image = Image.open(image_path)
        print(f"Информация об изображении: формат={image.format}, размер={image.size}, цветовая палитра={image.mode}")

        # Преобразование изображения (например, в черно-белое)
        processed_image = image.convert("L")  # Преобразование в оттенки серого
        processed_image.save("processed_image.jpg")  # Сохраняем для отладки
        print("Изображение преобразовано в черно-белое и сохранено как 'processed_image.jpg'")

        # Распознавание текста с использованием Tesseract
        text = pytesseract.image_to_string(processed_image, lang='rus+eng')
        print(f"Распознанный текст: {text}")

        os.remove(image_path)  # Удаляем оригинальное изображение
        os.remove("processed_image.jpg")  # Удаляем обработанное изображение для экономии места

        return text.strip()
    except Exception as e:
        print(f"Ошибка обработки изображения: {e}")
        return None

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