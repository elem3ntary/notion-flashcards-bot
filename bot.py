import telebot
from telebot.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from utils import env
from user import User
import re

telebot.apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(env['TG_TOKEN'])
SESSIONS: dict[str, User] = {}

bot.set_my_commands([
    BotCommand("/start", "Shows basic bot info"),
    BotCommand("/login", "Process login via Notion")
])


def get_or_set_session(from_user):
    user_id = from_user.id
    try:
        return SESSIONS[user_id]
    except KeyError:
        SESSIONS[user_id] = User.from_telegram_credentials(from_user)
        return SESSIONS[user_id]


@bot.middleware_handler(update_types=['message'])
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


@bot.message_handler(commands=["login"])
def login(message):
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Login via Notion", url=bot.session.generate_login_url())
    markup.add(button)
    bot.reply_to(message, "Please allow access to your workspace to proceed", reply_markup=markup)


@bot.message_handler(commands=["add_page"])
def add_page(message):
    text = "Send me link to the page:"
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    # url="https://bloom-eyebrow-74f.notion.site/Where-to-get-page-link-c1ede68fd209478ab1ac96f277a405e0"
    button = KeyboardButton(return_to_main)
    markup.add(button)
    next_message = bot.reply_to(message, text, reply_markup=markup)
    bot.register_next_step_handler(next_message, add_page_save)


def add_page_save(message):
    match = re.search(r"https://www.notion.so/.+-(.+)", message.text)

    if action := RESERVED_KEYWORDS.get(message.text):
        return action(message)

    if not match:
        bot.send_message(message.from_user.id, "Invalid link")
        return add_page(message)
    groups = match.groups()
    bot.session.add_page(groups[0])
# validation
