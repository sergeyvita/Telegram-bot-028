import os
import logging
from telegram import Update, ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import openai
import pytesseract
from PIL import Image
from pydub import AudioSegment
from dotenv import load_dotenv

# Загрузка переменных окружения :))
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TESSERACT_CMD = os.getenv("TESSERACT_CMD")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

PROMPT = (
    "Этот GPT выступает в роли профессионального создателя контента для Телеграм-канала Ассоциации застройщиков. "
    "Он создает максимально продающие посты на темы недвижимости, строительства, законодательства, инвестиций, "
    "производит расчеты по стоимости квартир. Если производится расчет стоимости квартир, каждая переменная по стоимости, "
    "первоначальному взносу, процентной ставке, ежемесячному платежу прописываются каждая на отдельной строчке жирным шрифтом. "
    "Контент ориентирован на привлечение внимания, удержание аудитории и стимулирование действий (например, обращения за консультацией или покупки). "
    "GPT учитывает деловой, но не формальный тон и стремится быть доступным, информативным и вовлекающим. Посты красиво оформляются с использованием эмодзи "
    "в стиле 'энергичный и современный', добавляя динамичности и вовлеченности. Например: 🌇 для темы строительства, ✨ для выделения преимуществ, "
    "📲 для призывов к действию. Все посты структурированные и содержат четкие призывы к действию, информацию о контактах и гиперссылки. "
    "Если по запросу необходимо показать расчеты по квартирам, то жирным выделяются комнатность квартиры, площадь и ежемесячный платеж по ипотечному кредиту. "
    "В конце каждого поста перед хэштегами указывается название компании 'Ассоциация застройщиков', номер телефона 8-800-550-23-93."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот Ассоциации застройщиков. Задавайте свои вопросы, отправляйте голосовые сообщения или фото для обработки.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.message.chat.id

    # Установить статус "печатает"
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        reply = response['choices'][0]['message']['content'].strip()
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Ошибка обработки сообщения: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте позже.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_path = "image.jpg"
    await photo_file.download_to_drive(image_path)

    logging.info(f"Изображение сохранено по пути: {image_path}")

    try:
        extracted_text = pytesseract.image_to_string(Image.open(image_path), lang='rus+eng')
        if extracted_text.strip():
            logging.info(f"Распознанный текст: {extracted_text}")

            # Установить статус "печатает"
            await context.bot.send_chat_action(chat_id=update.message.chat.id, action=ChatAction.TYPING)

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": f"Текст с изображения: {extracted_text}"}
                ],
                max_tokens=1500,
                temperature=1
            )
            reply = response['choices'][0]['message']['content'].strip()
            await update.message.reply_text(reply)
        else:
            raise ValueError("Текст не распознан.")
    except Exception as e:
        logging.error(f"Ошибка обработки изображения: {e}")
        await update.message.reply_text("Не удалось распознать текст на изображении.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice_file = await update.message.voice.get_file()
    audio_path = "audio.ogg"
    wav_path = "audio.wav"
    await voice_file.download_to_drive(audio_path)

    logging.info(f"Голосовое сообщение сохранено по пути: {audio_path}")

    try:
        # Конвертация в WAV
        audio = AudioSegment.from_ogg(audio_path)
        audio.export(wav_path, format="wav")

        # Распознавание речи (опционально можно подключить Google Speech API или другую систему)
        transcript_response = openai.Audio.transcribe(
            model="whisper-1",
            file=open(wav_path, "rb")
        )

        transcript = transcript_response['text']
        logging.info(f"Распознанный текст из голосового сообщения: {transcript}")

        # Установить статус "печатает"
        await context.bot.send_chat_action(chat_id=update.message.chat.id, action=ChatAction.TYPING)

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": transcript}
            ],
            max_tokens=500,
            temperature=0.7
        )
        reply = response['choices'][0]['message']['content'].strip()
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Ошибка обработки голосового сообщения: {e}")
        await update.message.reply_text("Не удалось обработать голосовое сообщение. Попробуйте позже.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Установка вебхука
    logging.info("Установка вебхука")
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        webhook_url=WEBHOOK_URL
    )