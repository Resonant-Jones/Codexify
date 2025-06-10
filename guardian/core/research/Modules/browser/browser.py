from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

import time
import random

"""
    Browser class should provide every kinds of interation allow to model to choose which action to perform

    The purpose of browser is just to get the url for crawl_ai to get content
    
    Brower should have the follwoing methods 
    - Scroll Up 
    - Scrool Down 
    - Access specific link
    - Print Screen
    - Access to next page 
    - get text from the current web page []
    - switch tab [done , refactor need]
    - open multiple tab [done] 
    - next page [done] 
    - previous page [done]

"""


class Browser:
    GOOGLE_URL = "https://google.com/"
    ARXIV_URL = "https://arxiv.org/"
    GOOGLE_NEWS_URL = "https://news.google.com/"
    GOOGLE_SCHOLAR = "https://scholar.google.com"
    # maybe user can also self define some website

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def GoogleSearch(self, query: str):
        self.driver.get(Browser.GOOGLE_URL)
        search_bar = self.driver.find_element(By.ID, "APjFqb")
        search_bar.send_keys(query)
        time.sleep(1.5)  # avoid bot detection
        search_bar.send_keys(Keys.RETURN)
        time.sleep(3)
        res = self.get_search_content()
        # we have to use beautiful soup here

    def switch_tab(self, n: int):
        all_tabls = self._get_all_handler()
        self.driver.switch_to.window(all_tabls[n])

    def new_tab(self):
        self.driver.switch_to.new_window("tab")
        self.driver.get("https://google.com")  # default set to be google

    def next_page(self):
        time.sleep(random.random() * 3)
        self.driver.forward()

    def prev_page(self):
        time.sleep(random.random() * 3)  # one to three seconds random
        self.driver.back()

    def access_url(self, url):
        self.driver.get(url)

    def CloseDriver(self):
        self.driver.close()

    def _get_all_handler(self):
        # maybe we have to refactor here such that a map {description : tab name}
        all_handler = self.driver.window_handles
        return all_handler


if __name__ == "__main__":
    b = Browser()
    b.GoogleSearch("tesla")
    time.sleep(1)
    b.CloseDriver()
