import telebot
from utils import env
from user import User

telebot.apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(env['TG_TOKEN'])
SESSIONS: dict[str, User] = {}


def get_or_set_session(from_user):
    user_id = from_user.id
    try:
        return SESSIONS[user_id]
    except KeyError:
        SESSIONS[user_id] = User.from_telegram_credentials(from_user)
        return SESSIONS[user_id]


@bot.middleware_handler(update_types=['message'])
def set_session(bot_instance, message):
    bot_instance.session = get_or_set_session(message.from_user)


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, f"Hello, {message.from_user.first_name}")


@bot.message_handler(commands=["login"])
def login(message):
    bot.reply_to(message, bot.session.generate_login_url())
