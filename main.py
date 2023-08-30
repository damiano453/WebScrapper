import time
from datetime import datetime
import json

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pdfkit

import logging

import os
import errno

from threading import Timer
import pyautogui

from LinkGenerator import LinkGenerator


class ScraperConfiguration:
    def __init__(self, parametersFolder):
        #self.parameters = parametersFolder
        generateLinks = LinkGenerator(parametersFolder)

        self.target_urls = generateLinks.getLinksToProcess()
        self.folders_structure = generateLinks.getFolderShiftsInfo()

        self.credentials = generateLinks.credentials

        self.smc_enabled_flag = generateLinks.getSmcEnabled()
        self.no_of_shifts = generateLinks.no_of_shifts

        logging.info(f"Configuration read correctly!")

        self.service_object = Service("msedgedriver")
        self.options = Options()
        self.options.add_experimental_option("detach", True)
        self.options.add_argument("-inprivate")

class WebScraper:
    def __init__(self, Parameters, ParserParameters):
        self.config = ScraperConfiguration(Parameters)
        
        self.parser = PageParser(ParserParameters)

        #print(self.config.folders_structure['dates'][0])

        self.scrape()

    def scrape(self):
        try:
            # Initialize scraping process
            driver = webdriver.Edge(service=self.config.service_object, options=self.config.options)
            driver.maximize_window()

            Timer(10, pyautogui.press, ["esc"]).start()

            #self._get_grafana(driver)
            self._get_loss_tree(driver)
            print(self.parser.data)

            driver.close()

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while making a request: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")


    def _get_loss_tree(self, driver):
        #print(self.config.target_urls)
        for iterator, url in enumerate(self.config.target_urls['SPALossTreeLinks']):

            # for Packer Reference OPEN+
            driver = self.__load_spa_page(driver, url)

            date = self.config.folders_structure['dates'][iterator]
            shift = self.config.folders_structure['shifts'][iterator]

            self.parser.parse_reference_packer(driver, date, shift, self.config.smc_enabled_flag)

            # for Crimper
            machineLinks = ['SPALossTreeCrimperLinks', 'SPALossTreeCombinerLinks', 'SPALossTreeCatTurnLinks']
            for machineLink in machineLinks:
                driver = self.__load_spa_page(driver, self.config.target_urls[machineLinks][iterator])

                self.parser.parse_machines(driver, machineLinks, date, shift, self.config.smc_enabled_flag)



            time.sleep(5)
            break

            #self._take_screenshot(driver, iterator, "03_Grafana Line Overview.png")

    @staticmethod
    def __load_spa_page(driver, url):
        driver.get(url)
        time.sleep(2)
        Timer(2, pyautogui.press, ["esc"]).start()
        Xpath_allUnplannedDowntime = '//*[@id="section_AllUnplannedDT"]/tbody/tr/td[4]/table/tbody/tr/td/input'
        Xpath_byPoSection = '/html/body/table[3]/tbody/tr[55]/td[2]/b'
        '/html/body/table[3]/tbody/tr[55]/td[2]/b'
        element_present = None
        while element_present == None:
            print("here")
            # time.sleep(2)
            if str(driver.page_source).lower().find("webdab") != -1:
                driver.refresh()
            elif str(driver.page_source) == "<html><head></head><body></body></html>" or \
                    str(driver.page_source).find("-DescriptionLT-") != -1:
                driver.refresh()
            else:
                print("else")
            print(element_present)
            try:
                element_present = EC.presence_of_element_located((By.XPATH, Xpath_byPoSection))
                WebDriverWait(driver, 10).until(element_present)
            except TimeoutException:
                driver.refresh()

        return driver

    def _get_grafana(self, driver):
        for iterator, url in enumerate(self.config.target_urls['grafanaLinks']):
            driver.get(url)
            time.sleep(5)
            if iterator == 0:
                self._authenticate_grafana(driver)

            driver.execute_script("document.body.style.zoom='45%'")

            try:
                element_present = EC.presence_of_element_located((By.CLASS_NAME, "panel-loading"))

                WebDriverWait(driver, 10).until(element_present)

                WebDriverWait(driver, 20).until_not(element_present)
            except TimeoutException:
                logging.debug(f"Grafana authenticated correctly!")
                pass

            self._take_screenshot(driver, iterator, "03_Grafana Line Overview.png")

    def _authenticate_grafana(self, driver):
        # Authentication logic for specific URLs
        # Modify this method as per your authentication requirements
        time.sleep(5)

        xPath_Login = '//*[@id="reactRoot"]/div[1]/main/div[3]/div/div[2]/div/div/form/div[1]/div[2]/div/div/input'
        xPath_Passwd = '//*[@id="current-password"]'
        xPath_Submit = '//*[@id="reactRoot"]/div[1]/main/div[3]/div/div[2]/div/div[1]/form/button'
        driver.find_element(By.XPATH, xPath_Login).send_keys(self.config.credentials["username"])
        driver.find_element(By.XPATH, xPath_Passwd).send_keys(self.config.credentials["password"])
        driver.find_element(By.XPATH, xPath_Submit).click()
        time.sleep(5)

    def _take_screenshot(self, driver, iterator, fileName):
        self._make_dir('./Output/{}/{}'.format(
            self.config.folders_structure['dates'][iterator],
            self.config.folders_structure['shifts'][iterator]))

        driver.save_screenshot('./Output/{}/{}/{}'.format(
            self.config.folders_structure['dates'][iterator],
            self.config.folders_structure['shifts'][iterator],
            fileName
        ))

    @staticmethod
    def _make_dir(path):
        try:
            os.makedirs(path, exist_ok=True)  # Python>3.2
        except TypeError:
            try:
                os.makedirs(path)
            except OSError as exc:  # Python >2.5
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    raise


class PageParser:
    def __init__(self, file):
        self.data = {}
        self.parameters = {}
        self._get_parse_parameters(file)

        #print(self.data)

    def parse_reference_packer(self, driver, machine, date, shift, smc_enabled_flag):
        try:
            # Parsing logic using BeautifulSoup or any other HTML parsing library
            # Extract relevant data and return as structured objects
            for key in self.data:
                if key == 'CLTC-Number of External Stops [#]':
                    continue
                elif key == 'COMB-Number of External Stops [#]':
                    continue
                elif key == 'CTU-Number of External Stops [#]':
                    continue

                function = self.parameters[key]["localisation"]["function"]
                if function == "assign":
                    value = self.__assign(key, date, shift, smc_enabled_flag)
                    self.data[key].append(value)
                elif function == "extract":
                    value = self.__extract(driver, key)
                    self.data[key].append(value)
                elif function == "extract_plus_1":
                    value = self.__extract(driver, key, addon=1)
                    self.data[key].append(value)
                elif function == "extract_split_number":
                    value = self.__extract_split_number(driver, key)
                    self.data[key].append(value)



                print({key : self.data[key]})


        except Exception as e:
            logging.error(f"An error occurred while parsing the page: {e}")

    def parse_machines(self, driver, machineLinks, date, shift, smc_enabled_flag):
        try:
            # Parsing logic using BeautifulSoup or any other HTML parsing library
            # Extract relevant data and return as structured objects
            for key in self.data:
                if key == 'CLTC-Number of External Stops [#]' and machineLinks == 'SPALossTreeCrimperLinks':
                    value = self.__extract(driver, key)
                    self.data[key].append(value)
                elif key == 'COMB-Number of External Stops [#]' and machineLinks == 'SPALossTreeCombinerLinks':
                    value = self.__extract(driver, key)
                    self.data[key].append(value)
                elif key == 'CTU-Number of External Stops [#]' and machineLinks == 'SPALossTreeCatTurnLinks':
                    value = self.__extract(driver, key)
                    self.data[key].append(value)

        except Exception as e:
            logging.error(f"An error occurred while parsing the page: {e}")

    @staticmethod
    def __assign(key, date, shift, smc_enabled_flag):
        if key == "Date":
            return date
        elif key == "Shift":
            return shift.rsplit("_")[0]
        elif key == "w/wo SM":
            return smc_enabled_flag

    def __extract_split_number(self, driver, key):
        value = self.__extract(driver, key)
        for val in value.rsplit(" "):
            if self.is_float(val):
                return val
    def __extract(self, driver, key, addon=0):
        Xpath_Row = self.parameters[key]["localisation"]["Xpath_table_raw"]
        key_word = self.parameters[key]["localisation"]["key_word"]
        try:
            rowsToAdd = self._find_row_in_table(driver, Xpath_Row, key_word)
        except:
            rowsToAdd = 0
        Xpath_Value = self.parameters[key]["localisation"]["Xpath_item"].format(rowsToAdd+addon)
        try:
            value = driver.find_element(By.XPATH, Xpath_Value)
            return value.text
        except:
            value = "NaN"
            return value
    def _get_parse_parameters(self, file_name):
        self.parameters = self._loadJSON(file_name)

        for key in self.parameters:
            self.data[key] = []

    def _loadJSON(self, FileName):
        with open(FileName, "r") as file:
            jsonContent = file.read()
            jsonList = json.loads(jsonContent)
            logging.debug(f"File: {FileName} read correctly!")
        return jsonList

    def _find_row_in_table(self, driver, Xpath_linePerformance, parameter, default=0):
        # Calculate rows modified, if PO was changed during the shift
        for i in range(1000):
            try:
                elem = driver.find_element(By.XPATH, Xpath_linePerformance.format(default + i))
                if parameter == "Reference run time":
                    if "Reference run time" in elem.text:
                        rowsToAddByPO = i
                        return rowsToAddByPO
                        break
                if elem.text == parameter:
                    rowsToAddByPO = i
                    return rowsToAddByPO
                    break
            # return True
            except NoSuchElementException:
                pass
        return 1

    @staticmethod
    def is_float(string):
        try:
            float(string)
            return True
        except ValueError:
            return False

def main():
    logging.basicConfig(level=logging.INFO)

    general_parameters = {'LU_information' : "Parameters/LU_information.json",
                  'SHIFT_information' : "Parameters/SHIFT_information.json",
                  'LINKS_information' : "Parameters/LINKS_information.json",
                  'credentials' : "Parameters/credentials.json"}

    parser_parameters = "./Parameters/Parser_configuration_SPA.json"

    #generateLinks = LinkGenerator(general_parameters)

    #configuration = ScraperConfiguration(general_parameters)

    scraper = WebScraper(general_parameters, parser_parameters)




class DataStore:
    def save(self, data):
        try:
            # Store the extracted data in a database or any other storage system
            print(f"Saving data: {data.title} - {data.description}")
        except Exception as e:
            print(f"An error occurred while saving the data: {e}")





if __name__ == "__main__":
    main()