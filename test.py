#!/usr/bin/env python3
from abc import ABC, abstractmethod
import xml.etree.ElementTree as et
import re
import gspread
import time
service_account = gspread.service_account(filename="./auth.json")

class Parser:
    @staticmethod
    def parse_svg(input):
        tree = et.parse(input)
        return tree

class SVGUtils:
    __tree, __root = None, None

    def __init__(self, tree):
        self.__tree = tree
        self.__root = self.__tree.getroot()

    def find_element_by_id(self, element_id):        
        return self.__root.findall(f'.//*[@id="{element_id}"]')[0]

    def element_attr_to_dict(self, element_id, attr):
        element = self.find_element_by_id(element_id)
        return dict(pair.split(":") for pair in element.attrib["" + attr + ""].split(";"))

    def set_style_attr(self, element_id, style):
        self.find_element_by_id(element_id).set(
            "style", ";".join(f"{k}:{v}" for k, v in style.items()))

    def __str__(self):
        return et.tostring(self.__tree.getroot()).decode()

class GraphicsPort(ABC):
    """
    Interface for graphic elements such as:
    - Range bars
    - Integer inputs
    - String inputs
    """
    @abstractmethod
    def sheet_action(self, action, **kwargs):
        pass

    @abstractmethod
    def render(self):
        pass


class ExternalDataProviderPort(ABC):
    """
    Interface for data retrieval from third party services such as
    - Google Sheets
    - Twitch Chat
    - Google word
    """
    def get_data(data):
        pass

    def set_data(data, value):
        pass


class GoogleSheetDataProviderAdapter(ExternalDataProviderPort):
    def __init__(self, google_service_account, sheet_name):
        self.google_service_account = google_service_account
        self.sheet = self.google_service_account.open("Necesidades")
        self.work_sheet = self.sheet.worksheet(sheet_name)

    def get_data(self, data):
        return self.work_sheet.acell(data).value

    def set_data(self, data, value):
        return self.work_sheet.update(data, value)


class RangeBar(GraphicsPort):
    _critical = False
    _empty = {
        "rightPhase": False,
        "fillPhase": False,
        "leftPhase": False
    }
    _opacity = {
        "rightPhase": 1,
        "fillPhase": 1,
        "leftPhase": 1
    }
    __value = 0
    _repeat = {
        "rightPhase": False,
        "fillPhase": False,
        "leftPhase": False
    }
    __external_data_adapter = None
    __utils: SVGUtils = None
    __phases_id = {
        #Partial_end = La parte de la derecha
        "rightPhase": "partial_end",
        "fillPhase": "fill",
        "leftPhase": "partial_start"
    }
    valid_actions = ["get_sheet_data", "update_sheet_data", "increment", "decrement", "opacity_update"]
    valid_types = ["numb", "text"]

    def __init__(self, utils: SVGUtils, external_data_port: ExternalDataProviderPort):
        self.__utils = utils
        self.__external_data_adapter = external_data_port
    
    def __increment(self, value):
        self.__value += abs(value)

    def __decrement(self, value):
        self.__value -= abs(value)

    def __get_sheet_data(self, type, cell):
        if type not in self.valid_types:
            raise Exception(f"{type} is not a valid type.")

        match type:
            case "numb":
                return round(float(self.__external_data_adapter.get_data(cell)),2)
            case "text":
                return self.__external_data_adapter.get_data(cell)
            
    def __update_sheet_data(self, cell, number):
        self.__external_data_adapter.set_data(cell, number)

    def __opacity_update(self, opacity, actPhase):
            PhaseStyle = self.__utils.element_attr_to_dict(self.__phases_id[actPhase], "style")
            PhaseStyle["fill-opacity"] = opacity
            self.__utils.set_style_attr(self.__phases_id[actPhase], PhaseStyle)

    def sheet_action(self, action, **kwargs):
        if action not in self.valid_actions:
            raise Exception(f"Invalid action {__class__}")

        match action:
            case "increment":
                self.__increment(kwargs["number"])
            case "decrement":
                self.__decrement(kwargs["number"])
            case "opacity_update":
                self.__opacity_update(kwargs["opacity"],kwargs["actPhase"])
            case "get_sheet_data":
                return self.__get_sheet_data(kwargs["type"],kwargs["cell"])
            case "update_sheet_data":
                return self.__update_sheet_data(kwargs["cell"],kwargs["number"])

    def getValue(self):
        return self.__value

    def setValue(self, value):
        self.__value = value

    def identifyAction(self, cell):
        action = self.sheet_action("get_sheet_data", type="text", cell=cell)
        #print(action)
        if (action == "Decrementar"):
            #print("valor RB pre decrement return:", self.getValue())
            return "decrement"
        if (action == "Incrementar"):
            return "increment"
        else:
            raise Exception(f"{action} is not a valid action.")

    def checkPhase(self, phase):
        match phase:
            case "rightPhase":
                return self._opacity["rightPhase"]
            case "leftPhase":
                return self._opacity["leftPhase"]

    def fillPhase(self, baseCellModified, phase):
        #probar a cambiar todos los self. por self._ en los def de la clase,
        # y ver si funciona
        if (baseCellModified != False):
            self.setValue(baseCellModified)
            self.sheet_action("update_sheet_data",cell="C3",number=100)
            self.sheet_action("opacity_update", opacity="0", actPhase="rightPhase")
        while self.getValue() > 13 and self.getValue() < 87:
            timeToAction = self.sheet_action("get_sheet_data", type="numb", cell="F3") * 60
            changeCell = self.sheet_action("get_sheet_data", type="numb", cell="E3")
            self.sheet_action(self.identifyAction("G3"),number=changeCell)
            self.sheet_action("update_sheet_data",cell="D3",number=self.getValue())
            if (self.getValue() < 12.9):
                self.sheet_action("update_sheet_data",cell="D3",number="10")
                self.setValue(10)
                self._empty[phase] = True
                self._empty["leftPhase"] = False
            if (self.getValue() > 86.9):
                self.sheet_action("update_sheet_data",cell="D3",number="87")
                self.setValue(87)
                self._empty[phase] = True
                self._empty["rightPhase"] = False
                self._empty["leftPhase"] = True
                if (self._repeat["fillPhase"] == True):
                    self.setValue(87)
                    self._repeat["fillPhase"] = False
                    return "fillPhaseIsEmpty"
            svg = self.render(phase)
            text_file = open("./1.svg", "w")
            text_file.write(svg)
            text_file.close()
            time.sleep(timeToAction)

    def partialPhase(self, baseCellModified, phase):
        #print("la fase es:", phase)
        #print("la opacidad de la fase es:",self._opacity[phase])
        if (baseCellModified != False):
            self.setValue(baseCellModified)
            self._opacity[phase] = baseCellModified / 100
            self.sheet_action("update_sheet_data",cell="C3",number=100)
        if (phase == "rightPhase"):
            self.setValue(86.9)
            if (self._opacity["rightPhase"] >= 1.01 and self._opacity["leftPhase"] >= 1.01):
                self._opacity["rightPhase"] = 1
            if (self._repeat["leftPhase"] == True):
                self._opacity[phase] = 0.01
                self._repeat["leftPhase"] = False
                self._repeat["fillPhase"] = True
            if (self._opacity[phase] == 0.0):
                self._empty["rightPhase"] = True
                self._repeat["fillPhase"] = True
        if (phase == "leftPhase"):
            self.setValue(12.9)
            self._opacity["rightPhase"] = 0
            #print("la nueva opacidad de la fase es:",self._opacity[phase])
            if (self._empty[phase] == False and self._opacity[phase] == 0):
                self._critical = True
            if (self._empty["fillPhase"] == True and self._opacity[phase] > 1):
                self.setValue(13.1)
                self._opacity[phase] = 1
                self._repeat["leftPhase"] = True
                return "fillPhaseIsEmpty"
            if (self._critical == True):
                self._opacity[phase] = 0.01
                self._critical = False
                self._repeat["leftPhase"] = True

        self.sheet_action("opacity_update", opacity=str(self._opacity[phase]), actPhase=phase)
        self.sheet_action("update_sheet_data",cell="D3",number=self.getValue())
        svg = str(self.__utils)
        text_file = open("./1.svg", "w")
        text_file.write(svg)
        text_file.close()
        timeToAction = self.sheet_action("get_sheet_data", type="numb", cell="F3") * 60
        time.sleep(timeToAction)

        while self._opacity[phase] > 0 and self._opacity[phase] < 1.01:
            timeToAction = self.sheet_action("get_sheet_data", type="numb", cell="F3") * 60
            changeCell = self.sheet_action("get_sheet_data", type="numb", cell="E3")
            #print("opacidad ACTUAL:", self._opacity[phase])
            action = self.identifyAction("G3")
            if (action == "decrement"):
                self._opacity[phase] -= (changeCell / 8)
            if (action == "increment" and self._opacity[phase] < 1.01 ):
                self._opacity[phase] += (changeCell / 8)
            if self._opacity[phase] < 0:
                self._opacity[phase] = 0
                self._empty[phase] = True
                if (phase == "leftPhase"):
                    self._critical = True
            self.sheet_action("opacity_update", opacity=str(self._opacity[phase]), actPhase=phase)
            self.sheet_action("update_sheet_data",cell="D3",number=self.getValue())
            svg = str(self.__utils)
            text_file = open("./1.svg", "w")
            text_file.write(str(self.__utils))
            text_file.close()
            time.sleep(timeToAction)

    def emptyBar(self):
        self._opacity["leftPhase"] = 0
        self._opacity["fillPhase"] = 0
        self._opacity["rightPhase"] = 0
        self.setValue(10)
        self.sheet_action("opacity_update", opacity="0", actPhase="rightPhase")
        self.sheet_action("opacity_update", opacity="0", actPhase="leftPhase")
        self.sheet_action("opacity_update", opacity="0", actPhase="fillPhase")
        svg = self.render("leftPhase")
        text_file = open("./1.svg", "w")
        text_file.write(svg)
        text_file.close()

    def alertBar(self):
        action = self.identifyAction(cell="G3")
        if (action == "increment"):
            self._empty["leftPhase"] = True
            return "leftPhaseIsEmpty"
        while action == "decrement":
            #print("Help, I'm at Critical Phase")
            #print("Action:",action)
            timeToAction = self.sheet_action("get_sheet_data", type="numb", cell="F3") * 60
            action = self.identifyAction(cell="G3")
            if (action == "increment"):
                self._empty["leftPhase"] = True
                return "leftPhaseIsEmpty"
            time.sleep(timeToAction)

    def render(self, phase):
        new_pos_x = round((self.__value * -1),2)
        new_width = round((self.__value - 10),2)
        element = self.__utils.find_element_by_id(self.__phases_id[phase])
        element.set("x", str(new_pos_x))
        element.set("width", str(new_width))
        #print("new_pos_x",new_pos_x)
        #print("new_width",new_width)
        return str(self.__utils)

 
def main():
    _emptyStatus = ""

    google_sheet_data_provider = GoogleSheetDataProviderAdapter(service_account, "Needs")

    svg = Parser.parse_svg("rangebar.svg")
    rb = RangeBar(SVGUtils(svg), google_sheet_data_provider)

    while True:
        baseCell = rb.sheet_action("get_sheet_data", type="numb", cell="C3")
        if (baseCell != 100.00):
            if (baseCell > 87.00):
                rb.partialPhase(baseCell, "rightPhase")
            if (baseCell > 13.00):
                rb._opacity = {"rightPhase": 0, "leftPhase": 1}
                rb.fillPhase(baseCell, "fillPhase")
            else:
                rb.emptyBar()
                rb.partialPhase(baseCell, "leftPhase")
        else:
            if (rb._empty["rightPhase"] == False or _emptyStatus == "rightPhaseIsEmpty"):
                #print("Start Phase 1 Loop")
                _emptyStatus = rb.partialPhase(False, "rightPhase")
                #rb._opacity = {"rightPhase": 0, "leftPhase": 1}
                #print("Exit Phase 1 Loop")
            if (rb._empty["fillPhase"] == False or _emptyStatus == "fillPhaseIsEmpty" or rb._repeat["fillPhase"] == True):
                #print("Start Phase 2 Loop")
                _emptyStatus = rb.fillPhase(False, "fillPhase")
                #print("Exit Phase 2 Loop")
            if (rb._empty["leftPhase"] == False or _emptyStatus == "leftPhaseIsEmpty" or rb._repeat["leftPhase"] == True):
                #print("Start Phase 3 Loop")
                _emptyStatus = rb.partialPhase(False, "leftPhase")
                #rb._opacity = {"rightPhase": 0, "leftPhase": 0}
                #print("Exit Phase 3 Loop")
            if (rb._critical == True):
                _emptyStatus = rb.alertBar()


if __name__ == "__main__":
    main()