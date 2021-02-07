from MTS import *

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup
from bs4 import element
import pandas as pd
import json
import re
from time import sleep

import logging

logger = logging.getLogger(__name__)
fhandler = logging.FileHandler(filename='selen.log', mode='a')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fhandler.setFormatter(formatter)
logger.addHandler(fhandler)
logger.setLevel(logging.INFO)

# Данные по регионам
regionsDF = pd.DataFrame(columns={"Регион", "class"})
# cites - сюда сохраняются все города
cities = pd.DataFrame()
# Данные по всем тарифам
df = pd.DataFrame(columns={"Название",
                           "Тип",
                           "Цена",
                           "Регион",
                           "Город",
                           "Описание",
                           "Опции"})

# Открываем браузер
driver = webdriver.Chrome(executable_path="/Applications/chromedriver")
driver.get("https://mts.ru/personal/mobilnaya-svyaz/tarifi/vse-tarifi")

# Открываем меню с регионами и городами
regionsMenuOpen(driver)

# Получаем список всех регионов, для того что бы потом
# по ним пройтись, открыть все города и посмотреть тарифы
jsObj = BeautifulSoup(driver.page_source, features="lxml")
regions = jsObj.findAll("div", {"class": "mts16-popup-regions__group"})
for i in regions:
    names = i.findAll("a", {"class": ["mts16-popup-regions__link mts16-popup-regions__subregions-opener",
                                      "mts16-popup-regions__link mts16-popup-regions__subregions-opener is-active"]})
    for name in names:
        regionsDF.loc[len(regionsDF)] = {"Регион": name.get_text(),
                                         "class": name.attrs["class"][0]}
logger.info(f"Список регионов получен.\n {regionsDF}")

# Теперь у нас есть список регинов. Обновляем страницу
# и начинаем обходить все регионы и города
driver.refresh()
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "js-user-region-title")))

try:
    for region in range(3):#range(len(regionsDF)):
        regionsMenuOpen(driver)

        # Находим регион в отктытом меню для обработки и кликаем на него
        regionsMenuClick(driver, regionsDF.loc[region]["Регион"], regionsDF.loc[region]['class'])
        cities = pd.concat([cities, extractCites(driver,
                                                 regionsDF.loc[region]["Регион"])],
                            ignore_index=True)
        logger.info(f'Города в регионе:\n {cities[cities["Регион"]==regionsDF.loc[region]["Регион"]]}')
        regionsMenuClose(driver)

        # Перебираем все города в регионе и для каждого смотрим тарифы
        for i in range(len(cities[cities["Регион"] == regionsDF.loc[region]["Регион"]])):

            regionsMenuOpen(driver)
            regionsMenuClick(driver, regionsDF.loc[region]["Регион"],
                             regionsDF.loc[region]['class'])

            citesWebDriver = driver.find_elements(By.CLASS_NAME,
                                                  "mts16-popup-regions__link")
            for j in citesWebDriver:
                city = cities[cities["Регион"] == regionsDF["Регион"].loc[region]]["Город"].values[i]
                if j.get_attribute("innerText") == city:
                    logger.info(f'Изучаем город: {city}')
                    ActionChains(driver).move_to_element(j).click(j).perform()
                    break

            showMoreClick(driver)
            t = tarifs(driver, city, regionsDF.loc[region]["Регион"])
            logger.info(f'Для города {city} обнаружено {len(t)} тарифов')
            df = pd.concat([df, t])
finally:
    df.reset_index()
    df.to_excel("tarifs1.xlsx")
    driver.close()
