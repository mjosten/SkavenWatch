"""
Functions to store and retrieve information about skaven_lists from a MongoDB docker container

Need to have environment variables to access the database
MONGO_HOST = mongodb
MONGO_INITDB_ROOT_USERNAME: ${MONGO_ROOT_USERNAME}
MONGO_INITDB_ROOT_PASSWORD: ${MONGO_ROOT_PASSWORD}

Steps to Test:
1. pull mongo docker image
    - `docker pull mongo`
2. Create docker network
    - `docker network create mongo-net`
3. start MongoDB Container
    - `docker run --name mongo-test \
        -d \
        -p 27017:27017 \
        --network mongo-net \
        -e MONGO_INITDB_ROOT_USERNAME=admin \
        -e MONGO_INITDB_ROOT_PASSWORD=adminpassword \
        mongo`
4. make sure that .env file has matching username and password enviornment variables
5. test with `python db_utils.py`

Steps to Run
`docker-compose build`
`docker-compose up`

@author: Michael Josten
"""
#imports
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
from typing import Any, Dict, List, Union
import pymongo
import os

from log_utils import setup_logger

load_dotenv()

#constants

MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = 27017
MONGO_USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD")

logger = setup_logger(__name__)

client = pymongo.MongoClient(f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}")


class SkavenDB():
    def __init__(self, client: pymongo.MongoClient = client, 
                 database_name: str = 'skaven_watch',
                 collection_name: str = 'skaven_collection',
                 date_check_collection: str = "date_check_collection") -> None:
        
        self.client = client
        self.db = self.client[database_name]
        self.collection = self.db[collection_name]        
        self.date_check_collection = self.db[date_check_collection]
        
        if not self.get_date_check():  # initialize date_check value if not exist
            self.update_date_check(str((datetime.now() - timedelta(1)).date()))  # default to yesterday
        
        
    def update_date_check(self, 
                          date_checked: str = str(date.today()), 
                          article_date: str = "") -> None:
        """
        Method that updates the date_checked in database
        
        :param date_checked: str of isoformat date 
        :param article_date: str of isoformat date of article
        """
        check_dict = {
            'id' : 1,
            'date_checked' : date_checked,
            'article_date' : article_date
        }
        self.date_check_collection.update_one(filter={'id': check_dict['id']},
                                              update={'$set': check_dict},
                                              upsert=True)
        
    def get_date_check(self) -> Union[Dict[str, str], None]:
        """
        Method that gets the date_checked from the database
        
        :return:
        {
            'date_checked': str in date isoformat,
            'article_date': str in date isoformat
        }
        """
        return self.date_check_collection.find_one({'id': 1})
        
        
    def change_db(self, db_name: str = 'skaven_watch', 
                  collection_name: str = 'skaven_collection'):
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def insert_skaven_dict(self, skaven_dict: Dict[str, Any]) -> bool:
        """
        Function that inserts a dictionary into a skaven_collection
        
        :param skaven_dict: 
        dict{
            'url': str
            'date': str,
            'lists': [{
                'player': str,
                'list': str
            }]
            'best_of_rest': [str]
        }
        :return bool: if insert was a success
        """
        inserted = self.collection.update_one(filter={'url': skaven_dict['url']},
                                              update={'$set': skaven_dict},
                                              upsert=True)
        return inserted.acknowledged
    
    def insert_skaven_lists(self, skaven_list: List[Dict[str, Any]]) -> bool:
        """
        Function that inserts list of dictionary into skaven_collection
        """
        result = []
        for el in skaven_list:
            result.append(self.insert_skaven_dict(el))
        return all(result)
    
    def find_skaven_list(self, query: Dict[str, Any]) -> Union[Dict[str, Any], None]:
        """
        function that finds a entry in skaven_collection
        
        ex: query = {'date': datetime.date(2023, 10, 25)}
        """
        logger.info(f"Querying DB with: {query}")
        result = self.collection.find_one(query)
        if result:
            logger.info("successfully retrived from DB")
            return result
        else:
            logger.warn("Query Failed")
            return None
        
    def find_most_recent_list(self) -> Union[Dict[str, Any], None]:
        return self.collection.find_one(sort=[('date', pymongo.DESCENDING)])
        
    def get_all_lists(self):  # returns a pymongo cursor type, similar to a list, but don't iterate
        return self.collection.find()
    
        
def test_connection():
    sk = SkavenDB(database_name='test', collection_name='test_coll')
    
    logger.info(f"Mongo Server Info: {sk.client.server_info()}")
    
    # insert a doc to be retrieved
    new_doc = {
        'name': "SkavenList",
        "description": "this is a test skaven list"
    }
    result_bool = sk.insert_skaven_dict(new_doc)
    
    if result_bool:
        print("success insert")
        result_doc = sk.find_skaven_list({'name': 'SkavenList'})
        if result_doc:
            from pprint import pprint
            print("success find")
            pprint(result_doc)
            
        else:
            print("failure find")
        
    else:
        print("fail insert")
    

if __name__ == "__main__":
    test_connection()
        