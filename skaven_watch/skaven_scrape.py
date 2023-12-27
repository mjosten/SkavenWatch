"""
find_skaven_list.py

This file will have functionality for webscraping goonhammer.com and finding skaven lists in their 'competative innovations' articles.

@author: Michael Josten
"""

# imports
import re
import time
import requests
from typing import Any, Dict, List, Union

from datetime import datetime, timedelta, date
from bs4 import BeautifulSoup
from log_utils import setup_logger
from db_utils import SkavenDB

logger = setup_logger(__name__)
skaven_db = SkavenDB()

# Constants
URL = 'https://www.goonhammer.com/category/columns/aos-competitive-innovations/'
URL_PATTERN = re.compile(r".*competitive-innovations.*", re.IGNORECASE)
RAT_PATTERN = re.compile(r".*skaven(?!brew).*", re.IGNORECASE)
IGNORE_PATTERN = re.compile(r".*skaven victory.*", re.IGNORECASE)
STOP_PATTERN = re.compile(r".*total.*", re.IGNORECASE)


def get_current_article_link(url=URL):
    """
    Function that will get a link to the most recent article of the aos competitive innovations.

    Will only return if the article is from yesterdays date.
    Looks like the articles come out at 14UTC, so need to run after that if want the most up to date article

    returns: str, url of most recent article
    """
    site_response = requests.get(url)
    if site_response.status_code == 200:
        logger.info("Getting current article link")
        # parse the HTML content using beautiful soup
        soup = BeautifulSoup(site_response.text, 'html.parser')

        # find something called td_module_mx5
        # goonhammer dynamically adjusts with new articles, so unsure if this
        # is sustainable
        div_elements = soup.find_all('div', class_='td_module_mx5')

        # get the container of the url
        container_soup = div_elements[0]

        # get url to competitive innovations article
        link = container_soup.find('a', href=URL_PATTERN)['href']

        return link
    
    else:
        logger.error(f"Site response error: {site_response.status_code}")
        raise requests.HTTPError
    
    

def get_all_article_links(url: str = URL):
    """
    Function that searches for all competitive innovation articles that are more recent than the time_limit
    
    :param url [optional]: str that is the URL to search for article links
    :param time_limit [optional] [defaults->timedelta(weeks=3)]: timedelta object
    :return: dict[date, str] of date -> url
    """
    site_response = requests.get(url)
    if site_response.status_code == 200:
        logger.info("Getting all article links")
        # parse HTML content using soup
        soup = BeautifulSoup(site_response.text, 'html.parser')
        
        # find all href tags with 
        href_soup = soup.find_all('a', class_=False, href=URL_PATTERN)
        
        # look for hrefs with parent of 'h3'
        result = []
        for el in href_soup:
            if el.parent.name == 'h3':
                result.append(el['href'])
        
        logger.info(f"found {len(result)} article links")
        return result
    
    else:
        logger.error(f"Site response error: {site_response.status_code}")
        raise requests.HTTPError


def get_article_date(url):
    """
    Helper function that gets the date of the article with the url
    
    :param url: str of url
    :return datetime.date object
    """
    site_response = requests.get(url)
    
    if site_response.status_code == 200:
        soup = BeautifulSoup(site_response.text, 'html.parser')
        article_date = _find_article_date(soup)
        return article_date
        
    else:
        logger.error(f"Site response error: {site_response.status_code}")
        raise requests.HTTPError
    
    
def _find_article_date(soup):
    """
    helper function that finds the date of the article with the soup object 
    
    :param soup: BeautifulSoup object of article
    :return datetime.date object
    """
    # get date of article
    date_soup = soup.find_all('time', class_='entry-date')
    # list comprehension to get the datetime value if the parent is of 'tdb-block-innter' class
    datetime_val = [datetime_el['datetime'] for datetime_el, parent_el in zip(date_soup, date_soup) if parent_el.find_parent('div', class_='tdb-block-inner')][0]
    article_date = datetime.fromisoformat(datetime_val).date()
    return article_date


def _get_skaven_list(p, stop_pattern):
    """
    function that will use 'p' as a starting paragraph,
    iterate through next paragraphs until the word "total" is read.

    Then append all the strings to the list and return
    """
    result = []
    while p:
        for s in p.get_text().split('\n'):  # split paragraph into sentences
            if s.startswith('–'):  # add tab if sentence starts with '-' for readability
                s = '\t' + s
            if re.match(r".*click to.*", s, re.IGNORECASE):  # dont add this sentence to the result
                continue
            result.append(s)

        if re.search(stop_pattern, p.get_text()):  # stop loop once we find the stop word
            break

        p = p.find_next('p')

    return result


def _compile_skaven_results(
    url,
    rat_pattern=RAT_PATTERN,
    stop_pattern=STOP_PATTERN,
    add_to_db: bool = True) -> Dict[str, Any]:
    """
    Function that takes in a url to competitive-innovations and finds 
    all the skaven lists that are found in the article

    returns: dict{
        'url': str
        'date': date,
        'lists': [{
            'name': str,
            'list': str
        }]
        'best_of_rest': [str]
    }
    """
    result = {}

    site_response = requests.get(url)
    
    if site_response.status_code == 200:
        logger.info(f"Compiling Skaven results from {url}")
        
        result['url'] = url
        
        soup = BeautifulSoup(requests.get(url).text, 'html.parser')
        
        # get date of article
        article_date = _find_article_date(soup)
        result['date'] = str(article_date)
        
        # get all strings with 'skaven'
        skaven_strings = soup.find_all(string=rat_pattern)

        # get the top scoring skaven lists
        result['lists'] = []
        name_list = []
        list_list = []
        
        for ss in skaven_strings:
            if ss.parent.name == 'h2':  # hopefully this is the player name of the list
                name_list.append(ss)
            elif (ss.parent.name == 'p' or ss.parent.name == 'strong') and not IGNORE_PATTERN.match(ss) and len(ss.split(' ')) <= 12:  # hopefully the content of the list, dont want large paragraphs with the word skaven
                list_list.append(_get_skaven_list(ss.parent, stop_pattern))
                        
        # go through each list and try to get a name
        if len(name_list) > 0 and len(name_list) == len(list_list):  # if the article is of type 1: Ie, has each list separate, there will be a h2 with the name
            for n, l in zip(name_list, list_list):
                result['lists'].append({
                    'name': n,
                    'list': "\n".join(l)
                })
                
        # no name_list so that means that each list is headered by the player name   
        elif not name_list:
            for l in list_list:
                result['lists'].append({
                    'name': l[0],  # get name of player from first line
                    'list': "\n".join(l[1:])
                })
                
        elif len(name_list) != len(list_list):  # hopefully this never happens, otherwise there is a problem with the algorithm
            logger.warning("Something strange: number of names and number of lists is different. Examine logs")
            logger.warning("NameList Contents:")
            for n in name_list:
                logger.warning("------------")
                logger.warning(n)
            logger.warning("SkavenList Contents")
            for l in list_list:
                logger.warning("-------------")
                logger.warning(l)    
                
        logger.info(f"Found {len(result['lists'])} Skaven Lists")
        
        # collect the best of the rest skaven lists
        temp_result = []

        lists_soup = soup.find_all('ul', class_=False, id=False)
        for ul in lists_soup:
            for li in ul.find_all('li'):
                # stripped_strings conbines all strings from one object
                el = ' '.join(li.stripped_strings)
                if re.search(rat_pattern, el):  # if the element contains "skaven"
                    temp_result.append(el)

        # if there are any best of the rest skaven lists, add to the results
        logger.info(f"Found {len(temp_result)} Best of the Rest Lists")
        result['best_of_rest'] = temp_result
        
        #   - update the database
        if add_to_db:
            skaven_db.insert_skaven_dict(result)
            
        return result

    else:
        logger.error(f"Site response error: {site_response.status_code}")
        raise requests.HTTPError
    
    
def _format_skaven_message(skaven_dict: Dict[str, Any]):
    """
    Function that gives a formatted message about the article from the url
    
    :param skaven_dict: 
    dict{
        'url': str
        'date': str in isoformat,
        'lists': [{
            'player': str,
            'list': str
        }]
        'best_of_rest': [str]
    }
    
    :return: str of message
    
    """    
    logger.info(f"Formatting Skaven Message: {str(skaven_dict['date'])}")
    
    skaven_lists = skaven_dict['lists']  # dict[str, str]
    best_of_rest = skaven_dict['best_of_rest']  # [str]
    
    message = f"{skaven_dict['date']} Skaven Results:\n"
    message += f"{skaven_dict['url']}\n"
    
    # add the skaven lists
    if skaven_lists:
        message += f"Skaven Lists:\n\n"
        for i, d in enumerate(skaven_lists):
            message += f"List {i+1} - {d['name']}\n{d['list']}\n"
        
    # add best of the rest to the message
    if best_of_rest:
        message += "\nBest of the Rest:\n"
        for i, el in enumerate(best_of_rest):
            message += f"L{i+1} - {el}"
    
    # if no skaven at all   
    elif not (skaven_lists or best_of_rest):
        message += f"No Skaven Lists Today :("
        
    return message
        
        
def get_skaven_message_from_url(url) -> str:
    """
    Function that creates a skaven list message from the url of the article
    :param url: str
    :return: str of message
    """
    article_dict = skaven_db.find_skaven_list({'url': url})
    
    if article_dict:
        return _format_skaven_message(article_dict)
    else:
        # compile skaven results and format message
        article_dict = _compile_skaven_results(url)
        return _format_skaven_message(article_dict)
        
        
def get_current_skaven_message(debug=False) -> Union[str, None]:
    """
    Function that gets todays article and returns a message of the skaven lists found
    
    :param debug: bool if should return most recent article 
                instead of no article if there is no article today
    :return: str message or None
    """
    # check if there is an article in the db that came out today
    logger.info("getting current skaven list")
    logger.info("checking db...")
    today_date = date.today()
    skaven_dict = skaven_db.find_most_recent_list()
    message = None
    
    if skaven_dict:  # there exists a list in the db
        logger.info(f"found list in db: {skaven_dict['date']}")
        # check if the date of skaven_dict is today
        db_date = date.fromisoformat(skaven_dict['date'])
        if db_date == today_date:
            logger.info("DB list from today")
            # list is from today, can return message
            message =  _format_skaven_message(skaven_dict)
        
        # DB list is not from today
        # Check the date_checked object in the db to see if we need to query goonhammer
        else:
            date_checked = skaven_db.get_date_check()
            # check if goonhammer was already checked for a new article
            if (date_checked and (date.fromisoformat(date_checked['date_checked']) == today_date)) and not debug:
                # we already checked goonhammer and there is no new article so don't message anything
                logger.info(f"Already checked Goonhammer today, no new list: {str(today_date)}")
                message = None
            
            # we did not check goonhammer today yet for a new article
            else:
                # check goonhammer for new article
                logger.info("Checking goonhammer for new article")
                current_article_url = get_current_article_link()
                current_article_date = get_article_date(current_article_url)
                
                if (current_article_date == today_date) or debug:
                    # if article date is today, then we have a new article
                    # update db and send message
                    skaven_dict = _compile_skaven_results(current_article_url)
                    logger.info(f"Found new article from goonhammer, updating DB: {skaven_dict['url']}")
                    skaven_db.insert_skaven_dict(skaven_dict)
                    message = _format_skaven_message(skaven_dict)
                    
                else:
                    # no new article, don't do anything
                    logger.info("No new goonhammer article, updating checked status")
                    message = None
                 
                # update date_checked   
                skaven_db.update_date_check(str(today_date), str(current_article_date))
                
    else:  # there is no list in the DB
        logger.info("No lists in DB, querying goonhammer for recent list")
        # query goonhammer for a list and input into DB
        current_article_url = get_current_article_link()
        skaven_dict = _compile_skaven_results(current_article_url)  # this function adds to DB
        
        # check if it occured today and if yes then can message
        if (date.fromisoformat(skaven_dict['date']) == today_date) or debug:
            logger.info("Found article from today, messaging")
            message = _format_skaven_message(skaven_dict)
        else:
            # don't message
            logger.info("No list from today, no message")
            message = None
            
    return message  # str or None


def get_all_skaven_message(time_limit: timedelta = timedelta(weeks=9)) -> List[str]:
    """
    Function that gets all skaven messages from most recent to time_limit
    - side functionality is to populate the database
    
    :param time_limit: timedelta. amount of time back to get articles
    :return: List[str] of messages of skaven articles
    """
    current_date = datetime.now().date()
    threshold_date = current_date - time_limit
    logger.info(f"threshold date: {threshold_date}")
    result = []
    # get all articles 
    article_urls = get_all_article_links()
    for url in article_urls:
        # process each article
        article_date = get_article_date(url)
        logger.info(f"article_date: {article_date}")
        # check if article is less than time_limit
        if article_date >= threshold_date:
            result.append(get_skaven_message_from_url(url))
            time.sleep(2)  # need to sleep so we are not scraping too fast
        else:
            break  # we get the articles in order on the website
            # so it is a strong possibility that if a article is out of date, 
            # then the rest of the articles are out of date
    return result
        
    
if __name__ == "__main__":
    
    # url = 'https://www.goonhammer.com/competitive-innovations-in-the-mortal-realms-world-championships-of-warhammer-war-in-the-heartlands/'
    url = 'https://www.goonhammer.com/competitive-innovations-in-the-mortal-realms-shipping-up-to-boston/'
    
    result = _compile_skaven_results(url, add_to_db=False)
    message = _format_skaven_message(result)
    
    from pprint import pprint

    pprint(result)
    print("--------------")
    print(message)
    
    # simple test
    # result = get_current_article_link()
    # if result:
    #     (url, current) = result
    # else:
    #     print("Unable to get current article")
    #     exit(1)
    
    # print(f"Current Date Article: {current}")
    
    # print("----------")
    # result = compile_skaven_results(url)
    
    # for el in result:
    #     print(el)
    
    # result = compile_skaven_results('https://www.goonhammer.com/competitive-innovations-in-the-mortal-realms-no-mercy-from-namarti/')
    # compile_skaven_results('https://www.goonhammer.com/competitive-innovations-in-the-mortal-realms-there-must-be-something-in-the-water/')
    # compile_skaven_results('https://www.goonhammer.com/competitive-innovations-in-the-mortal-realms-calm-before-the-storm/')
    
    #------
    # Testing database by getting all skaven messages and populating the database, then retrieving
    # result = get_all_skaven_message()
    # logger.info(f"Got {len(result)} Skaven Messages")
    
    # logger.info("querying db now: ")
    # r = skaven_db.get_all_lists()
    # logger.info(f"found {len(list(r))} lists in DataBase")
        
    
   