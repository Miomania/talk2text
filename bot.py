import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
import os

# Настройка логирования:
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Убедитесь, что уровень логирования включен для отладки
)

TOKEN = '7588606694:AAF-5-IEioDYBs2wPFjQ133ArY8YYxKmrac'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Я ваш бот.')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(update.message.text)

async def voice_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Отправляем стартовое сообщение
    processing_message = await update.message.reply_text("Распознавание текста...")

    file = await context.bot.get_file(update.message.voice.file_id)
    with tempfile.NamedTemporaryFile(delete=False) as voice_file:
        await file.download_to_drive(voice_file.name)
        voice_file.close()

        audio = AudioSegment.from_ogg(voice_file.name)
        wav_path = voice_file.name + '.wav'
        audio.export(wav_path, format='wav')

        recognizer = sr.Recognizer()
        recognized_text = ""

        duration_per_chunk = 10 * 1000
        chunks = range(0, len(audio), duration_per_chunk)

        for i in chunks:
            chunk_audio = audio[i:i + duration_per_chunk]

            if chunk_audio.dBFS == float('-inf'):
                logging.debug(f"Тишина в сегменте {i / 1000}s - {(i + duration_per_chunk) / 1000}s, пропускаем этот фрагмент.")
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as chunk_wav_file:
                chunk_audio.export(chunk_wav_file.name, format='wav')

                with sr.AudioFile(chunk_wav_file.name) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                    audio_data = recognizer.record(source)

                    try:
                        text_fragment = recognizer.recognize_google(audio_data, language='ru-RU')
                        recognized_text += " " + text_fragment
                    except sr.UnknownValueError as e:
                        logging.error(f"Ошибка распознавания части аудио {i / 1000}s - {(i + duration_per_chunk) / 1000}s: {str(e)}")
                    except sr.RequestError as e:
                        logging.error(f"Ошибка сервиса распознавания речи {i / 1000}s - {(i + duration_per_chunk) / 1000}s: {str(e)}")

                os.remove(chunk_wav_file.name)
        
        # Обновляем сообщение с распознанным текстом
        if not recognized_text:
            await processing_message.edit_text("Не удалось распознать текст в аудио.")
        else:
            await processing_message.edit_text(f"Распознанный текст: {recognized_text}")
        
        os.remove(voice_file.name)
        os.remove(wav_path)

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(MessageHandler(filters.VOICE, voice_to_text))

    application.run_polling()

if __name__ == '__main__':
    main()
