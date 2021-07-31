from bot import bot
from flask import request
from app import app
from pyngrok import ngrok
import utils
import telebot
from utils import env

PORT = env['PORT']
TG_TOKEN = env['TG_TOKEN']


def gen_public_url():
    """
    Generates public ngrok link for dev purposes
    """
    return ngrok.connect(PORT, bind_tls=True).public_url


if utils.env['DEV']:
    env['DOMAIN'] = gen_public_url()

DOMAIN = env['DOMAIN']
# Setting up webhook
webhook_info = bot.get_webhook_info()
if webhook_info.url != DOMAIN:
    bot.set_webhook(f"{DOMAIN}/{TG_TOKEN}")


@app.route(f"/{TG_TOKEN}", methods=["POST"])
def tg_token():
    """Process Telegram webhook calls"""
    req_data = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(req_data)
    bot.process_new_updates([update])

    return ""


app.run(port=PORT, debug=True)
