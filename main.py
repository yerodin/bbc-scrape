#! /usr/bin/env python3
import logging
import re

import selenium.common.exceptions
from openpyxl import Workbook
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

bbc_link = 'https://www.bbc.com/'
timeout = 6

debug_type = ''
link_debug = ''


def main():
    logging.info('Starting Scraper - Setting Up WebDriver')
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    logging.log(1, 'Retrieving BBC links')
    links = scrape_bbc_links(driver)
    info = []
    for l in links:
        link = l[0]
        i = (link, 'N/A -  JUNK', 'N/A -  JUNK')
        if l[1] is True:
            while True:
                try:
                    i = get_bbc_info(driver, link)
                    break
                except selenium.common.exceptions.StaleElementReferenceException:
                    continue
        if i[0] is not None:
            info.append(i)
        print(i)
    logging.log(1, 'Saving Info')
    logging.warning('Saving Info - (switch to stream in future for large data set)')
    save_news(info)
    driver.close()


def scrape_bbc_links(driver):
    driver.get(bbc_link)
    WebDriverWait(driver, 10).until(ec.visibility_of_element_located((By.CLASS_NAME, "content")))
    links = []
    for h in driver.find_elements(by=By.XPATH, value='//*[@href]'):
        link = h.get_attribute('href')
        if link_debug == '' or (link_debug != '' and link_debug in link):
            links.append((link, verify_link(link)))
    links = list(dict.fromkeys(links))
    return links


def verify_link(link):
    split = link.split('/')
    end = split[len(split) - 1]
    if '.' not in end and 'bbc' in link:  # and \
        # (
        # 'news/' in link or 'sport/' in link or 'article/' in link or 'bespoke/' in link or 'reel/' in link or 'usingthebbc/' in link or 'programmes/' in link):
        return True
    return False


def get_bbc_info(driver, link):
    link_type = classify_link(link)
    if debug_type != '':
        if link_type != debug_type:
            return link, 'Debug SKIP', 'Debug SKIP'
    heading_info = link_heading_info(link_type)

    driver.get(link)
    t = timeout
    heading = ''
    tries = 1
    while True:
        try:
            WebDriverWait(driver, t).until(ec.visibility_of_element_located((heading_info[0], heading_info[1])))
            heading = driver.find_element(by=heading_info[0], value=heading_info[1]).text
            if heading == 'Accessibility links' or heading == '':
                raise Exception
            break
        except Exception as e:
            t = 1
            if tries == 5:
                break
            logging.warning("Couldn't find heading, trying again with generic header")
            heading_info = (By.TAG_NAME, 'h'+str(tries))
            tries = tries+1
    if heading == '' or heading == 'Accessibility links':
        try:
            heading = driver.find_element(by=By.XPATH, value="//div[contains(@class, 'title-')]").text
        except Exception:
            return link, 'Not Found', 'Not Found'

    body = 'Not Found - Body'
    if link_type == 'live':
        body = get_live_link_body(driver)
    elif link_type == 'article':
        body = get_article_link_body(driver)
    elif link_type == 'reel':
        body = get_reel_link_body(driver)
    elif link_type == 'disability-sport':
        body = get_disability_sport_link_body(driver)
    elif link_type == 'sport':
        body = get_sport_link_body(driver)
    else:
        body = get_news_link_body(driver)
    if body == '':
        body = get_generic_link_body(driver)
    while len(body) > 0 and (body[len(body) - 1] == '\n' or body[len(body) - 1] == ' '):
        body = body[:-1]

    return link, heading, body


def get_live_link_body(driver):
    body_elements = driver.find_elements(by=By.XPATH,
                                         value="//div[contains(@class, 'gel-body-copy') and contains(@class ,'qa-post-body')]")
    logging.debug('Finding Live Body Elements')
    body = ''
    for element in body_elements:
        body = body + '\n' + element.text
        if len(body) > 0 and body[0] == '\n':
            body = body[1:]
    return body


def get_generic_link_body(driver):
    body_elements = driver.find_elements(by=By.XPATH, value="//div[contains(@class, 'bbc-')]")
    if len(body_elements) == 0:
        body_elements = driver.find_elements(by=By.XPATH, value="//p")
    body = ''
    for element in body_elements:
        body = body + '\n' + element.text
    if len(body) > 0 and body[0] == '\n':
        body = body[1:]
    return body


def get_article_link_body(driver):
    body_elements = driver.find_elements(by=By.XPATH, value="//div[@class='article__body-content']")
    body = ''
    for element in body_elements:
        body = body + '\n' + element.text
    if len(body) > 0 and body[0] == '\n':
        body = body[1:]
    return body


def get_reel_link_body(driver):
    body_elements = driver.find_elements(by=By.XPATH,
                                         value="//div[contains(@class, 'Summary')]")
    body = ''
    for element in body_elements:
        body = body + '\n' + element.text
    if len(body) > 0 and body[0] == '\n':
        body = body[1:]
    return body


def get_sport_link_body(driver):
    body_elements = driver.find_elements(by=By.XPATH,
                                         value="//div[contains(@class, 'gel-pica') and contains(@class ,'qa-story-body')]")
    body = ''
    for element in body_elements:
        body = body + '\n' + element.text
    if len(body) > 0 and body[0] == '\n':
        body = body[1:]
    return body


def get_disability_sport_link_body(driver):
    body_elements = driver.find_elements(by=By.XPATH, value="//div[contains(@class, 'RichTextContainer')]")
    body = ''
    for element in body_elements:
        body = body + '\n' + element.text
    if len(body) > 0 and body[0] == '\n':
        body = body[1:]
    return body


def get_news_link_body(driver):
    body_elements = driver.find_elements(by=By.XPATH, value="//*[@data-component='text-block']")
    body = ''
    for element in body_elements:
        body = body + '\n' + element.text
    if len(body) == 0:
        body_elements = driver.find_elements(by=By.XPATH, value="//p[contains(@class, 'Paragraph')]")  # Paragraph
        for element in body_elements:
            body = body + '\n' + element.text
    if len(body) > 0 and body[0] == '\n':
        body = body[1:]
    return body


def classify_link(link):
    if 'live/' in link:
        return 'live'
    elif 'article/' in link:
        return 'article'
    elif 'reel/' in link:
        return 'reel'
    elif 'sport/' in link and 'disability-sport' in link:
        return 'disability-sport'
    elif 'sport/' in link:
        return 'sport'
    elif 'news/' in link:
        return 'news'
    else:
        return 'junk'


def link_heading_info(link_type):
    if link_type == 'live' or link_type == 'sport' or link_type == 'reel':
        return By.XPATH, '//h1'
    elif link_type == 'article':
        return By.XPATH, "//div[contains(@class, 'article-headline__text')]"
    else:
        return By.ID, 'main-heading'


def save_news(info):
    wb = Workbook()
    ws = wb.active
    ws.append(['Link', 'Heading', 'Information'])
    for i in info:
        try:
            ws.append([i[0], i[1], i[2]])
        except Exception as e:
            logging.warning('Exception saving link:' + i[0])
            logging.warning('heading:' + i[1])
            logging.warning('data:' + i[2])
            logging.warning(e)

    wb.save("output.xlsx")


if __name__ == '__main__':
    main()
