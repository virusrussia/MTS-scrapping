'''
Created on 6 февр. 2021 г.

@author: alex
'''
from bs4 import BeautifulSoup
from bs4 import element
import pandas as pd
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import re
import logging

logger = logging.getLogger(__name__)
fhandler = logging.FileHandler(filename='selen.log', mode='a')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fhandler.setFormatter(formatter)
logger.addHandler(fhandler)
logger.setLevel(logging.INFO)


def extractCites(driver, region):
    """
    Функция для считывания открытого списка городов
    :param driver: webdriver - текущий драйвер браузера
    :param region: str - текстовое название региона в котором
    находятся города
    :return citesDF: DataFrame - текущий список городов
    """

    citesDF = pd.DataFrame(columns={"Регион", "Город"})
    jsObj = BeautifulSoup(driver.page_source, features="lxml")
    # Находим на текущей странице блок со списком городов
    regions = jsObj.find("div", {"class": "mts16-popup-regions__scroll js-scroll-subregions"})

    # Находим все элементы с городами
    names = regions.findAll("a", {"class": "mts16-popup-regions__link"})
    for name in names:
        citesDF.loc[len(citesDF)] = {"Регион": region,
                                     "Город": name.get_text()}
    logger.info(f"Список городов для региона {region} получен")
    return citesDF


def showMoreClick(driver):
    """
    Функция, которая находит на текущей странице кнопки с текстом
    'Показать еще' и нажимает на них, пока они не исчезнут
    :param driver: webdriver - текущий драйвер браузера
    """

    # Параметр, показывающий что хотя бы раз была нажата кнопка
    q = 1

    sleep(2)
    while q:
        btn = driver.find_elements_by_tag_name("button")
        q = 0
        for i in btn:
            if i.text == "Показать ещё":
                ActionChains(driver).move_to_element(i).perform()
                i.click()
                q += 1
                # Ждем одну секунду, что бы страница обновилась и кнопка либо
                # исчезла, либо появилась снова
                sleep(1)


def tarifOptions(tarif):
    """
    Функция, которая считывает опции тарифа в тарифном блоке
    :param tarif: bs4.Tag - блок тарифа с текущей страницы
    :return options: list - список опций тарифа
    """
    options = []
    det = tarif.findAll("ul", {"class": ["tariff-card__plist-list", "b-list"]})
    for i in det:
        advantages = i.findAll("li")
        for j in advantages:
            """
            Опции имеют свое форматирвоание для красиового вывода на странице,
            в котором очень много пробельных символов и символов табуляции.
            Регулярным выражением заменяем любую последоватльность таких
            символов одиночным пробелом и затем удаляем лидирующие и
            заканчивающие пробелы.
            """
            options.append([re.sub(r"[\s]+", " ", j.text).strip()])
    return options


def tarifs(driver, city, region):
    """
    Функция, читающая все тарифы на текущей странице со всеми доступными
    опциями.
    :param driver: webdriver - текущий драйвер браузера
    :param city:s tr - название города действия читаемых тарифоы
    :param region: str - название региона города, для которого читаем тарифы
    :return df: DataFrame - считанные со старницы тарифы
    """

    df = pd.DataFrame(columns={"Название",
                               "Тип",
                               "Цена",
                               "Регион",
                               "Город",
                               "Описание",
                               "Опции"})

    jsObj = BeautifulSoup(driver.page_source, features="lxml")
    tarifslist = jsObj.findAll("div", {"class": "tariff-list__item"})

    for tarif in tarifslist:
        df.loc[len(df)] = {"Название":
                           tarif.find("a", {"class": "tariff-card__title"}).text,
                           "Описание":
                           tarif.find("div", {"class": "tariff-card__text"}).text if tarif.find("div", {"class": "tariff-card__text"}) else None,
                           "Тип":
                           tarif.find("div", {"class": "tariff-card__plist-title"}).text if tarif.find("div",{"class":"tariff-card__plist-title"}) else None,
                           "Опции":
                           tarifOptions(tarif),
                           "Цена":
                           tarif.find("div", {"class": ["tariff-card__price-item", "tariff-card__price-wrapper js-break-left"]}).text.split() if tarif.find("div",{"class":["tariff-card__price-item", "tariff-card__price-wrapper js-break-left"]}) else None,
                           "Регион":
                           region,
                           "Город":
                           city
                           }
    return df


def regionsMenuOpen(driver):
    """
    Функция для открытия меню с регионами и городами
    :param driver: webdriver - текущий драйвер браузера
    """
    # Находим меню с регионами и городами и кликаем по нему
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "js-user-region-title")))
    elem = driver.find_elements(By.CLASS_NAME, "js-user-region-title")
    for i in elem:
        if i.get_attribute("class") == "header__top-text js-user-region-title":
            ActionChains(driver).move_to_element(i).click(i).perform()
            logger.info("Открыли меню с регионами")
            break
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "mts16-popup-regions__scroll-padding")))


def regionsMenuClose(driver):
    """
    Функция для закрытия меню с регионами и городами
    :param driver: webdriver - текущий драйвер браузера
    """
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "mts16-popup__close")))
    elem = driver.find_element(By.CLASS_NAME, "mts16-popup__close")
    ActionChains(driver).move_to_element(elem).click(elem).perform()
    logging.info("Закрыли меню с регионами")


def regionsMenuClick(driver, region, class_name):
    """
    Функция для открытия списка городов конретного региона в меню
    :param driver: webdriver - текущий драйвер браузера
    :param region: str - название региона, города которого нужно открыть
    :param class_name: str - HTML класс пункта меню региона в меню
    """
    elem = driver.find_elements(By.CLASS_NAME,
                                class_name)
    for reg in elem:
        if reg.get_attribute("innerText") == region:
            ActionChains(driver).move_to_element(reg).click(reg).perform()
            logger.info(f"Кликнули на регион {region}")
            break
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "mts16-popup-regions__scroll-padding")))
    # Для уменьшения нагрузки на сервер
    sleep(2)


