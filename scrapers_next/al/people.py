import re

import attr
from spatula import HtmlListPage, HtmlPage, XPath, CSS
from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    url: str
    chamber: str = ""


class LegDetail(HtmlPage):
    # senator
    # example_source = "http://www.legislature.state.al.us/aliswww/ISD/ALSenator.aspx?NAME=Albritton&OID_SPONSOR=100465&OID_PERSON=7691&SESSNAME=Regular%20Session%202022"
    # rep
    example_source = "http://www.legislature.state.al.us/aliswww/ISD/ALRepresentative.aspx?NAME=Alexander&OID_SPONSOR=100537&OID_PERSON=7710&SESSNAME=Regular%20Session%202022"
    # vacant (for some reason)
    # example_source = 'http://www.legislature.state.al.us/aliswww/ISD/ALRepresentative.aspx?NAME=District%2078&OID_SPONSOR=9100560&OID_PERSON=998507&SESSNAME=Regular%20Session%202022'

    def process_page(self):

        name = (
            CSS(".container-main #ContentPlaceHolder1_lblMember")
            .match_one(self.root)
            .text_content()
        )

        # print('name', name)
        # TODO: any way to get rid of the empty ''?
        if self.input.chamber == "upper":
            name_split = re.split("SENATOR|, ", name)
        elif self.input.chamber == "lower":
            name_split = re.split("REPRESENTATIVE|, ", name)
        full_name = name_split[2] + name_split[1]
        # if full_name == "":
        #     self.warn("This seat is vacant")

        table = CSS("#ContentPlaceHolder1_TabSenator_TabLeg_gvLEG").match_one(self.root)

        for tr in CSS("tr").match(table):
            # print("tr ", tr.text_content())
            type, info = CSS("td").match(tr)
            # print("tr's: ", tr_1.text_content())
            type = type.text_content()
            info = info.text_content()

            if type == "Affiliation:":
                if info == "(R)":
                    party = "Republican"
                elif info == "(D)":
                    party = "Democrat"
                else:
                    # party = "Republican"
                    self.warn("the party must be included")

            elif type == "District:":
                # should i keep 'Senate District ##' or 'House District ##'?
                district = info.split(" ")[2]
            elif type == "County:":
                county = info
            elif type == "Phone Number:":
                phone = info
            elif type == "Fax Number:":
                if info != "":
                    fax = info
            elif type == "Street:":
                street = info
            elif type == "Office:":
                office = info
            elif type == "City:":
                city = info
            elif type == "Postal Code:":
                postal = info
            elif type == "Email:":
                email = info

        # is this formatted correctly?
        address = f"{street}, {office}, {city} AL"

        image = (
            CSS("#ContentPlaceHolder1_TabSenator_TabLeg_imgLEG")
            .match_one(self.root)
            .get("src")
        )
        print("image", image)

        p = ScrapePerson(
            name=full_name.title(),
            state="al",
            chamber=self.input.chamber,
            party=party,
            district=district,
            email=email,
            image=image,
        )
        p.add_source(self.source.url)
        p.add_source(self.input.url)

        # This address is the capitol office
        if re.search("11 South Union Street", street):
            p.capitol_office.address = address
            p.capitol_office.voice = phone
            try:
                p.capitol_office.fax = fax
            except ValueError:
                pass
        else:
            p.district_office.address = address
            p.district_office.voice = phone
            try:
                p.district_office.fax = fax
            except ValueError:
                pass

        p.extras["postal code"] = postal
        p.extras["county"] = county

        return p


class LegList(HtmlListPage):
    def process_item(self, item):
        last_name = re.split("Pictures/|_", item.get("src"))[1]
        oid_person = item.get("alt")

        # have to extract these numbers that are in the image for the URL, so will prob change selector in SenList and RepList
        # OID_SPONSOR=###
        # ex: http://www.legislature.state.al.us/aliswww/ISD/ALSenator.aspx?NAME=Albritton&OID_SPONSOR=100465&OID_PERSON=7691&SESSNAME=Regular%20Session%202022
        if last_name == "VACANT":
            pass

        elif self.chamber == "upper":
            oid_sponsor = item.get("longdesc").split("Senate/")[1]
            url = f"http://www.legislature.state.al.us/aliswww/ISD/ALSenator.aspx?NAME={last_name}&OID_SPONSOR={oid_sponsor}&OID_PERSON={oid_person}&SESSNAME=Regular%20Session%202022"
        elif self.chamber == "lower":
            oid_sponsor = item.get("longdesc").split("House/")[1]
            print("oid sponsor: ", item.get("longdesc"))

            url = f"http://www.legislature.state.al.us/aliswww/ISD/ALRepresentative.aspx?NAME={last_name}&OID_SPONSOR={oid_sponsor}&OID_PERSON={oid_person}&SESSNAME="
        # print("url", url)
        # print(self.input.url)

        p = PartialMember(url=self.source.url, chamber=self.chamber)

        return LegDetail(p, source=url)


class SenList(LegList):
    selector = XPath("//input[@type='image']")
    source = "http://www.legislature.state.al.us/aliswww/ISD/Senate/ALSenators.aspx"
    chamber = "upper"


class RepList(LegList):
    selector = XPath("//input[@type='image']")
    source = (
        "http://www.legislature.state.al.us/aliswww/ISD/House/ALRepresentatives.aspx"
    )
    chamber = "lower"
