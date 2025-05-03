import asyncio
import json
import os
import random
import logging

from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from speechkit import model_repository, configure_credentials, creds
from speechkit.stt import AudioProcessingType
from telegram import Update, Voice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

ASKING = 1
SIMILARITY_THRESHOLD = 50
MAX_QUESTIONS = 4
QUESTIONS = []
LOGGER = logging.getLogger(__name__)

user_data_store = {}

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    LOGGER.info(f"User {user_id} started the quiz.")
    questions = QUESTIONS.copy()[:MAX_QUESTIONS]
    random.shuffle(questions)
    user_data_store[user_id] = {
        "questions": questions,
        "answers": [],
        "pictures_iter": iter([q["picture"] for q in questions]),
        "pronounces_iter": iter([q["pronounce"] for q in questions]),
    }
    return await ask_next_question(update, context)


async def ask_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    state = user_data_store[user_id]

    picture = next(state["pictures_iter"], None)
    if not picture:
        LOGGER.info(f"User {user_id} completed all questions.")
        return await finalize_quiz(update, context)

    LOGGER.info(f"Sending question to user {user_id}.")
    await update.message.reply_photo(photo=open(picture, 'rb'))
    await update.message.reply_text(f"Ответь голосовым сообщением.")
    return ASKING


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    state = user_data_store.get(user_id)

    if not state:
        LOGGER.error(f"State not found for user {user_id}.")
        await update.message.reply_text("Произошла ошибка. Начни квиз заново командой /quiz.")
        return ConversationHandler.END

    voice = update.message.voice
    LOGGER.info(f"Received voice message from user {user_id}.")
    state["answers"].append(
        asyncio.create_task(
            download_and_recognize_voice(voice)
        )
    )
    pronounces_iter = state["pronounces_iter"]
    pronounce = next(pronounces_iter, None)
    if not pronounce:
        LOGGER.error(f"Pronounce not found for user {user_id}.")
        await update.message.reply_text("Произошла ошибка. Начни квиз заново командой /quiz.")
        return ConversationHandler.END

    await update.message.reply_voice(pronounce)
    return await ask_next_question(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    LOGGER.info(f"User {user_id} canceled the quiz.")
    await update.message.reply_text("Квиз отменён.")
    user_data_store.pop(update.effective_user.id, None)
    return ConversationHandler.END

def calculate_score(similarity):
    if similarity >= SIMILARITY_THRESHOLD:
        return similarity - SIMILARITY_THRESHOLD
    else:
        return 0

async def finalize_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    state = user_data_store[user_id]

    LOGGER.info(f"Finalizing quiz for user {user_id}.")
    await update.message.reply_text("Считаем результат...")

    recognized_answers = await asyncio.gather(*state["answers"])
    result = 0
    for i, q in enumerate(state["questions"]):
        recognized_answer = recognized_answers[i]
        correct_answer = q["answer"]
        similarity = fuzz.ratio(correct_answer, recognized_answer)
        LOGGER.info(f"Similarity for {correct_answer}: {similarity}")
        result += calculate_score(similarity)

    await update.message.reply_text(
        f"Набрано очков: {result}\n"
        "Правила /rules\n"
        "Ещё раз? /quiz\n"
    )

    return ConversationHandler.END

async def download_and_recognize_voice(voice: Voice):
    file = await voice.get_file()
    path = await file.download_to_drive()
    recognized = await asyncio.to_thread(recognize_voice, path)
    path.unlink()
    return recognized

def recognize_voice(audio):
    model = model_repository.recognition_model()
    model.model = 'general'  # https://yandex.cloud/en-ru/docs/speechkit/stt/models#tags
    model.language = 'en-US'  # https://yandex.cloud/en-ru/docs/speechkit/stt/models#languages
    model.audio_processing_type = AudioProcessingType.Full

    LOGGER.info(f"Send {audio} to Yandex STT")
    result = model.transcribe_file(audio)[0]
    LOGGER.info(f"Recive {audio} result from Yandex STT")

    return result.raw_text

def verify_questions(questions):
    required_keys = {"picture", "pronounce", "answer"}

    invalid_questions = [q for q in questions if not required_keys.issubset(q)]
    if len(invalid_questions) != 0:
        raise Exception(f"Incorrect question structure for some questions: {invalid_questions}")

    invalid_questions = []
    for q in questions:
        if not os.path.isfile(q["picture"]):
            invalid_questions.append(q)
        if not os.path.isfile(q["pronounce"]):
            invalid_questions.append(q)

    if len(invalid_questions) != 0:
        raise Exception(f"Some mandatory files is absent on local fs: {invalid_questions}")

    print("All checks passed")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(
        "Привет! Я бот для квиза по персонажам вселенной <a href='https://brainrot.fandom.com'>brainrot</a>.\n"
        "Доступные команды:\n"
        "/start - Запустить бота\n"
        "/quiz - Запустить квиз\n"
        "/cancel - Закончить квиз\n"
        "/rules - Показать правила\n",
        disable_web_page_preview=True
    )

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Правила квиза:\n"
        "1. Ответы принимаются только голосовыми сообщениями.\n"
        "2. За правильный ответ начисляются очки.\n"
        "3. Чем больше похоже на оригинал - тем больше очков.\n"
        "4. Максимум очков за правильный ответ - 50.\n"
        "5. Одна попытка - 4 вопроса.\n"
        "6. Удачи!"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.error("Exception while handling an update:", exc_info=context.error)

    if update and isinstance(update, Update) and update.effective_user:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Произошла ошибка. Попробуй последнее действие ещё раз."
        )

def main() -> None:
    with open("questions.json", "r", encoding="utf-8") as file:
        global QUESTIONS
        QUESTIONS = json.load(file)
    verify_questions(QUESTIONS)
    load_dotenv()
    configure_credentials(
        yandex_credentials=creds.YandexCredentials(
            api_key=os.getenv("YC_API_KEY")
        )
    )
    application = ApplicationBuilder().token(os.getenv("TG_BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("quiz", start_quiz)],
        states={
            ASKING: [MessageHandler(filters.VOICE, handle_voice)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler(["start", "help"], help_command))
    application.add_handler(CommandHandler("rules", rules_command))

    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
