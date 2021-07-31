import requests
from dataclasses import dataclass
from datetime import datetime
from bson.objectid import ObjectId
from typing import List, Union


@dataclass
class Flashcard:
    page_id: str
    block_id: str
    front_side: str
    back_side: str

    user: ObjectId


    def __hash__(self):
        return self.front_side


class NotionAPI:
    api_url = "https://api.notion.com/v1/"

    def __init__(self, access_token, *args):
        self.access_token = access_token
        self.args = args

    def page(self):
        return Page(self.access_token, self.api_url, *self.args)

    def block(self):
        return Block(self.access_token, self.api_url, *self.args)


class ApiHandler:

    def __init__(self, access_token, url, user_id):
        self.url = url
        self.access_token = access_token
        self.user_id = user_id

    def _make_request(self, method: str, url, **kwargs) -> dict:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Notion-Version": "2021-05-13"
        }
        res = requests.request(method, url, headers=headers, **kwargs)
        return res.json()

    def retrieve(self, item_id: str):
        response = self._make_request("GET", f"{self.url}/{item_id}")
        self.content = response
        return self

    def create(self, parent_id: str, properties: dict, **kwargs):
        body = {
            "parent": parent_id,
            **properties,
            **kwargs
        }
        return self._make_request("POST", self.url, data=body)

    def update(self, item_id, args):
        body = {
            "page_id": item_id,
            **args
        }
        response = self._make_request("PATCH", f"{self.url}/{item_id}", data=body)
        self.content = response
        return response


class Page(ApiHandler):

    def __init__(self, *args):
        super().__init__(*args)
        self.url += "pages"

    def get_title(self) -> str:
        return self.content["properties"]["title"]["title"][0]["text"]["content"]


class Block(ApiHandler):
    flashcard_smile = "🧩"

    def __init__(self, *args):
        super(Block, self).__init__(*args)
        self.url += "blocks"

    def retrieve(self, item_id: str):
        self.page_id = item_id
        response = self._make_request("GET", f"{self.url}/{item_id}/children")
        self.content = response
        return self

    @staticmethod
    def __parse_bulleted_item(item, user_id, page_id) -> Union[Flashcard, None]:
        block_text = item["bulleted_list_item"]["text"][0]["plain_text"]
        if not Block.flashcard_smile in block_text:
            return None
        front_side, back_side = block_text.strip().split("::")
        return Flashcard(page_id, item["id"], front_side, back_side, user_id, )

    def parse_flashcards(self) -> List[Flashcard]:
        children = self.content["results"]
        flashcards = []
        parse_options = {
            'bulleted_list_item': self.__parse_bulleted_item
        }
        for block in children:
            if parse_option := parse_options.get(block["type"]):
                flashcard = parse_option(block, self.user_id, self.page_id)
                if flashcard:
                    flashcards.append(flashcard)

        return flashcards
