from datetime import datetime
import json

import logging

import os
import errno

class LinkGenerator:
    def __init__(self, parametersFolder):
        self.luInformation = self.loadJSON(parametersFolder['LU_information'])
        self.shiftInformation = self.loadJSON(parametersFolder['SHIFT_information'])
        self.masterLinks = self.loadJSON(parametersFolder['LINKS_information'])
        self.credentials = self.loadJSON(parametersFolder['credentials'])

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

        self.linkupList = list(self.luInformation["LU_list"].keys())

        self.shiftNames = self.generateVectors(self.linkupList, self.generateShiftNames)
        self.dates = self.generateVectors(self.linkupList, self.generateDates)
        self.grafanaLinks = self.generateVectors(self.linkupList, self.generatelinkForGrafana)
        self.SPALossTreeLinks = self.generateVectors(self.linkupList, self.generateLinkForLossTree, "packer")
        self.SPALossTreeCrimperLinks = self.generateVectors(self.linkupList, self.generateLinkForLossTree, "crimper")
        self.SPALossTreeCombinerLinks = self.generateVectors(self.linkupList, self.generateLinkForLossTree, "combiner")
        self.SPALossTreeCatTurnLinks = self.generateVectors(self.linkupList, self.generateLinkForLossTree, "catturn")
        self.LineOverviewLinks = self.generateVectors(self.linkupList, self.generateLinkForLineOverview)

    def getLinksToProcess(self):
        links_to_process = {
            "grafanaLinks" : self.grafanaLinks,
            "SPALossTreeLinks" : self.SPALossTreeLinks,
            "SPALossTreeCrimperLinks" : self.SPALossTreeCrimperLinks,
            "SPALossTreeCombinerLinks" : self.SPALossTreeCombinerLinks,
            "SPALossTreeCatTurnLinks" : self.SPALossTreeCatTurnLinks,
            "LineOverviewLinks" : self.LineOverviewLinks
        }
        return links_to_process

    def getFolderShiftsInfo(self):
        folders_structure = {
            "dates" : self.dates,
            "shifts" : self.shiftNames
        }
        return folders_structure

    def getSmcEnabled(self):
        w_wo_SMC = self.shiftInformation["w_wo_SMC"]
        return w_wo_SMC

    def loadJSON(self, FileName):
        with open(FileName, "r") as file:
            jsonContent = file.read()
            jsonList = json.loads(jsonContent)
            logging.debug(f"File: {FileName} read correctly!")
            #logging.debug(f"Output: {jsonContent}")
        return jsonList

    def generateVectors(self, linkupList, function, machine="packer"):
        #Function to generate vectors, which later will be used as config for WebScrapper
        itemList = []
        for linkup in linkupList:
            timestamp_tmp = self.start_timestamp
            shift_no_tmp = self.first_shift
            firstRun = True
            while timestamp_tmp < self.stop_timestamp:
                itemList = function(timestamp_tmp, shift_no_tmp, linkup, firstRun, itemList, machine)

                shift_no_tmp = self.generateShiftNumber(shift_no_tmp, self.no_of_shifts)
                timestamp_tmp += self.shift_length
                firstRun = False
        return itemList

    def generatelinkForGrafana(self, timestamp_tmp, shift_no_tmp, linkup, firstRun, linkList, machine):
        link = self.masterLinks["address_Grafana"].format(LuHash=self.luInformation["LU_list"][linkup]["LuHash"],
                                                          LuName=linkup,
                                                          orgId=self.luInformation["LU_list"][linkup]["orgId"],
                                                          StartTimestamp=timestamp_tmp,
                                                          EndTimestamp=timestamp_tmp+self.shift_length)
        linkList.append(link)
        return linkList

    def generateLinkForLossTree(self, timestamp_tmp, shift_no_tmp, linkup, firstRun, linkList, machine):
        date = datetime.fromtimestamp(timestamp_tmp / 1000).date().__str__()
        link = self.masterLinks["address_Loss_Tree"].format(login=self.credentials["username"],
                                                            password=self.credentials["password"],
                                                            spaLineName=self.luInformation["LU_list"][linkup]["spaLineName"],
                                                            Date=date,
                                                            StartShift=shift_no_tmp,
                                                            EndShift=shift_no_tmp
                                                            )
        if machine != "packer":
            link += self.luInformation["LU_list"][linkup]["spaLineNames"][machine]
        linkList.append(link)
        return linkList

    def generateLinkForLineOverview(self, timestamp_tmp, shift_no_tmp, linkup, firstRun, linkList, machine):
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
                                                                spaLineName=self.luInformation["LU_list"][linkup]["spaLineName"],
                                                                Date=date
                                                                )
        linkList.append(link)
        return linkList

    def generateDates(self, timestamp_tmp, shift_no_tmp, linkup, firstRun, shiftList, machine):
        date = datetime.fromtimestamp(timestamp_tmp / 1000).date().__str__()
        shiftList.append(date)
        return shiftList

    def generateShiftNames(self, timestamp_tmp, shift_no_tmp, linkup, firstRun, shiftList, machine):
        shiftList.append("Shift{}_{}".format(shift_no_tmp, linkup))
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

