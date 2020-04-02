import re
import datetime as datetime

import lxml.html
from openstates_core.scrape import Scraper, Organization

from openstates.utils import LXMLMixin


class MOCommitteeScraper(Scraper, LXMLMixin):
    _reps_url_base = "http://www.house.mo.gov/"
    _senate_url_base = "http://www.senate.mo.gov/"
    _no_members_text = "This Committee does not have any members"
    # Committee page markup changed in 2016.
    _is_post_2015 = False

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )
        session_start_date = datetime.datetime.strptime(
            meta["start_date"], "%Y-%m-%d"
        ).date()

        meta_2016 = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == "2016"
        )
        session_start_date_2016 = datetime.datetime.strptime(
            meta_2016["start_date"], "%Y-%m-%d"
        ).date()

        if session_start_date > datetime.date.today():
            self.info("{} session has not begun - ignoring.".format(session))
            return
        elif session_start_date >= session_start_date_2016:
            self._is_post_2015 = True

        # joint committees scraped as part of lower
        if chamber in ["upper", None]:
            yield from self._scrape_upper_chamber(session)
        if chamber in ["lower", None]:
            yield from self._scrape_lower_chamber(session)

    def _scrape_upper_chamber(self, session):
        self.info("Scraping upper chamber for committees.")

        chamber = "upper"

        if self._is_post_2015 and self.latest_session() != session:
            url = "{base}{year}web/standing-committees".format(
                base=self._senate_url_base, year=session[2:]
            )
            comm_container_id = "primary"
        elif session == self.latest_session():
            url = "{base}standing-committees".format(base=self._senate_url_base)
            comm_container_id = "primary"
        else:
            url = "{base}{year}info/com-standing.htm".format(
                base=self._senate_url_base, year=session[2:]
            )
            comm_container_id = "mainContent"

        page = self.lxmlize(url)

        comm_links = self.get_nodes(
            page, '//div[@id = "{}"]//p/a'.format(comm_container_id)
        )

        for comm_link in comm_links:
            # Normalize to uppercase - varies between "Assigned bills" and "Assigned Bills"
            if "ASSIGNED BILLS" in comm_link.text_content().upper():
                continue

            comm_link = comm_link.attrib["href"]

            if self._is_post_2015:
                if "web" not in comm_link:
                    continue
            else:
                if "comm" not in comm_link:
                    continue

            comm_page = self.lxmlize(comm_link)

            if self._is_post_2015:
                comm_name = self.get_node(
                    comm_page, '//h1[@class="entry-title"]/text()'
                )
                members = self.get_nodes(
                    comm_page, '//div[@id="bwg_standart_thumbnails_0"]/a'
                )
            else:
                comm_name = self.get_node(
                    comm_page, '//div[@id="mainContent"]/p/text()'
                )
                members = self.get_nodes(comm_page, '//div[@id="mainContent"]//td/a')

            comm_name = comm_name.replace(" Committee", "")
            comm_name = comm_name.strip()

            committee = Organization(
                comm_name, chamber=chamber, classification="committee"
            )

            for member in members:
                mem_link = member.attrib.get("href", "")
                if "mem" not in mem_link:
                    continue

                if self._is_post_2015:
                    mem_parts = self.get_node(
                        member, './/span[@class="bwg_title_spun2_0"]'
                    )

                mem_parts = member.text_content().strip().split(",")
                # Senator title stripping mainly for post-2015.
                mem_name = re.sub(r"^Senator[\s]+", "", mem_parts[0])

                # this one time, MO forgot the comma between
                # the member and his district. Very rarely relevant
                try:
                    int(mem_name[-4:-2])  # the district's # is in this position
                except ValueError:
                    pass
                else:
                    mem_name = " ".join(mem_name.split(" ")[0:-1])  # member name fixed

                    # ok, so this next line. We don't care about
                    # the first 2 elements of mem_parts anymore
                    # so whatever. But if the member as a role, we want
                    # to make sure there are 3 elements in mem_parts and
                    # the last one is actually the role. This sucks, sorry.
                    mem_parts.append(mem_parts[-1])

                mem_role = "member"
                if len(mem_parts) > 2:
                    mem_role = mem_parts[2].lower().split("    ")[0].strip()

                if mem_name == "":
                    continue

                committee.add_member(mem_name, role=mem_role)

            committee.add_source(url)
            committee.add_source(comm_link)

            yield committee

    def _scrape_lower_chamber(self, session):
        self.info("Scraping lower chamber for committees.")

        chamber = "lower"

        url = "{base}CommitteeHierarchy.aspx".format(base=self._reps_url_base)
        page_string = self.get(url).text
        page = lxml.html.fromstring(page_string)
        # Last tr has the date
        committee_links = page.xpath("//li//a")
        for committee_link in committee_links:
            committee_name = committee_link.text_content().strip()
            committee_url = committee_link.attrib.get("href")

            committee_url = "{base}{members}{url}".format(
                base=self._reps_url_base,
                members="MemberGridCluster.aspx?filter=compage&category=committee&",
                url=committee_url,
            )
            actual_chamber = chamber
            if "joint" in committee_name.lower():
                actual_chamber = "legislature"

            committee_name = committee_name.replace("Committee On ", "")
            committee_name = committee_name.replace("Special", "")
            committee_name = committee_name.replace("Select", "")
            committee_name = committee_name.replace("Special", "")
            committee_name = committee_name.replace("Joint", "")
            committee_name = committee_name.replace(" Committee", "")
            committee_name = committee_name.strip()

            committee = Organization(
                committee_name, chamber=actual_chamber, classification="committee"
            )

            committee_page_string = self.get(committee_url).text
            committee_page = lxml.html.fromstring(committee_page_string)
            # First tr has the title (sigh)
            mem_trs = committee_page.xpath(
                "//table[@id='gvMembers_DXMainTable']//tr[contains(@class, 'dxgvDataRow')]"
            )
            for mem_tr in mem_trs:
                mem_code = None
                mem_links = mem_tr.xpath("td/a[1]")

                mem_role_string = mem_tr.xpath("td[4]")[0].text_content().strip()

                if len(mem_links):
                    mem_code = mem_links[0].attrib.get("href")
                # Output is "Rubble, Barney, Neighbor"

                mem_parts = mem_tr.xpath("td[2]")[0].text_content().strip().split(",")
                if self._no_members_text in mem_parts:
                    continue
                mem_name = mem_parts[1].strip() + " " + mem_parts[0].strip()
                # Sometimes Senator abbreviation is in the name
                mem_name = mem_name.replace("Sen. ", "")
                mem_name = mem_name.replace("Rep. ", "")

                mem_role = "member"

                if len(mem_role_string) > 2:
                    mem_role = mem_role_string.lower()

                membership = committee.add_member(mem_name, role=mem_role)
                membership.extras = {"code": mem_code}

            committee.add_source(url)
            committee.add_source(committee_url)

            yield committee
