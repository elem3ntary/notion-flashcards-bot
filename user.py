import utils
import requests

class User:

    def generate_login_url(self):
        return f"https://api.notion.com/v1/oauth/authorize?client_id={utils.env['NOTION_CLIENT_ID']}"
