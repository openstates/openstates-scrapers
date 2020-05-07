import collections
from openstates.scrape import Scraper, Organization
from utils import LXMLMixin

base_url = "http://www.nmlegis.gov/Committee/"

Member = collections.namedtuple("Member", "name role chamber")


def clean_committee_name(name_to_clean):
    head, _sep, tail = (
        name_to_clean.replace("House ", "")
        .replace("Senate ", "")
        .replace("Subcommittee", "Committee")
        .rpartition(" Committee")
    )

    return head + tail


class NMCommitteeScraper(Scraper, LXMLMixin):
    jurisdiction = "nm"

    def scrape(self, chamber=None):
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
                    self.warning(
                        "No legislative committee found at " "{}".format(committee_url)
                    )
