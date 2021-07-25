from flask import Flask, request

app = Flask(__name__)

@app.route('/notion_auth')
def notion_auth():
    req = request.get_data()
    print(req)
    return "ok"