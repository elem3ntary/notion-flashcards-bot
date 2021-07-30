import telebot
from telebot.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from utils import env
from user import User
import re
import logging
from functools import wraps
from functools import partial

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

telebot.apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(env['TG_TOKEN'])
SESSIONS: dict[str, User] = {}

bot.set_my_commands([
    BotCommand("/start", "Shows basic bot info"),
    BotCommand("/add_page", "Adds new page to bot`s library"),
    BotCommand("/reload", "Reloads flashcards from pages you have chosen for"),
    BotCommand("/study", "Starts active learning mode"),
    BotCommand("/passive", "Shows passive learning mode settings"),
    BotCommand("/login", "Process login via Notion")
])


def get_or_set_session(from_user):
    user_id = from_user.id
    try:
        return SESSIONS[user_id]
    except KeyError:
        SESSIONS[user_id] = User.from_telegram_credentials(from_user)
        return SESSIONS[user_id]


@bot.middleware_handler(update_types=['message', 'callback_query'])
def set_session(bot_instance, message):
    user = get_or_set_session(message.from_user)
    bot_instance.session = user


@bot.message_handler(commands=["start"])
def start(message):
    text = f"""
Hello, {message.from_user.first_name}. Welcome to Notion Flashcards Bot 🤸‍♀️ 
We are glad to see you here and ready to help you ^-^

Use /add_page to add new page for learning
Use /reload to reload flashcards from page
Use /study to enter manual study mode
Use /passive to change passive learning settings

🌟 Flashcards are reloaded automatically every 3 hours 🌟

Productive learning bro!


    """
    print(bot.session.is_logged_in_notion())
    if not bot.session.is_logged_in_notion():
        text += "It seems that you are not authorized. Please user /login to do it."

    bot.reply_to(message, text)


return_to_main = "Return to main"
RESERVED_KEYWORDS = {
    return_to_main: start
}


@bot.message_handler(func=lambda m: RESERVED_KEYWORDS.get(m.text, None))
def reserved_words(message):
    action = RESERVED_KEYWORDS[message.text]
    return action(message)


@bot.message_handler(commands=["login"])
def login(message):
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Login via Notion", url=bot.session.generate_login_url())
    markup.add(button)
    bot.reply_to(message, "Please allow access to your workspace to proceed", reply_markup=markup)


@bot.message_handler(commands=["add_page"])
def add_page(message):
    text = "Send me link to the page:"
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button = KeyboardButton(return_to_main)
    markup.add(button)
    next_message = bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(next_message, add_page_save)


def add_page_save(message):
    match = re.search(r"^https://www.notion.so/.+-(.{32})$", message.text)

    # TODO: забрати костиль та зробити декоратор
    if action := RESERVED_KEYWORDS.get(message.text, None):
        return action(message)

    if not match:
        bot.send_message(message.from_user.id, "Invalid link")
        return add_page(message)

    page_id = match.groups()[0]
    result = bot.session.add_page(page_id)
    if not result:
        text = "Page already exists or max page limit (5) exceeded ⛔️"
    else:
        page_title = bot.session.notion.page().retrieve(page_id).get_title()
        text = f"Page \"{page_title}\" successfully added and flashcards reloaded✅"

    bot.send_message(message.from_user.id, text)


def render_pages_markup(pages):
    markup = InlineKeyboardMarkup()
    for item in pages:
        title_button = InlineKeyboardButton(f"{item['title']}",
                                            callback_data=f"title_{item['page_id']}")
        reload_button = InlineKeyboardButton("♻️️", callback_data=f"reload_{item['page_id']}")
        delete_button = InlineKeyboardButton("⛔️", callback_data=f"delete_{item['page_id']}")
        markup.add(title_button, reload_button, delete_button)

    return markup


@bot.message_handler(commands=["reload"])
def reload(message):
    pages = bot.session.get_pages(1)
    if pages.count() < 1:
        text = "No pages are added"
    else:
        text = "Choose which page to reload"

    markup = render_pages_markup(pages)
    bot.reply_to(message, text, reply_markup=markup)


def get_call_prefix(call):
    return call.data.split("_")[0]


def get_call_suffix(func):
    @wraps(func)
    def wrapper(*args):
        call, *_ = args
        suffix = call.data.split("_")[-1]
        return func(call, suffix)

    return wrapper


@bot.callback_query_handler(func=lambda call: get_call_prefix(call) == "reload")
@get_call_suffix
def reload_callback(call, suffix):
    result = bot.session.reload_flashcards(suffix)
    if not result:
        text = "Error! Page might not exist"
    else:
        text = "Flashcards successfully updated!"
    bot.answer_callback_query(call.id, text)


@bot.callback_query_handler(func=lambda call: get_call_prefix(call) == "delete")
@get_call_suffix
def delete_callback(call, suffix):
    bot.session.delete_page(suffix)
    text = "Page deleted"
    bot.answer_callback_query(call.id, text)
    pages = bot.session.get_pages(1)
    markup = render_pages_markup(pages)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=markup)


def render_flashcard_message(flashcard, front_side=True):
    markup = InlineKeyboardMarkup()
    flashcard_id = flashcard['_id']
    text = "-" * 25 + "Flashcard" + "-" * 25 + "\n\n"
    text += flashcard["front_side"] if front_side else flashcard["back_side"]
    flashcard_position = "front" if front_side else "back"
    flashcard_text_btn = InlineKeyboardButton("*flip*",
                                              callback_data=f"flashcard-flip_{flashcard_position}_{flashcard_id}")

    markup.add(flashcard_text_btn, row_width=10)
    yes_btn = InlineKeyboardButton("✅", callback_data=f"flashcard-yes_{flashcard_id}")
    easy_btn = InlineKeyboardButton("✨", callback_data=f"flashcard-ez_{flashcard_id}")
    hard_btn = InlineKeyboardButton("🏋️‍♂️", callback_data=f"flashcard-hard_{flashcard_id}")
    no_btn = InlineKeyboardButton("❌", callback_data=f"flashcard-no_{flashcard_id}")

    markup.add(easy_btn, hard_btn, no_btn)
    markup.add(yes_btn)

    return text, markup


@bot.message_handler(commands=["study"])
def study_mode(message):
    flashcard = bot.session.get_next_flashcard()
    text, markup = render_flashcard_message(flashcard)
    bot.send_message(message.from_user.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: get_call_prefix(call) == "flashcard-flip")
@get_call_suffix
def flip_callback(call, suffix):
    flashcard = bot.session.get_flashcard_by_id(suffix)
    new_front_side = False if call.data.split("_")[1] == "front" else True
    text, markup = render_flashcard_message(flashcard, front_side=new_front_side)
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)

# TODO: study mode
# TODO: passive learning mode
# TODO: passive learning mode settings
# TODO: export to anki?
