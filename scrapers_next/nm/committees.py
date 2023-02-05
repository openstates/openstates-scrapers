import collections
import logging

import requests
from lxml import html
from openstates.scrape import Scraper, Organization
from spatula import HtmlListPage
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, URL, SkipItem
from openstates.models import ScrapeCommittee

from scrapers.utils import LXMLMixin

base_url = "http://www.nmlegis.gov/Committee/"

Member = collections.namedtuple("Member", "name role chamber")


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input
        members_xpath = '//table[@id="MainContent_formViewCommitteeInformation_gridViewCommitteeMembers"]/tbody/tr'
        member_nodes = XPath(members_xpath).match(self.root)

        print([x for x in member_nodes])

        com.add_source(
            self.source.url,
            note="Committee Details API",
        )
        com.add_link(
            self.source.url,
            note="homepage",
        )
        return com


class CommitteeList(HtmlListPage):
    home = "http://www.nmlegis.gov/Committee/"
    source = URL(
        f"{home}Senate_Standing",
        timeout=10,
    )
    chamber = "upper"

    def clean_committee_name(self, name_to_clean):
        head, _sep, tail = (
            name_to_clean.replace("House ", "")
            .replace("Senate ", "")
            .replace("Subcommittee", "Committee")
            .rpartition(" Committee")
        )

        return head + tail

    def process_page(self):
        senate_href_xpath = '//a[contains(@id, "MainContent_gridViewSenateCommittees_linkSenateCommittee")]'
        house_href_xpath = '//a[contains(@id, "MainContent_gridViewHouseCommittees_linkHouseCommittee")]'
        interim_href_xpath = '//a[contains(@id, "MainContent_gridViewCommittees_linkCommittee")]'
        all_committees = {self.chamber: XPath(senate_href_xpath).match(self.root)}
        other_coms_info = {"lower": {house_href_xpath: f"{self.home}House_Standing"},
                           "legislature": {interim_href_xpath: f"{self.home}interim"}}

        for chamber, item in other_coms_info.items():
            for xpath, url in item.items():
                self.root = html.fromstring(requests.get(url).content)
                all_committees[chamber] = XPath(xpath).match(self.root)

        for chamber, elems in all_committees.items():
            for item in elems:
                name, com_url = item.text, item.get("href")

                if "subcommittee" in name.lower():
                    classification = "subcommittee"
                    parent = name.lower().replace("subcommittee", "").title()
                else:
                    parent = None
                    classification = "committee"

                com = ScrapeCommittee(
                    name=self.clean_committee_name(name).title(),
                    chamber=chamber,
                    parent=parent,
                    classification=classification,
                )
                print(com_url)
                yield CommitteeDetail(
                    com, source=URL(com_url, timeout=30)
                )


class NMCommitteeScraper(Scraper, LXMLMixin):
    jurisdiction = "nm"

    def process_page(self, chamber=None):
        if chamber:
            chambers = [chamber]
        else:
            chambers = ["upper", "lower", "legislature"]

        # Xpath query string format for legislative chamber committee urls
        base_xpath = (
            '//table[@id="MainContent_gridView{0}Committees"]//a'
            '[contains(@id, "MainContent_gridView{1}Committees_link'
            '{2}Committee")]/@href'
        )
        chamber_paths = {
            "upper": {
                "url": "{}Senate_Standing".format(base_url),
                "chamber_xpath": base_xpath.format("Senate", "Senate", "Senate"),
            },
            "lower": {
                "url": "{}House_Standing".format(base_url),
                "chamber_xpath": base_xpath.format("House", "House", "House"),
            },
            "legislature": {
                "url": "{}Interim".format(base_url),
                "chamber_xpath": base_xpath.format("", "", ""),
            },
        }

        for chamber in chambers:
            page = self.lxmlize(chamber_paths[chamber]["url"])

            committee_urls = self.get_nodes(
                page, chamber_paths[chamber]["chamber_xpath"]
            )

            for committee_url in committee_urls:
                committee_page = self.lxmlize(committee_url)

                c_name = (
                    committee_page.xpath(
                        '//li/a[contains(@id, "siteMapBreadcrumbs_lnkPage_")]'
                    )[-1]
                    .text_content()
                    .strip()
                )

                if c_name:
                    members_xpath = (
                        '//table[@id="MainContent_formView'
                        "CommitteeInformation_grid"
                        'ViewCommitteeMembers"]/tbody/tr'
                    )
                    member_nodes = self.get_nodes(committee_page, members_xpath)

                    tds = {"title": 0, "name": 1, "role": 3}

                    members = []

                    for member_node in member_nodes:
                        m_title = member_node[tds["title"]].text_content()
                        m_name = self.get_node(
                            member_node[tds["name"]],
                            ".//a[contains(@href, " '"/Members/Legislator?SponCode=")]',
                        ).text_content()

                        role = member_node[tds["role"]].text_content()

                        if m_title == "Senator":
                            m_chamber = "upper"
                        elif m_title == "Representative":
                            m_chamber = "lower"
                        else:
                            m_chamber = None

                        if role in (
                                "Chair",
                                "Co-Chair",
                                "Vice Chair",
                                "Member",
                                "Advisory",
                                "Ranking Member",
                        ):
                            if chamber == "legislature":
                                m_role = "interim {}".format(role.lower())
                            else:
                                m_role = role.lower()
                        else:
                            m_role = None

                        if m_role:
                            members.append(
                                Member(name=m_name, role=m_role, chamber=m_chamber)
                            )

                    # Interim committees are collected during the scraping
                    # for joint committees, and most interim committees
                    # have members from both chambers. However, a small
                    # number of interim committees (right now, just 1) have
                    # only members from one chamber, so the chamber is set
                    # to their chamber instead of 'legislature' for those
                    # committees.
                    if chamber == "legislature":
                        m_chambers = set([mem.chamber for mem in members])
                        if len(m_chambers) == 1:
                            chamber = m_chambers.pop()
                    committee = Organization(
                        name=clean_committee_name(c_name),
                        chamber=chamber,
                        classification="committee",
                    )
                    for member in members:
                        committee.add_member(member.name, member.role)
                    committee.add_source(committee_url)
                    if not committee._related:
                        self.warning(
                            "skipping blank committee {0} "
                            "at {1}".format(c_name, committee_url)
                        )
                    else:
                        yield committee

                else:
                    logging.warning(
                        "No legislative committee found at " "{}".format(committee_url)
                    )


if __name__ == '__main__':
    s = CommitteeList()
    for i in s.do_scrape():
        print(i)
