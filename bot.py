"""
Telegram-бот: диагностический тест "Насколько твой стиль усиливает твою мужскую привлекательность?"

Технологии: Python 3.11+, aiogram 3.x, python-dotenv
Без базы данных — состояние пользователей хранится в памяти (словарь user_states).
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command

# ---------------------------------------------------------------------------
# Загрузка переменных окружения
# ---------------------------------------------------------------------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")
PERSONAL_LINK = os.getenv("PERSONAL_LINK", "https://t.me/your_username")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден! Проверь .env файл.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------------------------------------------------------------------------
# Хранилище состояния пользователей (в памяти, без БД)
# ---------------------------------------------------------------------------
# Структура одной записи:
# user_states[user_id] = {
#     "current_question": int,   # индекс текущего вопроса (0..19)
#     "scores": {"A": int, "B": int, "C": int, "D": int},
# }
user_states: dict[int, dict] = {}

# ---------------------------------------------------------------------------
# Данные теста: 20 вопросов, каждый с категорией и 4 вариантами ответов
# Категории: A - Первое впечатление, B - Система стиля,
#            C - Привлекательность, D - Индивидуальность
# Каждый вариант: (текст, баллы 0-3)
# ---------------------------------------------------------------------------

QUESTIONS = [
    # --- Категория A: Первое впечатление ---
    {
        "category": "A",
        "text": "Когда ты знакомишься с новым человеком, что происходит чаще всего?",
        "options": [
            ("Меня почти не запоминают", 0),
            ("Отношение нейтральное", 1),
            ("Обычно оставляю хорошее впечатление", 2),
            ("Часто замечаю искренний интерес к себе", 3),
        ],
    },
    {
        "category": "A",
        "text": "За последние 30 дней тебе делали комплимент внешнему виду?",
        "options": [
            ("Ни разу", 0),
            ("Один раз", 1),
            ("Несколько раз", 2),
            ("Регулярно", 3),
        ],
    },
    {
        "category": "A",
        "text": "Если завтра тебя пригласят на важное мероприятие, насколько уверен, что произведешь сильное первое впечатление?",
        "options": [
            ("Вообще не уверен", 0),
            ("Скорее нет", 1),
            ("Скорее да", 2),
            ("Полностью уверен", 3),
        ],
    },
    {
        "category": "A",
        "text": "Когда смотришь свои случайные фотографии, чаще думаешь:",
        "options": [
            ("Удалить это", 0),
            ("Нормально", 1),
            ("Нравится", 2),
            ("Выгляжу охуенно", 3),
        ],
    },
    {
        "category": "A",
        "text": "Как часто люди проявляют интерес к тебе после первого знакомства?",
        "options": [
            ("Практически никогда", 0),
            ("Редко", 1),
            ("Иногда", 2),
            ("Часто", 3),
        ],
    },
    # --- Категория B: Система стиля ---
    {
        "category": "B",
        "text": "Сколько времени нужно, чтобы собрать образ на свидание?",
        "options": [
            ("Больше часа", 0),
            ("20–60 минут", 1),
            ("До 20 минут", 2),
            ("Уже есть готовые варианты", 3),
        ],
    },
    {
        "category": "B",
        "text": "Если открыть твой шкаф прямо сейчас:",
        "options": [
            ("Хаос", 0),
            ("Есть хорошие вещи, но нет системы", 1),
            ("Большинство вещей сочетаются", 2),
            ("Всё продумано", 3),
        ],
    },
    {
        "category": "B",
        "text": "Сколько вещей ты реально носишь?",
        "options": [
            ("Меньше 30%", 0),
            ("Около половины", 1),
            ("Большинство", 2),
            ("Практически все", 3),
        ],
    },
    {
        "category": "B",
        "text": "Покупая новую вещь:",
        "options": [
            ("Просто понравилась", 0),
            ("Иногда думаю с чем носить", 1),
            ("Обычно понимаю куда встроить", 2),
            ("Всегда покупаю под систему", 3),
        ],
    },
    {
        "category": "B",
        "text": "Есть ли у тебя готовые образы под разные жизненные ситуации?",
        "options": [
            ("Нет", 0),
            ("Под одну ситуацию", 1),
            ("Под несколько", 2),
            ("Под все основные ситуации", 3),
        ],
    },
    # --- Категория C: Привлекательность ---
    {
        "category": "C",
        "text": "Как часто девушки сами проявляют интерес?",
        "options": [
            ("Практически никогда", 0),
            ("Редко", 1),
            ("Иногда", 2),
            ("Регулярно", 3),
        ],
    },
    {
        "category": "C",
        "text": "Когда заходишь в новое место:",
        "options": [
            ("Хочется не выделяться", 0),
            ("Нейтрально", 1),
            ("Чувствую себя уверенно", 2),
            ("Чувствую себя хозяином положения", 3),
        ],
    },
    {
        "category": "C",
        "text": "Как часто ты откладываешь знакомство, потому что выглядишь не так, как хотелось бы?",
        "options": [
            ("Часто", 0),
            ("Иногда", 1),
            ("Редко", 2),
            ("Никогда", 3),
        ],
    },
    {
        "category": "C",
        "text": "Твой внешний вид сейчас:",
        "options": [
            ("Скорее мешает", 0),
            ("Почти не влияет", 1),
            ("Помогает", 2),
            ("Сильно помогает", 3),
        ],
    },
    {
        "category": "C",
        "text": "Если завтра свидание с девушкой мечты:",
        "options": [
            ("Срочно менял бы образ", 0),
            ("Немного переживал бы", 1),
            ("Был бы спокоен", 2),
            ("Пошел бы прямо сейчас", 3),
        ],
    },
    # --- Категория D: Индивидуальность ---
    {
        "category": "D",
        "text": "Может ли человек описать твой стиль после одной встречи?",
        "options": [
            ("Нет", 0),
            ("Вряд ли", 1),
            ("Скорее да", 2),
            ("Да", 3),
        ],
    },
    {
        "category": "D",
        "text": "Чем твой стиль отличается от большинства мужчин вокруг?",
        "options": [
            ("Ничем", 0),
            ("Немного", 1),
            ("Заметно", 2),
            ("Очень сильно", 3),
        ],
    },
    {
        "category": "D",
        "text": "Есть ли у твоего стиля идея?",
        "options": [
            ("Нет", 0),
            ("Никогда не думал", 1),
            ("Частично", 2),
            ("Да, четко понимаю свой вайб", 3),
        ],
    },
    {
        "category": "D",
        "text": "Можешь описать свой стиль в трех словах?",
        "options": [
            ("Нет", 0),
            ("Очень размыто", 1),
            ("Примерно могу", 2),
            ("Легко", 3),
        ],
    },
    {
        "category": "D",
        "text": "Насколько твой внешний вид отражает твою личность?",
        "options": [
            ("Практически никак", 0),
            ("Частично", 1),
            ("В основном", 2),
            ("Полностью", 3),
        ],
    },
]

TOTAL_QUESTIONS = len(QUESTIONS)  # 20

CATEGORY_NAMES = {
    "A": "Первое впечатление",
    "B": "Система стиля",
    "C": "Привлекательность",
    "D": "Индивидуальность",
}

# ---------------------------------------------------------------------------
# Тексты уровней по итоговому баллу (0-60)
# ---------------------------------------------------------------------------

def get_level_text(total_score: int) -> tuple[str, str]:
    """Возвращает (название уровня, текст уровня) по общему баллу."""
    if 0 <= total_score <= 15:
        return (
            "NPC",
            "Сейчас твой внешний вид почти не работает на тебя.\n\n"
            "Скорее всего, ты выглядишь как большинство мужчин и почти не "
            "управляешь первым впечатлением.\n\n"
            "Это не значит, что с тобой что-то не так.\n\n"
            "Это значит, что твой внешний образ пока не показывает миру твою "
            "реальную личность, характер и потенциал."
        )
    elif 16 <= total_score <= 30:
        return (
            "Случайный стиль",
            "У тебя уже могут быть нормальные вещи.\n\n"
            "Но пока нет системы.\n\n"
            "Иногда образ получается удачным, иногда случайным.\n\n"
            "Из-за этого ты можешь выглядеть проще, слабее или скучнее, чем "
            "являешься на самом деле."
        )
    elif 31 <= total_score <= 45:
        return (
            "Мужчина со вкусом",
            "У тебя уже есть база.\n\n"
            "Ты не выглядишь случайно, но стиль пока не стал твоим "
            "полноценным инструментом.\n\n"
            "Сейчас у тебя есть потенциал сделать образ более запоминающимся, "
            "привлекательным и статусным."
        )
    else:  # 46-60
        return (
            "Магнит",
            "Твой внешний вид уже работает на тебя.\n\n"
            "Ты понимаешь, как через стиль усиливать первое впечатление, "
            "привлекательность и собственное состояние.\n\n"
            "Следующий уровень — превратить стиль в систему и часть личного "
            "бренда."
        )


# ---------------------------------------------------------------------------
# Тексты для самой слабой зоны
# ---------------------------------------------------------------------------

WEAK_ZONE_TEXTS = {
    "A": (
        "Твоя главная просадка — первое впечатление.\n\n"
        "Это значит, что люди могут не считывать твою реальную ценность в "
        "первые секунды.\n\n"
        "Ты можешь быть умным, амбициозным и интересным, но внешний образ не "
        "сразу это показывает.\n\n"
        "В итоге тебе приходится доказывать то, что сильный образ мог бы "
        "транслировать сразу."
    ),
    "B": (
        "Твоя главная просадка — система стиля.\n\n"
        "Скорее всего, у тебя есть отдельные нормальные вещи, но они не "
        "складываются в цельный образ.\n\n"
        "Из-за этого стиль выглядит случайным.\n\n"
        "А случайный стиль редко создает сильное впечатление."
    ),
    "C": (
        "Твоя главная просадка — привлекательность образа.\n\n"
        "Это значит, что внешний вид пока не усиливает твою сексуальность, "
        "уверенность и интерес к тебе со стороны девушек так, как мог бы.\n\n"
        "Не потому что ты непривлекательный.\n\n"
        "А потому что образ пока не раскрывает твой потенциал."
    ),
    "D": (
        "Твоя главная просадка — индивидуальность.\n\n"
        "Ты можешь выглядеть нормально, но не запоминаться.\n\n"
        "А в современном мире 'нормально' часто означает 'невидимо'.\n\n"
        "Проблема не в отсутствии личности.\n\n"
        "Проблема в том, что внешний образ пока не умеет ее показывать."
    ),
}


# ---------------------------------------------------------------------------
# Тексты блоков после результата
# ---------------------------------------------------------------------------

LOSING_NOW_TEXT = (
    "Что ты можешь терять прямо сейчас:\n\n"
    "— более сильное первое впечатление\n"
    "— внимание девушек\n"
    "— ощущение уверенности\n"
    "— запоминаемость\n"
    "— возможность выглядеть дороже и интереснее без лишних слов"
)

WHATS_NEXT_TEXT = (
    "Хорошая новость:\n\n"
    "стиль — это не талант.\n\n"
    "Это система.\n\n"
    "И в ближайшие дни я начну разбирать в канале, как эта система работает:\n\n"
    "— почему стиль влияет на коммуникацию\n"
    "— как работает эффект ореола\n"
    "— почему одни мужчины запоминаются, а другие остаются фоном\n"
    "— как создать образ, который отражает твою личность\n"
    "— как использовать стиль как инструмент мужской привлекательности\n\n"
    "Сделай скриншот своего результата.\n\n"
    "Скоро я покажу, как прокачивать каждую из этих зон."
)

WELCOME_TEXT = (
    "Бро, этот тест покажет, насколько твой внешний вид сейчас работает на "
    "тебя.\n\n"
    "Не в формате душных цветотипов и модных трендов.\n\n"
    "А по реальным вещам:\n\n"
    "— какое первое впечатление ты производишь\n"
    "— насколько твой образ отражает твою личность\n"
    "— помогает ли внешний вид твоей привлекательности\n"
    "— есть ли у тебя вообще свой стиль\n\n"
    "20 вопросов.\n"
    "Примерно 3 минуты.\n\n"
    "В конце ты получишь свой уровень, баллы по 4 зонам и поймешь, где "
    "сейчас главная просадка."
)

UNKNOWN_MESSAGE_TEXT = "Бро, чтобы пройти тест, нажми /start"
UNKNOWN_CALLBACK_TEXT = (
    "Бро, эта кнопка уже неактуальна. Нажми /restart и пройди тест заново."
)


# ---------------------------------------------------------------------------
# Вспомогательные функции для клавиатур
# ---------------------------------------------------------------------------

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Пройти тест'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пройти тест", callback_data="start_test")]
        ]
    )


def get_question_keyboard(question_index: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с вариантами ответа для конкретного вопроса.
    callback_data формата: "answer:{question_index}:{option_index}"
    """
    question = QUESTIONS[question_index]
    buttons = []
    for option_index, (option_text, _score) in enumerate(question["options"]):
        callback_data = f"answer:{question_index}:{option_index}"
        buttons.append(
            [InlineKeyboardButton(text=option_text, callback_data=callback_data)]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_final_keyboard() -> InlineKeyboardMarkup:
    """Финальная клавиатура с переходом в канал, личным разбором и рестартом."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в канал", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="Получить личный разбор", url=PERSONAL_LINK)],
            [InlineKeyboardButton(text="Пройти заново", callback_data="restart_test")],
        ]
    )


# ---------------------------------------------------------------------------
# Логика отправки вопроса
# ---------------------------------------------------------------------------

async def send_question(chat_id: int, question_index: int, edit_message: Message | None = None):
    """
    Отправляет (или редактирует) сообщение с вопросом question_index.
    Показывает прогресс "Вопрос X/20".
    """
    question = QUESTIONS[question_index]
    progress_text = f"Вопрос {question_index + 1}/{TOTAL_QUESTIONS}\n\n{question['text']}"
    keyboard = get_question_keyboard(question_index)

    if edit_message is not None:
        await edit_message.edit_text(progress_text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, progress_text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Логика показа результата
# ---------------------------------------------------------------------------

async def send_result(chat_id: int, scores: dict[str, int], edit_message: Message | None = None):
    """
    Считает итоговые баллы, определяет уровень и самую слабую зону,
    отправляет серию сообщений с результатом.
    """
    total_score = sum(scores.values())

    # 1. Уровень
    level_name, level_text = get_level_text(total_score)
    text_level = f"Твой уровень: {level_name}\n\n{level_text}"

    if edit_message is not None:
        await edit_message.edit_text(text_level)
    else:
        await bot.send_message(chat_id, text_level)

    # 2. Показатели по зонам
    stats_text = (
        "Твои показатели:\n\n"
        f"Первое впечатление — {scores['A']}/15\n"
        f"Система стиля — {scores['B']}/15\n"
        f"Привлекательность — {scores['C']}/15\n"
        f"Индивидуальность — {scores['D']}/15"
    )
    await bot.send_message(chat_id, stats_text)

    # 3. Самая слабая зона (если несколько с минимумом — берем первую по порядку A,B,C,D)
    weakest_category = min(scores, key=lambda cat: (scores[cat], "ABCD".index(cat)))
    weak_text = WEAK_ZONE_TEXTS[weakest_category]
    await bot.send_message(chat_id, weak_text)

    # 4. Что можно терять
    await bot.send_message(chat_id, LOSING_NOW_TEXT)

    # 5. Что делать дальше + финальные кнопки
    await bot.send_message(chat_id, WHATS_NEXT_TEXT, reply_markup=get_final_keyboard())


# ---------------------------------------------------------------------------
# Хендлеры команд
# ---------------------------------------------------------------------------

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start — приветствие и кнопка начала теста."""
    user_id = message.from_user.id
    # Сбрасываем состояние пользователя на старте (на случай если был старый прогресс)
    user_states.pop(user_id, None)

    await message.answer(WELCOME_TEXT, reply_markup=get_start_keyboard())


@dp.message(Command("restart"))
async def cmd_restart(message: Message):
    """Обработчик команды /restart — сбрасывает прогресс и предлагает начать заново."""
    user_id = message.from_user.id
    user_states.pop(user_id, None)

    await message.answer(
        "Хорошо, бро, начинаем заново.\n\n" + WELCOME_TEXT,
        reply_markup=get_start_keyboard(),
    )


# ---------------------------------------------------------------------------
# Хендлеры callback-кнопок
# ---------------------------------------------------------------------------

@dp.callback_query(F.data == "start_test")
async def callback_start_test(callback: CallbackQuery):
    """Запускает тест: создает состояние пользователя и показывает первый вопрос."""
    user_id = callback.from_user.id

    # Инициализируем состояние пользователя
    user_states[user_id] = {
        "current_question": 0,
        "scores": {"A": 0, "B": 0, "C": 0, "D": 0},
    }

    await send_question(callback.message.chat.id, 0, edit_message=callback.message)
    await callback.answer()


@dp.callback_query(F.data == "restart_test")
async def callback_restart_test(callback: CallbackQuery):
    """Перезапускает тест по кнопке 'Пройти заново'."""
    user_id = callback.from_user.id
    user_states.pop(user_id, None)

    await callback.message.answer(WELCOME_TEXT, reply_markup=get_start_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("answer:"))
async def callback_answer(callback: CallbackQuery):
    """
    Обрабатывает ответ пользователя на вопрос.
    callback_data формата "answer:{question_index}:{option_index}"
    """
    user_id = callback.from_user.id

    # Если состояния нет — пользователь нажал на старую/неактуальную кнопку
    if user_id not in user_states:
        await callback.answer(UNKNOWN_CALLBACK_TEXT, show_alert=True)
        return

    # Разбираем callback_data
    try:
        _, question_index_str, option_index_str = callback.data.split(":")
        question_index = int(question_index_str)
        option_index = int(option_index_str)
    except (ValueError, IndexError):
        await callback.answer(UNKNOWN_CALLBACK_TEXT, show_alert=True)
        return

    state = user_states[user_id]

    # Проверяем, что отвечают именно на текущий вопрос
    # (защита от нажатия кнопок старого вопроса)
    if question_index != state["current_question"]:
        await callback.answer(UNKNOWN_CALLBACK_TEXT, show_alert=True)
        return

    # Проверяем валидность индекса вопроса/варианта
    if question_index < 0 or question_index >= TOTAL_QUESTIONS:
        await callback.answer(UNKNOWN_CALLBACK_TEXT, show_alert=True)
        return

    question = QUESTIONS[question_index]
    if option_index < 0 or option_index >= len(question["options"]):
        await callback.answer(UNKNOWN_CALLBACK_TEXT, show_alert=True)
        return

    # Начисляем баллы в нужную категорию
    _option_text, score = question["options"][option_index]
    category = question["category"]
    state["scores"][category] += score

    # Переходим к следующему вопросу
    next_question_index = question_index + 1
    state["current_question"] = next_question_index

    if next_question_index < TOTAL_QUESTIONS:
        # Показываем следующий вопрос
        await send_question(
            callback.message.chat.id, next_question_index, edit_message=callback.message
        )
    else:
        # Тест завершен — показываем результат и очищаем состояние
        scores = state["scores"]
        user_states.pop(user_id, None)
        await send_result(callback.message.chat.id, scores, edit_message=callback.message)

    await callback.answer()


# ---------------------------------------------------------------------------
# Обработка неизвестных сообщений и callback'ов (должны быть зарегистрированы последними)
# ---------------------------------------------------------------------------

@dp.callback_query()
async def callback_unknown(callback: CallbackQuery):
    """Любые callback-запросы, не обработанные выше — считаем неактуальными."""
    await callback.answer(UNKNOWN_CALLBACK_TEXT, show_alert=True)


@dp.message()
async def message_unknown(message: Message):
    """Любые текстовые сообщения, не являющиеся командами /start или /restart."""
    await message.answer(UNKNOWN_MESSAGE_TEXT)


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

async def main():
    logger.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
