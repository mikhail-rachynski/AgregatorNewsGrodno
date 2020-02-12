import requests
from bs4 import BeautifulSoup
import re
import tageditor
import db
import os
import bot
import threading
from time import sleep
import logging

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',}

class HTMLfromSite():
    """Инициализирует экземпляр BeautifulSoup и передаёт страницу с 
    HTML-кодом из полученного URL
    """
    def __init__(self, url):
        self.url = url
        self.page = requests.get(self.url, headers=headers)
        self.soup = BeautifulSoup(self.page.text, 'html.parser')


class ScraperData:
    """Патерн для поиска и получения ссылок на последнюю новость.
    Получает HTML-код и сокращённое имя, с помощью которого и выбирается
    метод скрапинга.    
    """
    def scrap_page(self, page_for_scraping, site, site_name):
        scraper = self.get_site_scraper(site)
        return scraper(page_for_scraping)

    def get_site_scraper(self, site):
        if site == 's13':
            return self._scraper_s13
        elif site == 'newgrodno':
            return self._scraper_newgrodno
        elif site == 'grodnonews':
            return self._scraper_grodnonews
        elif site == 'vgr':
            return self._scraper_vgr
        elif site == 'life':
            return self._scraper_life
        elif site == 'plus':
            return self._scraper_plus
        else:
            raise ValueError(site)

    def _scraper_s13(self, page_for_scraping):     
        last_news = page_for_scraping.soup.find_all(class_="first display-none")[1]
        return page_for_scraping.url + last_news.a["href"]

    def _scraper_newgrodno(self, page_for_scraping):       
        last_news = page_for_scraping.soup.find_all(class_="all-over-thumb-link")[0]["href"]
        return last_news

    def _scraper_grodnonews(self, page_for_scraping):      
        last_news = page_for_scraping.soup.find_all(class_="new-single")[0]
        return page_for_scraping.url[0:20] + last_news.a["href"]

    def _scraper_vgr(self, page_for_scraping):    
        last_news = page_for_scraping.soup.find_all(class_="entry-title edgtf-post-title")[0]
        return last_news.a["href"]

    def _scraper_life(self, page_for_scraping):    
        last_news = page_for_scraping.soup.find_all(class_="nano-content")[0]
        return last_news.a["href"]

    def _scraper_plus(self, page_for_scraping):    
        last_news = page_for_scraping.soup.find(class_="allmode-title").a["href"]
        return page_for_scraping.url + last_news


class NewsPage(ScraperData):
    """Наследуемый класс от ScraperData. 
    Получает HTML-код страницы и ещет текст с новостью. Записывает
    в базу данных URL сайта, название, заголовок новости и отчищенный
    текст новости.
    """
    def scrap_page(self, page_for_scraping, site, site_name):
        scraper = self.get_site_scraper(site)
        return scraper(page_for_scraping, site_name)

    def scraper_decorator(func):
        def wrapper(self, page_for_scraping, site_name):
            news = []
            news.append(site_name)
            news.append(tageditor.cleaning_title
                    (page_for_scraping.soup.title))
            news.append(func(page_for_scraping, site_name))
            news.append("")
            news.append(page_for_scraping.url)
            db.send_news_to_database(news)
            bot.send_news(db.request_news_by_url
                    (page_for_scraping.url).id)
        return wrapper

    @scraper_decorator
    def _scraper_s13(page_for_scraping, site_name):
        return tageditor.cleaning_content(page_for_scraping.soup.p)
    
    @scraper_decorator
    def _scraper_newgrodno(page_for_scraping, site_name):        
        news_find_p = tageditor.cleaning_content(page_for_scraping.soup.find(class_="entry-content entry clearfix").find_all("p"))
        news_find_div = tageditor.cleaning_content(page_for_scraping.soup.find(class_="entry-content entry clearfix").find_all("div"))                        
        if len(str(news_find_p)) > 0:
            return news_find_p
        else:
            return news_find_div

    @scraper_decorator
    def _scraper_grodnonews(page_for_scraping, site_name):
        return tageditor.cleaning_content(page_for_scraping.soup.find
            (class_="post-content"))

    @scraper_decorator
    def _scraper_vgr(page_for_scraping, site_name):
        return tageditor.cleaning_content(page_for_scraping.soup.find
            (class_="edgtf-post-content").find_all("p"))
    
    @scraper_decorator    
    def _scraper_life(page_for_scraping, site_name):            
        return tageditor.cleaning_content(page_for_scraping.soup.find
            (class_="post-content description cf entry-content has-share-float content-normal"))

    @scraper_decorator
    def _scraper_plus(page_for_scraping, site_name):
        return tageditor.cleaning_content(page_for_scraping.soup.find
            (class_="itemBody").find_all("p"))


def scrap_site(url, site_abbreviation, site_name):
    """
    """
    get_latest_news_url = ScraperData()
    get_news_page = NewsPage()

    try:
        page_latest_news = HTMLfromSite(url)
        page_full_news = HTMLfromSite(get_latest_news_url.scrap_page
                                    (page_latest_news, 
                                    site_abbreviation, 
                                    site_name))
        if db.request_news_by_url(page_full_news.url) == None:        
            get_news_page.scrap_page(page_full_news, 
                                    site_abbreviation, 
                                    site_name)  
    except Exception as err:
        print(err)
        

def main():
    """Циклический вызов функций срапинга сайтов.
    Принимает время в секундах, через которое происходит скрапинг
    """
    while True:
        scrap_site("http://s13.ru", 
                    "s13", 
                    "Блог Гродно s13")
        scrap_site("http://newgrodno.by", 
                    "newgrodno", 
                    "NewGrodno.By")
        scrap_site("http://grodnonews.by/news/", 
                    "grodnonews", 
                    "Гродненская правда")
        scrap_site("http://vgr.by/gazeta/", 
                    "vgr", 
                    "Вечерний Гродно")
        scrap_site("http://ru.hrodna.life/", 
                    "life", 
                    "Hrodna.life")
        scrap_site("https://grodnoplustv.by", 
                    "plus", 
                    "Гродно Плюс")
        sleep(60)

    
if __name__ == '__main__':
    # Инициализация потоков
    t1 = threading.Thread(target=main, args=())
    t2 = threading.Thread(target=bot.bot.polling, args=())
    # Запуск потоков
    t1.start()
    t2.start()   
