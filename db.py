from pymongo import MongoClient
from utils import env


def get_database():
    """
    Setups MONGODB connection
    :return: MongoClient
    """
    client = MongoClient(env['MONGODB_URL'])
    return client['notion-bot']
