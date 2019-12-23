"""Scrapes Idaho committees for the latest term."""
from pupa.scrape import Scraper, Organization
import lxml.html


_COMMITTEE_URL = (
    "https://legislature.idaho.gov/committees/%scommittees/"  # house/senate
)
_JOINT_URL = "https://legislature.idaho.gov/sessioninfo/2017/joint/"

_CHAMBERS = {"upper": "senate", "lower": "house"}
_REV_CHAMBERS = {"senate": "upper", "house": "lower"}


def clean_name(name):
    return name.replace(u"\xa0", " ")


class IDCommitteeScraper(Scraper):
    def get_joint_committees_data(self, name, url):
        page = self.get(url).text
        html = lxml.html.fromstring(page)
        org = Organization(name=name, chamber="legislature", classification="committee")
        table = html.xpath("//section[@class=' row-equal-height no-padding']")
        for td in table:
            senate_members = td.xpath("div[1]/div/div/div[2]/div/p/strong")
            if len(senate_members) > 0:
                member_string = list(senate_members[0].itertext())
                if len(member_string) > 1:
                    name = member_string[0]
                    role = member_string[1]
                    for ch in ["Sen.", ",", u"\u00a0"]:
                        name = name.replace(ch, " ").strip()
                        role = role.replace(ch, " ").strip()
                    org.add_member(name, role=role)
                else:
                    name = member_string[0].replace("Sen.", " ").strip()
                    for ch in ["Sen.", ",", u"\u00a0"]:
                        name = name.replace(ch, " ").strip()
                    org.add_member(name)
            house_members = list(td.xpath("div[2]/div/div/div[2]/div/p/strong"))
            if len(house_members) > 0:
                member_string = list(house_members[0].itertext())
                if len(member_string) > 1:
                    name = member_string[0].replace("Rep.", " ").strip()
                    role = member_string[1].replace(",", " ").strip()
                    for ch in ["Rep.", ",", u"\u00a0"]:
                        name = name.replace(ch, " ").strip()
                        role = role.replace(ch, " ").strip()
                    org.add_member(name, role=role)
                else:
                    name = member_string[0].replace("Rep.", " ").strip()
                    for ch in ["Rep.", ",", u"\u00a0"]:
                        name = name.replace(ch, " ").strip()
                    org.add_member(name)
        org.add_source(url)
        return org

    def scrape_committees(self, chamber):
        url = _COMMITTEE_URL % _CHAMBERS[chamber]
        page = self.get(url).text
        html = lxml.html.fromstring(page)
        table = html.xpath("body/section[2]/div/div/section[2]/div[2]/div/div/div/div")
        for row in table[1:]:
            # committee name, description, hours of operation,
            # secretary and office_phone
            text = list(row[0].xpath("div")[0].itertext())
            attributes = [
                list(
                    value.replace(u"\xa0", " ")
                    .replace("Secretary:", "")
                    .encode("ascii", "ignore")
                    for value in text
                    if "Email:" not in value and value != "\n" and "Phone:" not in value
                )
            ]
            for i in range(len(attributes[0])):
                if "Room" in str(attributes[0][i]):
                    attributes[0][i] = (
                        str(attributes[0][i]).split("Room")[0].replace(", ", " ")
                    )
            org = Organization(
                chamber=chamber,
                classification="committee",
                name=str(attributes[0][0].decode()),
            )
            if len(attributes[0]) > 5:
                org.add_contact_detail(
                    type="email",
                    value=str(attributes[0][4].decode()),
                    note="District Office",
                )
                org.add_contact_detail(
                    type="voice",
                    value=str(attributes[0][5].decode()),
                    note="District Office",
                )
            else:
                org.add_contact_detail(
                    type="email",
                    value=str(attributes[0][3].decode()),
                    note="District Office",
                )
                org.add_contact_detail(
                    type="voice",
                    value=str(attributes[0][4].decode()),
                    note="District Office",
                )
            org.add_source(url)
            # membership
            td_text = list()
            for td in row[1].xpath("div") + row[2].xpath("div"):
                td_text += td.itertext()
            members = list(
                value
                for value in td_text
                if value != " " and value != "\n" and value != ","
            )
            role = "member"
            for member in members:
                if member in ["Chair", "Vice Chair"]:
                    role = member.lower()
                    continue
                elif member.strip():
                    org.add_member(member.strip(), role=role)
                    role = "member"
            yield org

    def scrape_joint_committees(self):
        page = self.get(_JOINT_URL).text
        html = lxml.html.fromstring(page)
        html.make_links_absolute(_JOINT_URL)
        joint_li = html.xpath('//div[contains(h2, "Joint")]/ul/li')
        for li in joint_li:
            name, url = li[0].text, li[0].get("href")
            yield self.get_joint_committees_data(name, url)

    def scrape(self, chamber=None):
        """
        Scrapes Idaho committees for the latest term.
        """
        # self.validate_term(term, latest_only=True)
        if chamber in ["upper", "lower"]:
            yield from self.scrape_committees(chamber)
        elif chamber == "joint":
            yield from self.scrape_joint_committees()
        else:
            yield from self.scrape_committees("upper")
            yield from self.scrape_committees("lower")
            yield from self.scrape_joint_committees()
