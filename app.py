from flask import Flask, request
from user import User
from bot import bot

app = Flask(__name__)


@app.route('/notion_auth', methods=["GET"])
def notion_auth():
    state_token = request.args["state"]
    code = request.args["code"]
    user = User.from_id(state_token)
    if not user:
        return 400, "Oops. Try again latter!"
    result = user.fetch_access_token(code)
    if not result:
        return 400, "Oops. Try again latter!"
    bot.send_photo(chat_id=user.user["user_id"], photo=result["workspace_icon"],
                   caption=f"Workspace name: {result['workspace_name']}")
    return result
