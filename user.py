from datetime import datetime
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
        count = pages.find().count()
        if result or count >= 5:
            return False
        page = self.notion.page().retrieve(page_id)
        pages.insert_one({
            "page_id": page_id,
            "user": self._model["_id"],
            "title": page.get_title(),
        })
        self.reload_flashcards(page_id)
        return True

    def get_pages(self, page_number, per_page=5):
        skip = (page_number - 1) * per_page if page_number > 0 else 0
        return pages.find({"user": self._model["_id"]}).skip(skip).limit(per_page).sort("updatedAt", direction=-1)

    def reload_flashcards(self, page_id):
        result = pages.update_one({"page_id": page_id}, {"$set": {"updatedAt": datetime.now()}})
        if result.matched_count == 0:
            return False

        block = self.notion.block().retrieve(page_id)
        retrieved_flashcards = block.parse_flashcards()

        available_flashcards = flashcards.find({"page_id": page_id})
        available_flashcards_dict = {}
        for i in available_flashcards:
            available_flashcards_dict[i["block_id"]] = i

        to_insert = []
        for retrieved_flashcard in retrieved_flashcards:
            block_id = retrieved_flashcard.block_id

            flashcard_exists = available_flashcards_dict.get(block_id)
            if not flashcard_exists:
                retrieved_flashcard.createdAt = datetime.now()
                to_insert.append(retrieved_flashcard.__dict__)
                continue
            del available_flashcards_dict[block_id]

            if flashcard_exists["front_side"] != retrieved_flashcard.front_side or \
                    flashcard_exists["back_side"] != retrieved_flashcard.back_side:
                retrieved_flashcard.editedAt = datetime.now()
                flashcards.update_one({"block_id": block_id}, {"$set": retrieved_flashcard.__dict__, })

        if len(to_insert) > 0:
            flashcards.insert(to_insert)
        to_delete = list(map(lambda i: i["block_id"], available_flashcards_dict.values()))
        if len(to_delete) > 0:
            flashcards.delete_many({"block_id": {"$in": to_delete}})

        return True
