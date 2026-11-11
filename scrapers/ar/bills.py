import itertools
import re
import datetime
import pytz
import urllib.parse

from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.exceptions import EmptyScrape

import lxml.html

from .common import get_slug_for_session, get_biennium_year

TIMEZONE = pytz.timezone("US/Central")
_AR_ORGANIZATION_ENTITY_NAME_KEYWORDS = [
    "Committee",
    "House Management",
    "Senate Efficiency",
]


class ARBillScraper(Scraper):
    sponsors_chamber_cache = {}

    def scrape(self, chamber=None, session=None):

        self.slug = get_slug_for_session(session)

        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                self.session_name = i["name"]
                self.biennium = get_biennium_year(self.session_name)

        session_year = int(self.slug[:4])
        odd_year = session_year if session_year % 2 else session_year - 1
        self.biennium_session = urllib.parse.quote_plus(f"{odd_year}/{self.slug}")

        url = (
            "https://www.arkleg.state.ar.us/Bills/SearchByRange"
            f"?ddBienniumSession={self.biennium_session}"
        )
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)
        type_urls = sorted(
            set(
                page.xpath(
                    "//a[contains(@href, '/Bills/ViewBills?type=') and "
                    f"contains(@href, 'ddBienniumSession={self.biennium_session}')]/@href"
                )
            )
        )

        self.seen = set()
        for type_url in type_urls:
            bill_chamber = {"H": "lower", "S": "upper"}[
                re.search(r"type=([HS])", type_url).group(1)
            ]
            if chamber and bill_chamber != chamber:
                continue
            yield from self.scrape_bill_list(type_url, bill_chamber, session)

        if not self.seen:
            raise EmptyScrape

    def scrape_bill_list(self, type_url, chamber, session):
        for start in itertools.count(0, 20):
            page = lxml.html.fromstring(self.get(f"{type_url}&start={start}").text)
            new_rows = []
            for row in page.xpath(
                "//div[@role='row'][.//a[starts-with(@aria-label, 'Bill Number ')]]"
            ):
                measureno = row.xpath(
                    "string(.//a[starts-with(@aria-label, 'Bill Number ')])"
                ).strip()
                if measureno not in self.seen:
                    self.seen.add(measureno)
                    new_rows.append((measureno, row.xpath("normalize-space(div[2])")))
            if not new_rows:
                break
            for measureno, title in new_rows:
                yield from self.scrape_bill(measureno, title, chamber, session)

    def scrape_bill(self, measureno, title, chamber, session):
        bill_id = re.sub(r"^([A-Z]+)(\d+)$", r"\1 \2", measureno)

        type_spec = re.match(r"(H|S)([A-Z]+)\s", bill_id).group(2)
        bill_type = {
            "B": "bill",
            "R": "resolution",
            "JR": "joint resolution",
            "CR": "concurrent resolution",
            "MR": "memorial",
            "CMR": "concurrent memorial",
        }[type_spec]

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )

        # need year before if it's a fiscal or special session beyond first
        year = session[0:4]
        if len(session) > 4 and session[-1] != "1":
            year = int(year) - 1
        bill_url = bill_id.replace(" ", "")

        # versions for special sessions have a different format
        is_special = True if len(session) > 5 else False
        if is_special:
            version_url = f"https://www.arkleg.state.ar.us/Bills/FTPDocument?path=%2FBills%2F{self.slug}%2FPublic%2F{bill_url}.pdf"
        else:
            version_url = f"https://www.arkleg.state.ar.us/assembly/{year}/{self.slug}/Bills/{bill_url}.pdf"
        bill.add_version_link(bill_id, version_url, media_type="application/pdf")

        yield from self.scrape_bill_page(bill)

        yield bill

    def classify_action(self, action):
        action_type = []
        if action.startswith("Filed"):
            action_type.append("introduction")
        elif action.startswith("Read first time") or action.startswith(
            "Read the first time"
        ):
            action_type.append("reading-1")
        if re.match("Read the first time, .*, read the second time", action):
            action_type.append("reading-2")
        elif action.startswith("Read the third time and passed"):
            action_type.append("passage")
            action_type.append("reading-3")
        elif action.startswith("Read the third time"):
            action_type.append("reading-3")
        elif action.startswith("DELIVERED TO GOVERNOR"):
            action_type.append("executive-receipt")
        elif action.startswith("Notification"):
            action_type.append("executive-signature")
        elif "vetoed by the Governor" in action or "Governor Vetoed" in action:
            action_type.append("executive-veto")
        elif "override" and "veto passed" in action.casefold():
            action_type.append("veto-override-passage")
            action_type.append("passage")
        elif "override" and "veto failed" in action.casefold():
            action_type.append("veto-override-failure")
            action_type.append("failure")

        if "referred to" in action:
            action_type.append("referral-committee")

        if "Returned by the Committee" in action:
            if "recommendation that it Do Pass" in action:
                action_type.append("committee-passage-favorable")
            else:
                action_type.append("committee-passage")

        if re.match(r"Amendment No\. \d+ read and adopted", action):
            action_type.append("amendment-introduction")
            action_type.append("amendment-passage")

        return action_type

    def get_entity_name(self, link):
        entity_type = "person"
        if any(keyword in link for keyword in _AR_ORGANIZATION_ENTITY_NAME_KEYWORDS):
            entity_type = "organization"
        return entity_type

    def get_chamber(self, name):
        chamber = ""
        if "senator" in name.lower() or "senate" in name.lower():
            chamber = "upper"
        elif "representative" in name.lower() or "house" in name.lower():
            chamber = "lower"
        elif "joint" in name.lower():
            chamber = "legislature"
        return chamber

    def scrape_bill_page(self, bill):
        measureno = bill.identifier.replace(" ", "")
        url = (
            "https://www.arkleg.state.ar.us/Bills/Detail"
            f"?id={measureno}&ddBienniumSession={self.biennium_session}"
        )
        page = self.get(url).text
        bill.add_source(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        history_rows = page.xpath(
            "//h3[contains(., 'Bill Status History')]"
            "/following::div[@id='tableDataWrapper'][1]"
            "/div[contains(@class, 'tableRow')]"
        )
        # newest first on the page
        for row in reversed(history_rows):
            actor = {"House": "lower", "Senate": "upper"}[
                row.xpath("normalize-space(div[1])")
            ]
            date = TIMEZONE.localize(
                datetime.datetime.strptime(
                    row.xpath("normalize-space(div[2])"), "%m/%d/%Y %I:%M:%S %p"
                )
            )
            action = row.xpath("normalize-space(div[3])")
            bill.add_action(
                action or "[No text provided]",
                date,
                chamber=actor,
                classification=self.classify_action(action),
            )

        primary_sponsors_path = page.xpath(
            "//div[text()[contains(.,'Lead Sponsor:')]]/../div[2]/a"
        )
        for sponsor_path in primary_sponsors_path:
            primary_sponsors = sponsor_path.text_content().strip()
            if primary_sponsors == "":
                continue

            primary_sponsors_link = sponsor_path.attrib["href"]
            chamber = self.scrape_chamber(primary_sponsors_link)

            bill.add_sponsorship(
                primary_sponsors,
                classification="primary",
                entity_type=self.get_entity_name(primary_sponsors_link),
                primary=True,
                chamber=chamber,
            )

        other_primary_sponsors_path = page.xpath(
            "//div[text()[contains(.,'Other Primary Sponsor:')]]/../div[2]/a"
        )
        for sponsor_path in other_primary_sponsors_path:
            other_primary_sponsors = sponsor_path.text_content().strip()
            other_primary_sponsors_link = sponsor_path.attrib["href"]
            chamber = self.scrape_chamber(other_primary_sponsors_link)

            bill.add_sponsorship(
                other_primary_sponsors,
                classification="primary",
                entity_type=self.get_entity_name(other_primary_sponsors_link),
                primary=True,
                chamber=chamber,
            )

        cosponsor_path = page.xpath(
            "//div[text()[contains(.,'CoSponsors:')]]/../div[2]/a"
        )
        for sponsor_path in cosponsor_path:
            cosponsor = sponsor_path.text_content().strip()
            cosponsor_link = sponsor_path.attrib["href"]
            chamber = self.scrape_chamber(cosponsor_link)

            bill.add_sponsorship(
                cosponsor,
                classification="cosponsor",
                entity_type=self.get_entity_name(cosponsor_link),
                primary=False,
                chamber=chamber,
            )

        amendment_path = page.xpath(
            "//h3[text()[contains(.,'Amendments')]]/../../.."
            "/div/div/div[contains(@class, 'row tableRow')"
            " and descendant::div[contains(span, 'Amendment Number:')]]"
        )
        for row in amendment_path:
            div = list(row)
            amendment_number = (
                div[1].text_content().replace("Amendment Number:", "").strip()
            )
            for a in div[4]:
                amendment_url = a.attrib["href"].strip()
            amendment_date = div[3].text_content().strip()
            date = TIMEZONE.localize(
                datetime.datetime.strptime(amendment_date, "%m/%d/%Y %I:%M:%S %p")
            )
            date = "{:%Y-%m-%d}".format(date)
            bill.add_version_link(
                note="Amendment " + amendment_number,
                url=amendment_url,
                classification="amendment",
                date=date,
                media_type="application/pdf",
            )

        acts_link_xpath = (
            "//a[contains(@aria-label, 'Act') and contains(@href, '/Acts/')"
            " and contains(@aria-label,'.PDF')]"
        )

        if page.xpath(acts_link_xpath):
            act_link = page.xpath(acts_link_xpath)[0]
            act_link_parent = "//div[a[contains(@aria-label, 'Act') and contains(@href, '/Acts/') and contains(@aria-label,'.PDF')]]/text()"
            # two text matches here, before the image (blank), and after
            act_num = page.xpath(act_link_parent)[1].strip()
            act_num = f"Act {act_num}"
            act_url = act_link.xpath("@href")[0]
            bill.add_version_link(
                act_num,
                act_url,
                media_type="application/pdf",
                classification="became-law",
            )
            bill.add_citation(
                f"AR Acts, {self.biennium} - {self.session_name}",
                act_num,
                citation_type="chapter",
                url=act_url,
            )

        FI_path = page.xpath(
            "//h3[text()[contains(.,'DFA Fiscal Impacts')"
            " or contains(.,'BLR Fiscal Impacts')"
            " or contains(.,'Other Fiscal Impacts')]]"
            "/../../../div/div[contains(@class, 'row tableRow')]"
        )
        for row in FI_path:
            div = list(row)
            FI_number = div[0].text_content().replace("FI Number:", "").strip()
            for a in div[3]:
                if isinstance(a, lxml.html.HtmlComment):
                    continue
                FI_url = a.attrib["href"].strip()

            FI_date = div[2].text_content().replace("Date Issued:", "").strip()
            date = TIMEZONE.localize(datetime.datetime.strptime(FI_date, "%m/%d/%Y"))
            date = "{:%Y-%m-%d}".format(date)
            bill.add_document_link(
                note=FI_number,
                url=FI_url,
                classification="fiscal-note",
                date=date,
                media_type="application/pdf",
            )

        study_path = page.xpath(
            "//h3[text()[contains(.,'Actuarial Cost Studies')]]"
            "/../../../div/following::div[contains(@class, 'row tableRow')"
            " and descendant::div[contains(span, 'Study Number')]]"
        )
        for row in study_path:
            div = list(row)
            study_number = div[0].text_content().replace("Study Number:", "").strip()
            for a in div[2]:
                study_url = a.attrib["href"].strip()
            study_date = div[1].text_content().replace("Date Issued:", "").strip()
            date = TIMEZONE.localize(
                datetime.datetime.strptime(study_date, "%m/%d/%Y %I:%M:%S %p")
            )
            date = "{:%Y-%m-%d}".format(date)
            bill.add_document_link(
                note=study_number,
                url=study_url,
                classification="fiscal-note",
                date=date,
                media_type="application/pdf",
            )

        for link in page.xpath(
            "//*[@id='tableDataWrapper']/div/div[4]/a[contains(@href, '/Bills/Votes?id=')]"
        ):
            date = link.xpath("normalize-space(string(../../div[2]))")
            date = TIMEZONE.localize(
                datetime.datetime.strptime(date, "%m/%d/%Y %I:%M:%S %p")
            )

            motion = link.xpath("string(../../div[3])")
            yield from self.scrape_vote(bill, date, motion, link.attrib["href"])

    def scrape_vote(self, bill, date, motion, url):
        page = self.get(url).text
        if "not yet official" in page or "No data found for the vote" in page:
            # Sometimes they link to vote pages before they go live
            pass

        else:
            page = lxml.html.fromstring(page)

            if "Senate" in url:
                actor = "upper"
            else:
                actor = "lower"

            votevals = ["yes", "no", "not voting", "other"]
            yes_count = int(
                page.xpath(
                    "substring-after(//*[@id='bodyContent']/div/div/div/b[contains(text(), 'Yeas')], ': ')"
                )
            )
            no_count = int(
                page.xpath(
                    "substring-after(//*[@id='bodyContent']/div/div/div/b[contains(text(), 'Nays')], ': ')"
                )
            )
            not_voting_count = int(
                page.xpath(
                    "substring-after(//*[@id='bodyContent']/div/div/div/b[contains(text(), 'Non Voting')], ': ')"
                )
            )
            other_count = int(
                page.xpath(
                    "substring-after(//*[@id='bodyContent']/div/div/div/b[contains(text(), 'Present')], ': ')"
                )
            )
            passed = yes_count > no_count + not_voting_count + other_count
            vote_type = []
            vote_type.append("passage")
            if "override" and "veto" in motion.casefold():
                vote_type.append("veto-override")
            vote = VoteEvent(
                start_date=date,
                motion_text=motion,
                result="pass" if passed else "fail",
                classification=vote_type,
                chamber=actor,
                bill=bill,
            )
            try:
                excused_count = int(
                    page.xpath(
                        "substring-after(//*[@id='bodyContent']/div/div/div/b[contains(text(), 'Excused')], ': ')"
                    )
                )
                vote.set_count("excused", excused_count)
                votevals.append("excused")
            except (ValueError, IndexError):
                pass
            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("not voting", not_voting_count)
            vote.set_count("other", other_count)
            vote.add_source(url)

            xpath = '//*[@id="bodyContent"]/div/div/div[(contains(@class, "voteList"))]'

            divs = page.xpath(xpath)

            for voteval, div in zip(votevals, divs):
                for a in div.xpath(".//a"):
                    name_path = a.attrib["href"].strip()
                    first_split = name_path.split("=")[1]
                    second_split = first_split.split("&")[0]
                    name = second_split.replace("+", " ")
                    if not name:
                        continue
                    else:
                        vote.vote(voteval, name)
            yield vote

    def scrape_chamber(self, url):
        if url in self.sponsors_chamber_cache:
            return self.sponsors_chamber_cache[url]

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        headers = page.xpath("//h1")
        if not headers:
            # Some legislator detail pages occasionally load without an <h1>
            # (transient errors/blocks). Fall back to an empty chamber rather
            # than failing the entire scrape.
            self.warning(f"No <h1> found on legislator page, skipping chamber: {url}")
            self.sponsors_chamber_cache[url] = ""
            return ""
        title = headers[0].text_content().strip()
        chamber = self.get_chamber(title)
        self.sponsors_chamber_cache[url] = chamber

        return chamber
