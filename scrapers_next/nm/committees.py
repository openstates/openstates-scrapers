from spatula import HtmlPage, HtmlListPage, XPath, SelectorError, URL, SkipItem
import requests
from lxml import html
from openstates.models import ScrapeCommittee


class UnknownSubCommFound(BaseException):
    def __init__(self, com_name):
        super().__init__(f"unknown for subcommittee found: {com_name}")


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input
        try:
            name_xpath = '//table[@id="MainContent_formViewCommitteeInformation_gridViewCommitteeMembers"]/tbody/tr'
            mem_count = len(XPath(name_xpath).match(self.root))
        except SelectorError:
            raise SkipItem("empty committee")
        for i in range(1, mem_count):
            try:
                name = (
                    XPath(f"{name_xpath}[{i}]/td[2]")
                    .match(self.root)[0]
                    .text_content()
                    .strip()
                )
                role = (
                    XPath(f"{name_xpath}[{i}]/td[5]")
                    .match(self.root)[0]
                    .text_content()
                    .strip()
                )
            except SelectorError:
                raise SkipItem("empty committee")
            com.add_member(name, role)
        if not com.members:
            raise SkipItem("empty committee")

        com.add_source(
            self.source.url,
            note="Committee Details Page",
        )
        com.add_link(
            self.source.url,
            note="homepage",
        )
        return com


def clean_committee_name(name_to_clean):
    """
    Helper function to remove unwanted substrings and
    symbols from committee name, return cleaned name.
    """
    head, _sep, tail = (
        name_to_clean.lower()
        .title()
        .replace("'", "")
        .replace("House ", "")
        .replace("Senate ", "")
        .replace("Subcommittee", "")
        .rpartition(" Committee")
    )
    return head + tail


class CommitteeList(HtmlListPage):
    home = "http://www.nmlegis.gov/Committee/"
    source = URL(
        f"{home}Senate_Standing",
        timeout=10,
    )
    chamber = "upper"

    def process_page(self):
        senate_href_xpath = '//a[contains(@id, "MainContent_gridViewSenateCommittees_linkSenateCommittee")]'
        house_href_xpath = '//a[contains(@id, "MainContent_gridViewHouseCommittees_linkHouseCommittee")]'
        interim_href_xpath = (
            '//a[contains(@id, "MainContent_gridViewCommittees_linkCommittee")]'
        )
        all_committees = {self.chamber: XPath(senate_href_xpath).match(self.root)}
        other_coms_info = {
            "lower": {house_href_xpath: f"{self.home}House_Standing"},
            "legislature": {interim_href_xpath: f"{self.home}interim"},
        }

        for chamber, item in other_coms_info.items():
            for xpath, url in item.items():
                self.root = html.fromstring(requests.get(url).content)
                all_committees[chamber] = XPath(xpath).match(self.root)

        for chamber, elems in all_committees.items():
            for item in elems:
                name, com_url = item.text, item.get("href")
                if not com_url:
                    continue
                classification = "committee"
                parent = None
                if "subcommittee" in name.lower():
                    # Subcommittees that do not have clear parent committee
                    #  after investigation on NM legislature site will be
                    #  stored with classification as "committee"
                    if name.lower() in [
                        "transportation infrastructure revenue subcommittee",
                        "capitol security subcommittee",
                    ]:
                        pass
                    else:
                        raise UnknownSubCommFound(name)

                com = ScrapeCommittee(
                    name=clean_committee_name(name).title(),
                    chamber=chamber,
                    parent=parent,
                    classification=classification,
                )
                if not com_url.startswith("http"):
                    if com_url.startswith("/"):
                        com_url = f"{self.home.replace('Committee/', '')}{com_url}"
                    else:
                        com_url = f"{self.home}{com_url}"
                com.add_source(
                    self.home,
                    note="Committee Page from nmlegis.gov site",
                )
                yield CommitteeDetail(com, source=URL(com_url, timeout=30))
