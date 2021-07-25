from bot import bot
from flask import request
from app import app
from pyngrok import ngrok
import utils
import telebot
from utils import env

PORT = env['PORT']
TG_TOKEN = env['TG_TOKEN']

# Setting up public url for dev purposes
if utils.env['DEV']:
    https_tunnel = ngrok.connect(PORT, bind_tls=True)
    webhook_info = bot.get_webhook_info()
    if webhook_info.url != https_tunnel:
        bot.set_webhook(f"{https_tunnel.public_url}/{TG_TOKEN}")


# Process webhook calls
@app.route(f"/{TG_TOKEN}", methods=["POST"])
def tg_token():
    req_data = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(req_data)
    bot.process_new_updates([update])

    return ""


app.run(port=PORT)
