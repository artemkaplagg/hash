# bot.py -- MONARCH BOT
from aiogram import Router
from content import LAWS, QUOTES, CHAPTERS, CHALLENGES, get_quote, get_chapter, get_challenge, REACTIONS_WIN
router = Router()

# aiogram 3.26 + Bot API 9.4 | HTML | цветные кнопки | реакции | FSM Scenes

import asyncio
import logging
import os
import random
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReactionTypeEmoji, URLInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    BOT_TOKEN, OWNER_ID, PHOTO_MORNING, PHOTO_DAY,
    PHOTO_EVENING, PHOTO_COOLDOWN_MIN, TZ_OFFSET
)
from database import (
    init_db, get_profile, update_streak, increment_tasks_done,
    increment_reads, update_last_photo,
    add_task, get_tasks, complete_task, delete_task, delete_all_tasks,
    save_action, get_last_actions, save_read, get_reads_count,
)
from content import LAWS, QUOTES, CHAPTERS, CHALLENGES, get_quote, get_chapter, get_challenge, REACTIONS_WIN
#     LAWS, QUOTES, CHAPTERS, CHALLENGES,
#     get_quote, get_chapter, get_challenge, REACTIONS_WIN
# )
# 
# logging.basicConfig(level=logging.INFO)
# router = Router()


# ─── UTILS ────────────────────────────────────────────────────

def now_kyiv() -> datetime:
    return datetime.now(timezone(timedelta(hours=TZ_OFFSET)))


def today_str() -> str:
    return now_kyiv().strftime("%Y-%m-%d")


def time_greeting() -> str:
    h = now_kyiv().hour
    if 5 <= h < 12:
        return "Доброе утро"
    if 12 <= h < 18:
        return "Добрый день"
    if 18 <= h < 23:
        return "Добрый вечер"
    return "Поздно уже"


def format_datetime() -> str:
    dt = now_kyiv()
    days = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
    months = ["января","февраля","марта","апреля","мая","июня",
              "июля","августа","сентября","октября","ноября","декабря"]
    return f"{days[dt.weekday()]}, {dt.day} {months[dt.month-1]} · {dt.strftime('%H:%M')}"


def get_photo_for_now() -> str:
    h = now_kyiv().hour
    if 6 <= h < 12:
        return PHOTO_MORNING
    if 12 <= h < 18:
        return PHOTO_DAY
    return PHOTO_EVENING


def should_send_photo(last_photo_sent: str | None) -> bool:
    if not last_photo_sent:
        return True
    try:
        last = datetime.fromisoformat(last_photo_sent)
        diff = (now_kyiv() - last).total_seconds() / 60
        return diff >= PHOTO_COOLDOWN_MIN
    except Exception:
        return True


def streak_phrase(streak: int) -> str:
    if streak == 0:
        return "Начни сегодня"
    if streak < 3:
        return "Хорошее начало"
    if streak < 7:
        return "Держишься"
    if streak < 14:
        return "Огонь не гаснет"
    if streak < 30:
        return "Сильная серия"
    return "Легенда"


# ─── MIDDLEWARE: только OWNER ──────────────────────────────────

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Any, Callable, Awaitable

class OwnerOnly(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        uid = None
        if isinstance(event, Message):
            uid = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            uid = event.from_user.id if event.from_user else None
        if uid != OWNER_ID:
            return
        return await handler(event, data)


# ─── FSM STATES ───────────────────────────────────────────────

class PlanFSM(StatesGroup):
    adding = State()

class ActionFSM(StatesGroup):
    writing = State()


# ─── KEYBOARDS ────────────────────────────────────────────────

def kb_main() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🗓  План на сегодня",  callback_data="plan",       style="primary"),
        InlineKeyboardButton(text="📚  Знания",           callback_data="know_menu",  style="success"),
    )
    b.row(
        InlineKeyboardButton(text="⚡  Действие",         callback_data="action_menu",style="success"),
        InlineKeyboardButton(text="📊  Статистика",       callback_data="stats",      style="primary"),
    )
    return b.as_markup()


def kb_plan(tasks: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in tasks:
        icon = "✅" if t["completed"] else "⬜"
        b.row(InlineKeyboardButton(
            text=f"{icon}  {t['title']}",
            callback_data=f"task_done:{t['id']}" if not t["completed"] else "noop",
            style="success" if t["completed"] else "primary",
        ))
    b.row(
        InlineKeyboardButton(text="➕  Добавить задачу",  callback_data="task_add",   style="success"),
        InlineKeyboardButton(text="🗑  Очистить всё",    callback_data="task_clear",  style="danger"),
    )
    b.row(InlineKeyboardButton(text="◀️  Назад",          callback_data="back_main",  style="primary"))
    return b.as_markup()


def kb_know() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="⚔️  Законы власти",   callback_data="know:law:0",    style="primary"),
        InlineKeyboardButton(text="💬  Цитаты",          callback_data="know:quote:0",  style="success"),
    )
    b.row(
        InlineKeyboardButton(text="📖  Главы",           callback_data="know:chapter:0",style="primary"),
        InlineKeyboardButton(text="🧩  Задачи",          callback_data="know:task:0",   style="success"),
    )
    b.row(InlineKeyboardButton(text="◀️  Назад",          callback_data="back_main",     style="primary"))
    return b.as_markup()


def kb_content_nav(ctype: str, idx: int, total: int, answered: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="◀️", callback_data=f"know:{ctype}:{(idx-1)%total}", style="primary"),
        InlineKeyboardButton(text=f"{idx+1}/{total}", callback_data="noop", style="primary"),
        InlineKeyboardButton(text="▶️", callback_data=f"know:{ctype}:{(idx+1)%total}", style="primary"),
    )
    if not answered:
        b.row(InlineKeyboardButton(
            text="✅  Прочитал",
            callback_data=f"know_read:{ctype}:{idx}",
            style="success",
        ))
    else:
        b.row(InlineKeyboardButton(text="✓  Засчитано", callback_data="noop", style="success"))
    b.row(InlineKeyboardButton(text="◀️  К разделам", callback_data="know_menu", style="primary"))
    return b.as_markup()


# ─── PLAN TEXT ────────────────────────────────────────────────

def plan_text(tasks: list[dict]) -> str:
    today = now_kyiv().strftime("%d.%m.%Y")
    done = sum(1 for t in tasks if t["completed"])
    total = len(tasks)

    if not tasks:
        return (
            f"<b>🗓  План на {today}</b>\n"
            f"<code>{'─'*22}</code>\n\n"
            f"<i>Задач пока нет.\n"
            f"Добавь первую 👇</i>"
        )

    lines = [
        f"<b>🗓  План на {today}</b>  <code>[{done}/{total}]</code>",
        f"<code>{'─'*22}</code>",
        "",
    ]
    for i, t in enumerate(tasks, 1):
        icon = "✅" if t["completed"] else f"{i}."
        title = f"<s>{t['title']}</s>" if t["completed"] else t["title"]
        lines.append(f"{icon}  {title}")

    if done == total and total > 0:
        lines += ["", "<b>🔥  Все задачи выполнены!</b>"]

    return "\n".join(lines)


# ─── /start ───────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    profile = await get_profile()
    streak = profile.get("streak", 0)
    joined = profile.get("joined_at", "")
    tasks = await get_tasks(today_str())
    done = sum(1 for t in tasks if t["completed"])
    total = len(tasks)

    # Считаем дни в боте
    days_in = 0
    if joined:
        try:
            j = datetime.fromisoformat(joined)
            days_in = (now_kyiv() - j.replace(tzinfo=timezone.utc)).days
        except Exception:
            days_in = 0

    task_line = ""
    if total > 0:
        task_line = f"\n📋  Задачи: <b>{done}/{total}</b>"

    text = (
        f"<b>👋  {time_greeting()}, Артём!</b>\n"
        f"<code>{'─'*24}</code>\n\n"
        f"📅  {format_datetime()}\n"
        f"🔥  Streak: <b>{streak} дн.</b>  <i>·  {streak_phrase(streak)}</i>"
        f"{task_line}\n\n"
        f"<blockquote>День {days_in+1} в системе</blockquote>\n\n"
        f"<i>Выбери раздел:</i>"
    )

    photo = get_photo_for_now()
    last_sent = profile.get("last_photo_sent")

    if photo and should_send_photo(last_sent):
        await update_last_photo(now_kyiv().isoformat())
        try:
            if photo.startswith("http"):
                await message.answer_photo(
                    photo=URLInputFile(photo),
                    caption=text,
                    reply_markup=kb_main(),
                )
            else:
                await message.answer_photo(
                    photo=photo,
                    caption=text,
                    reply_markup=kb_main(),
                )
            return
        except Exception:
            pass

    await message.answer(text, reply_markup=kb_main())
    await message.react([ReactionTypeEmoji(emoji="👋")])


# ─── BACK TO MAIN ─────────────────────────────────────────────

@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery):
    await call.answer()
    profile = await get_profile()
    streak = profile.get("streak", 0)
    tasks = await get_tasks(today_str())
    done = sum(1 for t in tasks if t["completed"])
    total = len(tasks)

    task_line = f"\n📋  Задачи: <b>{done}/{total}</b>" if total > 0 else ""

    text = (
        f"<b>👑  MONARCH</b>\n"
        f"<code>{'─'*24}</code>\n\n"
        f"📅  {format_datetime()}\n"
        f"🔥  Streak: <b>{streak} дн.</b>  <i>·  {streak_phrase(streak)}</i>"
        f"{task_line}\n\n"
        f"<i>Выбери раздел:</i>"
    )
    try:
        await call.message.edit_text(text, reply_markup=kb_main())
    except Exception:
        await call.message.answer(text, reply_markup=kb_main())


# ─── ПЛАН ─────────────────────────────────────────────────────

@router.callback_query(F.data == "plan")
async def show_plan(call: CallbackQuery):
    await call.answer()
    tasks = await get_tasks(today_str())
    try:
        await call.message.edit_text(plan_text(tasks), reply_markup=kb_plan(tasks))
    except Exception:
        await call.message.answer(plan_text(tasks), reply_markup=kb_plan(tasks))


@router.callback_query(F.data == "task_add")
async def task_add_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(PlanFSM.adding)
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="❌  Отмена", callback_data="task_add_cancel", style="danger"))
    await call.message.edit_text(
        "<b>➕  Новая задача</b>\n\n"
        "Напиши название задачи:\n"
        "<i>Можно добавить несколько -- каждую с новой строки</i>",
        reply_markup=b.as_markup(),
    )


@router.message(PlanFSM.adding)
async def task_add_process(message: Message, state: FSMContext):
    await state.clear()
    lines = [l.strip() for l in message.text.strip().splitlines() if l.strip()]
    if not lines:
        await message.answer("Пустое сообщение, попробуй снова.")
        return

    today = today_str()
    for line in lines[:10]:  # максимум 10 за раз
        await add_task(today, line[:100])

    tasks = await get_tasks(today)
    added = len(lines)
    await message.answer(
        f"{'✅' if added == 1 else '✅'} <b>{'Задача добавлена' if added == 1 else f'{added} задачи добавлены'}!</b>\n\n"
        + plan_text(tasks),
        reply_markup=kb_plan(tasks),
    )


@router.callback_query(F.data == "task_add_cancel")
async def task_add_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Отменено")
    tasks = await get_tasks(today_str())
    await call.message.edit_text(plan_text(tasks), reply_markup=kb_plan(tasks))


@router.callback_query(F.data.startswith("task_done:"))
async def task_toggle(call: CallbackQuery, bot: Bot):
    task_id = int(call.data.split(":")[1])
    await complete_task(task_id)
    await increment_tasks_done()

    tasks = await get_tasks(today_str())
    done = sum(1 for t in tasks if t["completed"])
    total = len(tasks)

    await call.answer(f"✅  +1")

    # Реакция при выполнении всех задач
    if done == total and total > 0:
        try:
            reaction = random.choice(REACTIONS_WIN)
            await bot.set_message_reaction(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reaction=[ReactionTypeEmoji(emoji=reaction)],
            )
        except Exception:
            pass

    # Обновляем streak если все сделаны
    if done == total and total > 0:
        profile = await get_profile()
        last = profile.get("last_report")
        today = today_str()
        if last != today:
            new_streak = profile.get("streak", 0) + 1
            await update_streak(new_streak, today)

    try:
        await call.message.edit_text(plan_text(tasks), reply_markup=kb_plan(tasks))
    except Exception:
        pass


@router.callback_query(F.data == "task_clear")
async def task_clear_confirm(call: CallbackQuery):
    await call.answer()
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅  Да, удалить",  callback_data="task_clear_yes", style="danger"),
        InlineKeyboardButton(text="❌  Отмена",       callback_data="plan",           style="primary"),
    )
    try:
        await call.message.edit_text(
            "🗑  Удалить <b>все задачи</b> на сегодня?",
            reply_markup=b.as_markup(),
        )
    except Exception:
        pass


@router.callback_query(F.data == "task_clear_yes")
async def task_clear_yes(call: CallbackQuery):
    await delete_all_tasks(today_str())
    await call.answer("Очищено")
    tasks = await get_tasks(today_str())
    await call.message.edit_text(plan_text(tasks), reply_markup=kb_plan(tasks))


# ─── ЗНАНИЯ ───────────────────────────────────────────────────

CONTENT_MAP = {
    "law":     (LAWS),
    "quote":   (QUOTES,    get_quote),
    "chapter": (CHAPTERS,  get_chapter),
    "task":    (CHALLENGES,get_challenge),
}

CONTENT_LABEL = {
    "law":     "⚔️  Закон",
    "quote":   "💬  Цитата",
    "chapter": "📖  Глава",
    "task":    "🧩  Задача",
}


@router.callback_query(F.data == "know_menu")
async def know_menu(call: CallbackQuery):
    await call.answer()
    reads = await get_reads_count()
    text = (
        f"<b>📚  База знаний</b>\n"
        f"<code>{'─'*22}</code>\n\n"
        f"⚔️  Законов власти:  <b>{len(LAWS)}</b>\n"
        f"💬  Цитат:          <b>{len(QUOTES)}</b>\n"
        f"📖  Глав:           <b>{len(CHAPTERS)}</b>\n"
        f"🧩  Задач:          <b>{len(CHALLENGES)}</b>\n\n"
        f"Прочитано всего: <b>{reads}</b>"
    )
    try:
        await call.message.edit_text(text, reply_markup=kb_know())
    except Exception:
        await call.message.answer(text, reply_markup=kb_know())


@router.callback_query(F.data.startswith("know:"))
async def show_content(call: CallbackQuery):
    await call.answer()
    _, ctype, idx_str = call.data.split(":")
    idx = int(idx_str)
    items, getter = CONTENT_MAP[ctype]
    item = getter(idx)
    total = len(items)
    label = CONTENT_LABEL[ctype]

    if ctype == "law":
        text = (
            f"<b>{label} #{item['number']}</b>\n"
            f"<b>{item['title']}</b>\n"
            f"<code>{'─'*22}</code>\n\n"
            f"{item['body']}\n\n"
            f"<blockquote>💡  {item['lesson']}</blockquote>"
        )
    elif ctype == "quote":
        text = (
            f"<b>{label}</b>\n"
            f"<code>{'─'*22}</code>\n\n"
            f"<blockquote><i>{item['text']}</i></blockquote>\n\n"
            f"— <b>{item['author']}</b>\n\n"
            f"<tg-spoiler>{item['context']}</tg-spoiler>"
        )
    elif ctype == "chapter":
        text = (
            f"<b>{label}</b>\n"
            f"<i>{item['source']}</i>\n"
            f"<b>{item['title']}</b>\n"
            f"<code>{'─'*22}</code>\n\n"
            f"<tg-spoiler>{item['body']}</tg-spoiler>\n\n"
            f"<b>❓  {item['question']}</b>"
        )
    else:  # task
        text = (
            f"<b>{label}</b>\n"
            f"<b>{item['title']}</b>\n"
            f"<code>{'─'*22}</code>\n\n"
            f"{item['task']}\n\n"
            f"<tg-spoiler>💡  {item['answer']}</tg-spoiler>"
        )

    try:
        await call.message.edit_text(text, reply_markup=kb_content_nav(ctype, idx, total))
    except Exception:
        await call.message.answer(text, reply_markup=kb_content_nav(ctype, idx, total))


@router.callback_query(F.data.startswith("know_read:"))
async def mark_read(call: CallbackQuery, bot: Bot):
    _, ctype, idx_str = call.data.split(":")
    idx = int(idx_str)
    items, _ = CONTENT_MAP[ctype]
    total = len(items)

    await save_read(ctype, idx)
    await increment_reads()
    await call.answer("+1 прочитано ✅")

    # Реакция
    try:
        await bot.set_message_reaction(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reaction=[ReactionTypeEmoji(emoji="🔥")],
        )
    except Exception:
        pass

    try:
        await call.message.edit_reply_markup(
            reply_markup=kb_content_nav(ctype, idx, total, answered=True)
        )
    except Exception:
        pass


# ─── ДЕЙСТВИЕ ─────────────────────────────────────────────────

@router.callback_query(F.data == "action_menu")
async def action_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    last = await get_last_actions(5)

    lines = ["<b>⚡  Действие</b>", f"<code>{'─'*22}</code>", ""]
    if last:
        lines.append("<i>Последние записи:</i>")
        for a in last:
            dt = a["created_at"][:10]
            lines.append(f"<code>{dt}</code>  {a['text'][:60]}")
        lines.append("")
    else:
        lines.append("<i>Записей пока нет</i>")
        lines.append("")

    lines.append("Напиши мысль, цель или действие 👇")

    await state.set_state(ActionFSM.writing)

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="❌  Отмена", callback_data="action_cancel", style="danger"))

    try:
        await call.message.edit_text("\n".join(lines), reply_markup=b.as_markup())
    except Exception:
        await call.message.answer("\n".join(lines), reply_markup=b.as_markup())


@router.message(ActionFSM.writing)
async def action_save(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    text = message.text.strip()
    if len(text) < 3:
        await message.answer("Слишком коротко.")
        return

    await save_action(text)

    await message.answer(
        f"<b>⚡  Записано</b>\n\n"
        f"<blockquote>{text}</blockquote>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="◀️  В меню", callback_data="back_main", style="primary")
        ]]),
    )

    try:
        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji="⚡")],
        )
    except Exception:
        pass


@router.callback_query(F.data == "action_cancel")
async def action_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Отменено")
    await back_main(call)


# ─── СТАТИСТИКА ───────────────────────────────────────────────

@router.callback_query(F.data == "stats")
async def show_stats(call: CallbackQuery):
    await call.answer()
    profile = await get_profile()
    reads = await get_reads_count()

    streak = profile.get("streak", 0)
    tasks_done = profile.get("tasks_done", 0)
    joined = profile.get("joined_at", "")

    days_in = 0
    if joined:
        try:
            j = datetime.fromisoformat(joined)
            days_in = (now_kyiv() - j.replace(tzinfo=timezone.utc)).days
        except Exception:
            days_in = 0

    # Streak бар
    bar_len = 10
    filled = min(streak, bar_len)
    bar = "🟧" * filled + "⬜" * (bar_len - filled)

    text = (
        f"<b>📊  Статистика</b>\n"
        f"<code>{'═'*24}</code>\n\n"
        f"📅  В системе: <b>{days_in+1} дн.</b>\n\n"
        f"<code>{'─'*24}</code>\n\n"
        f"🔥  <b>Streak</b>\n"
        f"<code>{bar}</code>\n"
        f"<b>{streak} дней</b>  ·  <i>{streak_phrase(streak)}</i>\n\n"
        f"<code>{'─'*24}</code>\n\n"
        f"✅  Задач выполнено:  <b>{tasks_done}</b>\n"
        f"📚  Материалов прочитано:  <b>{reads}</b>\n"
    )

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️  Назад", callback_data="back_main", style="primary"))

    try:
        await call.message.edit_text(text, reply_markup=b.as_markup())
    except Exception:
        await call.message.answer(text, reply_markup=b.as_markup())


# ─── NOOP ─────────────────────────────────────────────────────

@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


# ─── MAIN ─────────────────────────────────────────────────────

async def main():
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(OwnerOnly())
    dp.callback_query.middleware(OwnerOnly())
    dp.include_router(router)

    print("MONARCH BOT started")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
