from utils import env
from db import get_database
import urllib.parse
from pymongo.collection import Collection
from bson.objectid import ObjectId
import requests
from base64 import b64encode
from typing import Union
from notion_api import NotionAPI

db = get_database()

users = db["users"]
pages = db["pages"]
flashcards = db["flashcards"]


class User:
    redirect_uri = f"http://localhost:3000/notion_auth"

    def __init__(self, user: Collection):
        self._model = user

        try:
            self.notion = NotionAPI(user["access_token"], user["_id"])
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

    def add_page(self, page_id: str) -> bool:
        result = pages.find_one({"page_id": page_id, "user": self._model["_id"]})
        if result:
            return False
        page = self.notion.page().retrieve(page_id)
        pages.insert_one({
            "page_id": page_id,
            "user": self._model["_id"],
            "title": page.get_title(),
        })
        self.load_flashcards(page_id)
        return True

    def get_pages(self, page_number, per_page=5):
        skip = (page_number - 1) * per_page if page_number > 0 else 0
        return pages.find({"user": self._model["_id"]}).skip(skip).limit(per_page)

    def load_flashcards(self, page_id):
        block = self.notion.block().retrieve(page_id)
        flashcards_data = block.parse_flashcards()
        flashcards_data_dicts = list(map(lambda i: i.__dict__, flashcards_data))
        flashcards.insert(flashcards_data_dicts)

    def reload_flashcards(self, page_id):
        # TODO: адекватно переписати функцію
        available_flashcards = flashcards.find({"page_id": page_id})
        if available_flashcards.count() < 1:
            return self.load_flashcards(page_id)
        block = self.notion.block().retrieve(page_id)
        flashcards_data = block.parse_flashcards()
        # flashcards_data_dicts = list(map(lambda i: i.__dict__, flashcards_data))\
        flashcards_data_dict = {}
        for i in flashcards_data:
            flashcards_data_dict[i.block_id] = i

        for i in available_flashcards:
            block_id = i["block_id"]
            updated_flashcard = flashcards_data_dict.get(block_id)
            if not updated_flashcard:
                flashcards.delete_one({"block_id": block_id})
                continue

            if i["front_side"] != updated_flashcard.front_side or \
                    i["back_side"] != updated_flashcard.back_side:
                flashcards.update_one({"block_id": block_id}, {"$set": updated_flashcard.__dict__})

        # flashcards.update_many({"user": self._model["_id"]}, flashcards_data_dict.values(), upsert=True)
        # flashcards.find

# @staticmethod
# def get_user_by_state_token(state_token):
#     return users.find_one({"state_tokens": {"$in": [state_token]}})
