import requests
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Flashcard:
    front_side: str
    back_side: str

    coefficient: int = 0
    createdAt: int = datetime.now()

    def __hash__(self):
        return self.front_side


class NotionAPI:
    api_url = "https://api.notion.com/v1/"

    def __init__(self, access_token):
        self.access_token = access_token

    def page(self):
        return Page(self.access_token, self.api_url)

    def block(self):
        return Block(self.access_token, self.api_url)


class ApiHandler:

    def __init__(self, access_token, url):
        self.url = url
        self.access_token = access_token

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
        self.url = self.url + "pages"

    def get_title(self) -> str:
        return self.content["properties"]["title"]["title"][0]["text"]["content"]


class Block(ApiHandler):

    def __init__(self, *args):
        super(Block, self).__init__(*args)
        self.url = self.url + "blocks"

    def retrieve(self, item_id: str):
        response = self._make_request("GET", f"{self.url}/{item_id}/children")
        self.content = response
        return self

    @staticmethod
    def __parse_bulleted_item(item):
        block_text = item["bulleted_list_item"]["text"][0]["plain_text"]
        front_side, back_side = block_text.strip().split("::")
        return Flashcard(front_side, back_side)

    def parse_flashcards(self):
        children = self.content["results"]
        flashcards = []
        parse_options = {
            'bulleted_list_item': self.__parse_bulleted_item
        }
        for block in children:
            if parse_option := parse_options.get(block["type"]):
                flashcards.append(parse_option(block).__dict__)

        return flashcards
