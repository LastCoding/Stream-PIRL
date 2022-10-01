#!/usr/bin/env python3
from abc import ABC, abstractmethod
import xml.etree.ElementTree as et
import re
import gspread

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

class GraphicsPort(ABC):
    """
    Interface for graphic elements such as:
    - Range bars
    - Integer inputs
    - String inputs
    """
    @abstractmethod
    def execute_action(self, action, **kwargs):
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


class GoogleSheetDataProviderAdapter(ExternalDataProviderPort):
    def __init__(self, google_service_account, sheet_name):
        self.google_service_account = google_service_account
        self.sheet = self.google_service_account.open("DynamicOverlays")
        self.work_sheet = self.sheet.worksheet(sheet_name)

    def get_data(self, data):
        return self.work_sheet.acell(data).value


class RangeBar(GraphicsPort):
    __value = 0
    __external_data_adapter = None
    __utils: SVGUtils = None
    __main_elements_id = {
        "color": "fill",
        "width": "fill"
    }
    valid_actions = ["external_data_provider", "increment", "decrement", "change_color"]

    def __init__(self, utils: SVGUtils, external_data_port: ExternalDataProviderPort):
        self.__utils = utils
        self.__external_data_adapter = external_data_port
    
    def __increment(self, value):
        self.__value += abs(value)

    def __decrement(self, value):
        self.__value -= abs(value)

    def __external_data_provider(self, cell):
        self.__value = int(self.__external_data_adapter.get_data(cell))

    def __change_color(self, color):
        is_valid = re.match(r'^#([a-f0-9]{6})$', color.lower())
        if is_valid:
            element = self.__utils.find_element_by_id(self.__main_elements_id["color"])
            style = self.__utils.element_attr_to_dict(self.__main_elements_id["color"], "style")
            style["fill"] = color
            self.__utils.set_style_attr(self.__main_elements_id["color"], style)

        else:
            raise Exception("Invalid color code.")

    def execute_action(self, action, **kwargs):
        if action not in self.valid_actions:
            raise Exception(f"Invalid action {__class__}")

        match action:
            case "increment":
                self.__increment(kwargs["number"])
            case "decrement":
                self.__decrement(kwargs["number"])
            case "change_color":
                self.__change_color(kwargs["color"])
            case "external_data_provider":
                self.external_data_provider(kwargs["cell"])


    def render(self):
        return et.tostring(self._tree.getroot()).decode()

def main():

    google_sheet_data_provider = GoogleSheetDataProviderAdapter(service_account, "Hoja1")
    
    svg = Parser.parse_svg("rangebar.svg")
    rb = RangeBar(SVGUtils(svg), google_sheet_data_provider)
    rb.execute_action("change_color", color="#4287f5")

if __name__ == "__main__":
    main()