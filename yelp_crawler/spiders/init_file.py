import json
import re
from json.decoder import JSONDecodeError
from urllib.parse import quote
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem


REQUIRED_PARAMS_FILE_PATH = "yelp_crawler/spiders/required_params.json"


def get_search_params() -> dict:
    headers = _get_search_headers()
    url = _get_search_url()
    search_params = {"search_headers": headers, "search_url": url}
    return search_params


def _get_search_url() -> str:
    required_params = _get_required_params()
    category = quote(required_params["category"].capitalize())
    location = quote(required_params["location"])
    url = f"https://www.yelp.com/search?find_desc={category}&find_loc={location}&start=0"
    return url


def _get_required_params() -> dict:
    try:
        with open(REQUIRED_PARAMS_FILE_PATH, "r") as file:
            required_params = json.load(file)
            return required_params
    except FileNotFoundError:
        raise FileNotFoundError("ERROR: Need to create required_params.json file!")
    except JSONDecodeError:
        raise ValueError("ERROR: Wrong JSON syntax in required_params.json!")


def _get_search_headers() -> dict:
    user_agent, chrome_version = _get_random_user_agent()
    headers = {
        'authority': 'www.yelp.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'accept-language': 'en-US,en;q=0.9,es-US;q=0.8,es;q=0.7,ru-RU;q=0.6,ru;q=0.5,uk-UA;q=0.4,uk;q=0.3',
        'cache-control': 'max-age=0',
        'referer': 'https://www.yelp.com/',
        'sec-ch-ua': f'"Not_A Brand";v="99", "Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': user_agent
    }
    return headers


def _get_random_user_agent() -> (str, str):
    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)
    # It is not the best way, however in some very few cases we receive user_agent without version of chrome
    for limit in range(11):
        user_agent = user_agent_rotator.get_random_user_agent()
        chrome_version = re.search(r"Chrome/(\d+)?\.", user_agent)
        chrome_version = chrome_version[1] if chrome_version else chrome_version
        if chrome_version:
            return user_agent, chrome_version
    raise Exception("ERROR: Set better user agent!")
