from datetime import datetime
import json

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pdfkit

import logging

import os
import errno


class LinkGenerator:
    def __init__(self, ParametersFolder):
        self.luInformation = self.loadJSON(ParametersFolder['LU_information'])
        self.shiftInformation = self.loadJSON(ParametersFolder['SHIFT_information'])
        self.masterLinks = self.loadJSON(ParametersFolder['LINKS_information'])
        self.credentials = self.loadJSON(ParametersFolder['credentials'])

        logging.info(f"Config Read correctly!")

        # Multiplied by 1000, as grafana timestamp
        self.start_timestamp = int(datetime.strptime(self.shiftInformation["start_date"],
                                                     self.shiftInformation["format_date"]).timestamp()) * 1000
        self.stop_timestamp = int(datetime.strptime(self.shiftInformation["end_date"],
                                                    self.shiftInformation["format_date"]).timestamp()) * 1000
        self.shift_length = self.shiftInformation["length_of_shift"] * 60 * 60 * 1000
        self.no_of_shifts = self.shiftInformation["no_of_shifts"]
        self.first_shift = self.shiftInformation["first_shift"]
        self.smc_enabled_flag = self.shiftInformation["w_wo_SMC"]


        self.shiftNames = self.generateVectors('lu11', self.generateShiftNames)
        self.dates = self.generateVectors('lu11', self.generateDates)
        self.grafanaLinks = self.generateVectors('lu11', self.generatelinkForGrafana)
        self.SPALossTreeLinks = self.generateVectors('lu11', self.generateLinkForLossTree)
        self.LineOverviewLinks = self.generateVectors('lu11', self.generateLinkForLineOverview)
        self.SPALossTreeLinksModifier = self.modifiersForLossTree('lu11')

    def get(self):
        return

    def loadJSON(self, FileName):
        with open(FileName, "r") as file:
            jsonContent = file.read()
            jsonList = json.loads(jsonContent)
            logging.debug(f"File: {FileName} read correctly!")
            #logging.debug(f"Output: {jsonContent}")
        return jsonList

    def generateVectors(self, key, function):
        #Function to generate vectors, which later will be used as config for WebScrapper
        timestamp_tmp = self.start_timestamp
        shift_no_tmp = self.first_shift

        firstRun = True
        itemList = []
        while timestamp_tmp < self.stop_timestamp:

            itemList = function(timestamp_tmp, shift_no_tmp, key, firstRun, itemList)



            shift_no_tmp = self.generateShiftNumber(shift_no_tmp, self.no_of_shifts)
            timestamp_tmp += self.shift_length
            firstRun = False
        return itemList

    def generatelinkForGrafana(self, timestamp_tmp, shift_no_tmp, key, firstRun, linkList):
        link = self.masterLinks["address_Grafana"].format(LuHash=self.luInformation["LU_list"][key]["LuHash"],
                                                          LuName=key,
                                                          orgId=self.luInformation["LU_list"][key]["orgId"],
                                                          StartTimestamp=timestamp_tmp,
                                                          EndTimestamp=timestamp_tmp+self.shift_length)
        linkList.append(link)
        return linkList

    def generateLinkForLossTree(self, timestamp_tmp, shift_no_tmp, key, firstRun, linkList):
        date = datetime.fromtimestamp(timestamp_tmp / 1000).date().__str__()
        link = self.masterLinks["address_Loss_Tree"].format(login=self.credentials["username"],
                                                            password=self.credentials["password"],
                                                            spaLineName=self.luInformation["LU_list"][key]["spaLineName"],
                                                            Date=date,
                                                            StartShift=shift_no_tmp,
                                                            EndShift=shift_no_tmp
                                                            )
        linkList.append(link)
        return linkList

    def generateLinkForLineOverview(self, timestamp_tmp, shift_no_tmp, key, firstRun, linkList):
        if firstRun:
            previousDate = ""
        else:
            previousDate = datetime.fromtimestamp((timestamp_tmp-self.shift_length) / 1000).date().__str__()
        date = datetime.fromtimestamp(timestamp_tmp / 1000).date().__str__()
        if date == previousDate:
            link = "None"
        else:
            link = self.masterLinks["address_Line_Over"].format(login=self.credentials["username"],
                                                                password=self.credentials["password"],
                                                                spaLineName=self.luInformation["LU_list"][key]["spaLineName"],
                                                                Date=date
                                                                )
        linkList.append(link)
        return linkList

    def modifiersForLossTree(self, key):
        modifier = {"LossTreeLinkModifier":{}}
        for machine in self.luInformation["LU_list"][key]["spaLineNames"]:
            modifier["LossTreeLinkModifier"].update(
                {machine: self.luInformation["LU_list"][key]["spaLineNames"][machine]})

        return modifier

    def generateDates(self, timestamp_tmp, shift_no_tmp, key, firstRun, shiftList):
        date = datetime.fromtimestamp(timestamp_tmp / 1000).date().__str__()
        shiftList.append(date)
        return shiftList
    def generateShiftNames(self, timestamp_tmp, shift_no_tmp, key, firstRun, shiftList):
        shiftList.append("Shift{}_{}".format(shift_no_tmp, key))
        return shiftList

    def generateShiftNumber(self, shift_no_tmp, no_of_shifts):
        if shift_no_tmp >= no_of_shifts:
            shift_no_tmp = 1
        else:
            shift_no_tmp += 1
        #logging.debug(f"Shift Generated correctly")
        return shift_no_tmp





    def _make_dir(path):
        try:
            os.makedirs(path, exist_ok=True)  # Python>3.2
        except TypeError:
            try:
                os.makedirs(path)
            except OSError as exc: # Python >2.5
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    logging.info(f"Making Directory failed!")
                    raise

def main():
    logging.basicConfig(level=logging.DEBUG)

    Parameters = {'LU_information' : "Parameters/LU_information.json",
                  'SHIFT_information' : "Parameters/SHIFT_information.json",
                  'LINKS_information' : "Parameters/LINKS_information.json",
                  'credentials' : "Parameters/credentials.json"}

    generateLinks = LinkGenerator(Parameters)




class ScraperConfiguration:
    def __init__(self):
        self.links_to_process = {}
        self.folders_structure = {}
        self.smc_enabled_flag = ""


class WebScraper:
    def __init__(self):
        self.config = ScraperConfiguration()

    def scrape(self):
        try:
            # Initialize scraping process
            session = requests.Session()
            session.headers.update({'User-Agent': self.config.user_agent})

            for url in self.config.target_urls:
                # Authenticate for specific links
                if url == "https://example.com/login":
                    self.authenticate(session, url)

                response = session.get(url)
                response.raise_for_status()  # Raise exception for non-200 status codes

                html_content = response.text

                # Parse the HTML content
                parser = PageParser()
                parsed_data = parser.parse(html_content)

                # Store the parsed data
                data_store = DataStore()
                data_store.save(parsed_data)

                # Capture screenshot
                screenshot_maker = ScreenshotMaker()
                screenshot_maker.capture(url)

                # Print long page to PDF
                if parsed_data.is_long_page:
                    pdf_printer = PDFPrinter()
                    pdf_printer.print_to_pdf(url)

            session.close()

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while making a request: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def authenticate(self, session, url):
        # Authentication logic for specific URLs
        # Modify this method as per your authentication requirements
        if url == "https://example.com/login":
            payload = {
                'username': 'your_username',
                'password': 'your_password'
            }
            session.post(url, data=payload)


class PageParser:
    def parse(self, html_content):
        try:
            # Parsing logic using BeautifulSoup or any other HTML parsing library
            # Extract relevant data and return as structured objects

            # Sample data model
            data = DataModel()
            data.title = "Sample Title"
            data.description = "Sample Description"
            data.is_long_page = True  # Assume the page is long for demonstration purposes
            return data

        except Exception as e:
            print(f"An error occurred while parsing the page: {e}")


class DataModel:
    def __init__(self):
        self.title = ""
        self.description = ""
        self.is_long_page = False


class DataStore:
    def save(self, data):
        try:
            # Store the extracted data in a database or any other storage system
            print(f"Saving data: {data.title} - {data.description}")
        except Exception as e:
            print(f"An error occurred while saving the data: {e}")


class ScraperConfiguration:
    def __init__(self):
        self.target_urls = [
            "https://example.com",
            "https://example.com/login"
        ]
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                           "Chrome/90.0.4430.212 Safari/537.36 "


class ScreenshotMaker:
    def __init__(self):
        options = Options()
        options.add_argument("--headless")  # Run browser in headless mode
        self.driver = webdriver.Chrome(options=options)

    def capture(self, url):
        try:
            self.driver.get(url)
            # Capture screenshot and save it to the desired location
            self.driver.save_screenshot("screenshot.png")
        except Exception as e:
            print(f"An error occurred while capturing the screenshot: {e}")
        finally:
            self.driver.quit()


if __name__ == "__main__":
    main()