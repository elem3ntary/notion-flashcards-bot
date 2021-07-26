from utils import env
from db import get_database
import urllib.parse
from pymongo.collection import Collection
from bson.objectid import ObjectId
import requests
from base64 import b64encode
from typing import Union
from notion_api import NotionAPI
from uuid import uuid4 as uuid
from datetime import datetime
import pandas as pd

users = get_database()["users"]


class User:
    redirect_uri = f"http://localhost:3000/notion_auth"

    def __init__(self, user: Collection):
        # self._model = pd.DataFrame(list(user))
        self._model = user

        try:
            self.notion = NotionAPI(user["access_token"])
        except KeyError:
            pass

    @staticmethod
    def from_id(_id: str) -> Union["User", None]:
        user = users.find_one({"_id": ObjectId(_id)})
        if not user:
            return None

        return User(user)

    @staticmethod
    def from_telegram_credentials(from_user):
        user_id = from_user.id
        first_name = from_user.first_name
        user = users.find_one({"user_id": user_id})
        if not user:
            user = User.register(user_id, first_name)
        return User(user)

    @staticmethod
    def register(user_id, first_name):
        return users.insert_one({"user_id": user_id, "first_name": first_name})

    # def gen_state_token(self) -> str:
    #     """
    #     Generates a token that is used to identify user authorization attempt
    #     """
    #     token = str(uuid())
    #     state_token = {
    #         "token": token,
    #         "createdAt": str(datetime.now())
    #     }
    #     users.update_one({"_id": self.user["_id"]}, {"$push": {"state_tokens": state_token}})
    #     return token

    def generate_login_url(self):
        args = {
            "client_id": env['NOTION_CLIENT_ID'],
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": str(self._model["_id"])

        }
        url = "https://api.notion.com/v1/oauth/authorize?"
        return url + urllib.parse.urlencode(args)

    def fetch_access_token(self, code: str) -> Union[dict, None]:
        url = "https://api.notion.com/v1/oauth/token"
        auth_token = f"{env['NOTION_CLIENT_ID']}:{env['NOTION_CLIENT_SECRET']}".encode("ascii")
        encoded_token = b64encode(auth_token).decode('ascii')
        print(encoded_token)
        json_res = requests.post(url, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }, headers={
            "Authorization": f"Basic {encoded_token}"
        })
        res: dict = json_res.json()
        if res.get("error"):
            return None

        users.update_one({"_id": self._model["_id"]}, {"$set": res})

        return res

    def is_logged_in_notion(self) -> bool:
        return bool(self._model.get("access_token", None))

    def model_db_id(self) -> dict:
        return {"_id": self._model["_id"]}

    def add_page(self, page_id: str):
        users.update_one(self.model_db_id(), {"$addToSet": {"pages": page_id}})
        self.notion.page

        # @staticmethod
        # def get_user_by_state_token(state_token):
        #     return users.find_one({"state_tokens": {"$in": [state_token]}})
