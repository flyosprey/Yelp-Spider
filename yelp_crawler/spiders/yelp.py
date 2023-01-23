import json
import re
from json.decoder import JSONDecodeError
from urllib.parse import unquote
import scrapy
from scrapy.crawler import CrawlerProcess
from .init_file import get_search_params


class YelpSpider(scrapy.Spider):
    name = 'yelp'
    allowed_domains = ['yelp.com']
    start_urls = []

    def __init__(self, *args, **kwargs):
        self.all_params = get_search_params()
        self.start_urls.append(self.all_params["search_url"])
        super().__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(method="GET", url=url, headers=self.all_params["search_headers"], callback=self.parse)

    def parse(self, response, **kwargs):
        business_json = self._get_business_json(scrapy.Selector(response))
        business_datas = self._parse_business_json(business_json)
        for business_data in business_datas:
            details_url = f"https://www.yelp.com/biz/{business_data['resource_id']}/props"
            del business_data['resource_id']
            yield scrapy.Request(method="GET", url=details_url, headers=self.all_params["search_headers"],
                                 callback=self._parse_business_details, meta={"business_data": business_data})
        next_page_url = self._get_next_page_url(response.url, business_json)
        if next_page_url is not None:
            yield scrapy.Request(method="GET", url=next_page_url, headers=self.all_params["search_headers"],
                                 callback=self.parse)

    def _get_next_page_url(self, current_url, business_json) -> str or None:
        start_records = self._pagination(business_json)
        if start_records:
            next_page_url = re.sub(r"start=\d+", f"start={start_records}", current_url)
            return next_page_url
        return None

    @staticmethod
    def _pagination(business_json) -> int or None:
        props = business_json["legacyProps"]["searchAppProps"]["searchPageProps"]["mainContentComponentsListProps"]
        for prop in props:
            if prop.get("type", "") == "pagination":
                start, total = prop["props"]["startResult"], prop["props"]["totalResults"]
                results_per_page = prop["props"]["resultsPerPage"]
                if start < total < start + results_per_page:
                    start = total
                    return start
                elif start < total:
                    start += results_per_page
                    return start
                elif start >= total:
                    return None
                break
        return None

    def _parse_business_json(self, business_json) -> list:
        business_datas = []
        maps = business_json["legacyProps"]["searchAppProps"]["searchPageProps"]["rightRailProps"]["searchMapProps"]
        business_ids_list = self._get_marker_ids(maps)
        for business_ids in business_ids_list:
            business = maps["hovercardData"][business_ids["card_id"]]
            yelp_url = "https://www.yelp.com" + business['businessUrl']
            business_data = {"name": business["name"], "rating": business["rating"],
                             "resource_id": business_ids["resource_id"],
                             "number_of_reviews": business["numReviews"], "yelp_url": yelp_url}
            business_datas.append(business_data)
        return business_datas

    def _parse_business_details(self, response):
        business_data = response.meta["business_data"]
        details_json = self._get_details_json(response)
        business_data["business_url"] = self._get_business_url(details_json)
        business_data["reviews"] = self._get_reviews(details_json)
        if business_data["business_url"] is None:
            yield scrapy.Request(method="GET", url=business_data["yelp_url"], headers=self.all_params["search_headers"],
                                 callback=self._parse_business_url, meta={"business_data": business_data})
        else:
            yield business_data

    def _parse_business_url(self, response):
        business_data = response.meta["business_data"]
        url_raw = response.xpath(".//p[contains(text(), 'Business website')]/following-sibling::p/a/@href").get()
        business_data["business_url"] = self._normalize_business_url(url_raw)
        if not business_data["business_url"]:
            business_data["business_url"] = "The business has not personal website"
        yield business_data

    @staticmethod
    def _get_details_json(response) -> dict:
        if response.text:
            details_json = json.loads(response.text)
            return details_json
        raise Exception("We don't get details JSON")

    @staticmethod
    def _get_reviews(reviews_json) -> list:
        reviews = []
        reviews_obj = reviews_json["bizDetailsPageProps"]["reviewFeedQueryProps"]["reviews"]
        reviews_number = len(reviews_obj)
        reviews_number = 5 if reviews_number > 5 else reviews_number
        for index in range(0, reviews_number):
            reviewer = reviews_obj[index]["user"]["markupDisplayName"]
            reviewer_location = reviews_obj[index]["user"]["displayLocation"]
            review_date = reviews_obj[index]["localizedDate"]
            reviews.append({"reviewer": reviewer, "reviewer_location": reviewer_location, "review_date": review_date})
        return reviews

    @staticmethod
    def _get_reviews_json(response) -> dict:
        reviews_json_raw = response.xpath(".//script[contains(text(), 'review')]/text()").get()
        if reviews_json_raw:
            reviews_json = json.loads(reviews_json_raw)
            return reviews_json
        raise Exception("Failed to extract review json")

    def _get_business_url(self, details_json) -> str or None:
        business_url = None
        portfolio_props = details_json["bizDetailsPageProps"]["bizPortfolioProps"]
        if portfolio_props:
            business_url_raw = portfolio_props.get("ctaProps", {}).get("website", "")
            business_url = self._normalize_business_url(business_url_raw)
        return business_url

    @staticmethod
    def _normalize_business_url(business_url_raw) -> str or None:
        if business_url_raw:
            business_url = re.search(r"url=(.+?)&", business_url_raw)
            if business_url:
                return unquote(business_url[1])
        return None

    @staticmethod
    def _get_marker_ids(maps) -> list:
        markers = maps["mapState"]["markers"]
        business_ids_list = []
        for marker in markers:
            if "hovercardId" in marker.keys():
                business_ids_list.append({"card_id": marker["hovercardId"], "resource_id": marker["resourceId"]})
        return business_ids_list

    @staticmethod
    def _get_business_json(selector) -> dict:
        site_id = selector.re("data-hypernova-id=\"(.+?)\"")
        if site_id:
            json_raw = selector.xpath(f".//script[@data-hypernova-id='{site_id[0]}']//text()").get()
            if json_raw:
                try:
                    json_raw = json_raw.replace("<!--", "").replace("-->", "")
                    business_json = json.loads(json_raw)
                    return business_json
                except JSONDecodeError:
                    raise ValueError("ERROR: Wrong JSON syntax in 'json_raw' variable")
            raise Exception("Failed to extract business json!")
        raise Exception("There is no data-hypernova-id!")


if __name__ == "__main__":
    PROCESS = CrawlerProcess()
    PROCESS.crawl(YelpSpider)
    PROCESS.start()
