import telebot
import utils

bot = telebot.TeleBot(utils.env['TG_TOKEN'])


@bot.message_handler(commands=["start"])
def start(msg):
    bot.reply_to(msg, "Yes, Sir!")

