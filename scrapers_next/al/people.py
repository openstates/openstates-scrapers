import re

# import attr
from spatula import HtmlListPage, HtmlPage, XPath

# from openstates.models import ScrapePerson


class LegDetail(HtmlPage):
    # senator
    example_source = "http://www.legislature.state.al.us/aliswww/ISD/ALSenator.aspx?NAME=Albritton&OID_SPONSOR=100465&OID_PERSON=7691&SESSNAME=Regular%20Session%202022"
    # rep
    # example_source = 'http://www.legislature.state.al.us/aliswww/ISD/ALRepresentative.aspx?NAME=Alexander&OID_SPONSOR=100537&OID_PERSON=7710&SESSNAME=Regular%20Session%202022'
    # vacant (for some reason)
    # example_source = 'http://www.legislature.state.al.us/aliswww/ISD/ALRepresentative.aspx?NAME=District%2078&OID_SPONSOR=9100560&OID_PERSON=998507&SESSNAME=Regular%20Session%202022'


class LegList(HtmlListPage):
    def process_item(self, item):
        last_name = re.split("Pictures/|_", item.get("src"))[1]
        oid_sponsor = item.get("longdesc").split("Senate/")[1]
        # print('oid sponsor', oid_sponsor)
        oid_person = item.get("alt")
        # print(last_name)
        # print('self.chamber', self.chamber)

        # have to extract these weird numbers that are in the image for the URL, so will prob change selector in SenList and RepList
        # OID_SPONSOR=###
        # ex: http://www.legislature.state.al.us/aliswww/ISD/ALSenator.aspx?NAME=Albritton&OID_SPONSOR=100465&OID_PERSON=7691&SESSNAME=Regular%20Session%202022
        if self.chamber == "upper":
            url = f"http://www.legislature.state.al.us/aliswww/ISD/ALSenator.aspx?NAME={last_name}&OID_SPONSOR={oid_sponsor}&OID_PERSON={oid_person}&SESSNAME=Regular%20Session%202022"
        if self.chamber == "lower":
            url = f"http://www.legislature.state.al.us/aliswww/ISD/ALRepresentative.aspx?NAME={last_name}&OID_SPONSOR={oid_sponsor}&OID_PERSON={oid_person}&SESSNAME="
        print("url", url)
        # return LegDetail(source=url)


class SenList(LegList):
    # name text
    # selector = XPath("//span[@class='member_label']")

    selector = XPath("//input[@type='image']")
    source = "http://www.legislature.state.al.us/aliswww/ISD/Senate/ALSenators.aspx"
    chamber = "upper"


class RepList(LegList):
    selector = XPath("//span[@class='member_label']")
    source = (
        "http://www.legislature.state.al.us/aliswww/ISD/House/ALRepresentatives.aspx"
    )
    chamber = "lower"
