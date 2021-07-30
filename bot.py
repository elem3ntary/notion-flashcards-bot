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
        text = f"Page \"{page_title}\" successfully added ✅"

    bot.send_message(message.from_user.id, text)


@bot.message_handler(commands=["reload"])
def reload(message):
    # TODO: show pages to reload, sorted by reload time
    markup = InlineKeyboardMarkup()
    last_three_button = InlineKeyboardButton("Reload 3 most recent", callback_data="reloadlol_last_three")
    markup.add(last_three_button)
    items = bot.session.get_pages(1)
    for item in items:
        # TODO: possibility to delete pages
        markup.add(InlineKeyboardButton(item["title"], callback_data=f"reload_{item['page_id']}"))

    bot.reply_to(message, "Choose which page to reload", reply_markup=markup)


def get_call_prefix(call):
    return call.data.split("_")[0]


def get_call_suffix(func):
    @wraps(func)
    def wrapper(*args):
        call, *_ = args
        suffix = call.data.split("_")[1:]
        return func(call, suffix)

    return wrapper


@bot.callback_query_handler(func=lambda call: get_call_prefix(call) == "reload")
@get_call_suffix
def reload_callback(call, suffix):
    result = bot.session.reload_flashcards(suffix[-1])
    if not result:
        text = "Error! Page might not exist"
    else:
        text = "Flashcards successfully updated!"
    bot.answer_callback_query(call.id, text)

# TODO: study mode
# TODO: passive learning mode
# TODO: passive learning mode settings
# TODO: export to anki?
