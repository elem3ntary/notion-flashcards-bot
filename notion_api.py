import requests


class NotionAPI:
    api_url = "https://api.notion.com/v1/"

    def __init__(self, access_token):
        self.access_token = access_token

    def page(self):
        category_url = self.api_url + "pages/"
        return ApiHandler(self.access_token, category_url)


class ApiHandler:

    def __init__(self, access_token, url):
        self.url = url
        self.access_token = access_token

    def __make_request(self, method: str, url, **kwargs) -> dict:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Notion-Version": "2021-05-13"
        }
        res = requests.request(method, url, header=headers, **kwargs)
        return res.json()

    def retrieve(self, item_id: str):
        return self.__make_request("GET", f"{self.url}/{item_id}")

    def create(self, parent_id: str, properties: dict, **kwargs):
        body = {
            "parent": parent_id,
            **properties,
            **kwargs
        }
        return self.__make_request("POST", self.url, data=body)

    def update(self, item_id, args):
        body = {
            "page_id": item_id,
            **args
        }
        return self.__make_request("PATCH", f"{self.url}/{item_id}", data=body)
