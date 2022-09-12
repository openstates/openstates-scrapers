import os
import re
import datetime
import collections
from urllib.parse import unquote_plus, parse_qsl, urlparse

import lxml.html

from openstates.utils import convert_pdf
from openstates.scrape import Scraper, Bill, VoteEvent
import scrapelib

from .actions import Categorizer


class _Url(object):
    """A url object that can be compared with other url orbjects
    without regard to the vagaries of casing, encoding, escaping,
    and ordering of parameters in query strings."""

    def __init__(self, url):
        parts = urlparse(url.lower())
        _query = frozenset(parse_qsl(parts.query))
        _path = unquote_plus(parts.path)
        parts = parts._replace(query=_query, path=_path)
        self.parts = parts

    def __eq__(self, other):
        return self.parts == other.parts

    def __hash__(self):
        return hash(self.parts)


class WVBillScraper(Scraper):
    categorizer = Categorizer()

    _special_names = {
        "20161S": "1X",
        "2017": "rs",
        "20171S": "1X",
        "20172S": "2X",
        "20181S": "1x",
        "20182S": "2x",
        "20191S": "1x",
        "20211S": "1x",
        "20212S": "2x",
        "20213S": "3x",
        "20221S": "1X",
        "20222S": "2X",
        "20223S": "3X",
        "20224S": "4X",
    }

    bill_types = {
        "B": "bill",
        "R": "resolution",
        "CR": "concurrent resolution",
        "JR": "joint resolution",
    }

    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        if chamber == "lower":
            orig = "h"
        else:
            orig = "s"

        # scrape bills
        if "special" in self.jurisdiction.legislative_sessions[-1]["name"].lower():
            url = (
                "http://www.legis.state.wv.us/Bill_Status/Bills_all_bills.cfm?"
                "year=%s&sessiontype=%s&btype=bill&orig=%s"
                % (
                    self.jurisdiction.legislative_sessions[-1]["_scraped_name"],
                    self._special_names[session],
                    orig,
                )
            )
        else:
            url = (
                "http://www.legis.state.wv.us/Bill_Status/Bills_all_bills.cfm?"
                "year=%s&sessiontype=RS&btype=bill&orig=%s" % (session, orig)
            )

        page = lxml.html.fromstring(self.get(url, timeout=80).text)
        page.make_links_absolute(url)

        # Debug code to scrape an individual bill:
        # yield from self.scrape_bill(
        #     session,
        #     "upper",
        #     "SB 500",
        #     "test",
        #     "http://www.legis.state.wv.us/Bill_Status/Bills_history.cfm?input=500&year=2020&sessiontype=RS&btype=bill",
        # )

        for link in page.xpath("//a[contains(@href, 'Bills_history')]"):
            bill_id = link.xpath("string()").strip()
            title = link.xpath("string(../../td[2])").strip()
            if not title:
                self.warning("Can't find bill title, using ID as title")
                title = bill_id
            yield from self.scrape_bill(
                session, chamber, bill_id, title, link.attrib["href"]
            )

        # scrape resolutions
        if "special" in self.jurisdiction.legislative_sessions[-1]["name"].lower():
            res_url = (
                "http://www.legis.state.wv.us/Bill_Status/res_list.cfm?year=%s"
                "&sessiontype=%s&btype=res"
                % (
                    self.jurisdiction.legislative_sessions[-1]["_scraped_name"],
                    self._special_names[session],
                )
            )
        else:
            res_url = (
                "http://www.legis.state.wv.us/Bill_Status/res_list.cfm?year=%s"
                "&sessiontype=rs&btype=res"
                % (self.jurisdiction.legislative_sessions[-1]["_scraped_name"])
            )

        doc = lxml.html.fromstring(self.get(res_url, timeout=80).text)
        doc.make_links_absolute(res_url)

        # check for links originating in this house
        for link in doc.xpath('//a[contains(@href, "houseorig=%s")]' % orig):
            bill_id = link.xpath("string()").strip()
            title = link.xpath("string(../../td[2])").strip()
            if not title:
                self.warning("Can't find bill title, using ID as title")
                title = bill_id
            yield from self.scrape_bill(
                session, chamber, bill_id, title, link.attrib["href"]
            )

    def scrape_bill(
        self,
        session,
        chamber,
        bill_id,
        title,
        url,
        strip_sponsors=re.compile(r"\s*\(.{,50}\)\s*").sub,
    ):

        html = self.get(url).text

        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        bill_type = self.bill_types[bill_id.split()[0][1:]]

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )
        bill.add_source(url)

        xpath = '//strong[contains(., "SUBJECT")]/../' "following-sibling::td/a/text()"
        bill.subject = page.xpath(xpath)

        for version in self.scrape_versions(session, chamber, page, bill_id):
            bill.add_version_link(**version)

        self.scrape_amendments(page, bill)

        # Resolution pages have different html.
        values = {}
        trs = page.xpath('//div[@id="bhistcontent"]/table/tr')
        for tr in trs:
            heading = tr.xpath("td/strong/text()")
            if heading:
                heading = heading[0]
            else:
                continue
            value = tr.text_content().replace(heading, "").strip()
            values[heading] = value

        # summary was always same as title
        # bill['summary'] = values['SUMMARY:']

        # Add primary sponsor.
        primary = strip_sponsors("", values.get("LEAD SPONSOR:", ""))
        if primary:
            bill.add_sponsorship(
                name=primary.strip(),
                classification="primary",
                entity_type="person",
                primary=True,
            )

        # Add cosponsors.
        if values.get("SPONSORS:"):
            sponsors = strip_sponsors("", values["SPONSORS:"])
            sponsors = re.split(r", (?![A-Z]\.)", sponsors)
            for name in sponsors:
                name = name.strip(", \n\r")
                if name:
                    # Fix name splitting bug where "Neale, D. Hall"
                    match = re.search(r"(.+?), ([DM]\. Hall)", name)
                    if match:
                        for name in match.groups():
                            bill.add_sponsorship(
                                name=name.strip(),
                                classification="cosponsor",
                                entity_type="person",
                                primary=False,
                            )
                    else:
                        bill.add_sponsorship(
                            name=name.strip(),
                            classification="cosponsor",
                            entity_type="person",
                            primary=False,
                        )

        for link in page.xpath("//a[contains(@href, 'votes/house')]"):
            yield from self.scrape_house_vote(bill, link.attrib["href"])

        for tr in reversed(
            page.xpath("//table[@class='tabborder']/descendant::tr")[1:]
        ):
            tds = tr.xpath("td")
            if len(tds) < 3:
                continue

            chamber_letter = tds[0].text_content()
            chamber = {"S": "upper", "H": "lower"}[chamber_letter]

            # Index of date info no longer varies on resolutions.
            date = tds[2].text_content().strip()
            date = datetime.datetime.strptime(date, "%m/%d/%y").date()

            action = tds[1].text_content().strip()
            if action.lower().startswith("passed senate"):
                for href in tds[1].xpath("a/@href"):
                    yield from self.scrape_senate_vote(bill, href, date)

            attrs = dict(
                chamber=chamber, description=action, date=date.strftime("%Y-%m-%d")
            )
            temp = self.categorizer.categorize(action)
            related_entities = []
            for key, values in temp.items():
                if key != "classification":
                    for value in values:
                        related_entities.append({"type": key, "name": value})
            attrs.update(
                classification=temp["classification"], related_entities=related_entities
            )
            bill.add_action(**attrs)

        yield bill

    def scrape_house_vote(self, bill, url):
        try:
            filename, resp = self.urlretrieve(url, timeout=80)
        except scrapelib.HTTPError:
            self.warning("missing vote file %s" % url)
            return
        text = convert_pdf(filename, "text")
        os.remove(filename)

        lines = text.splitlines()

        vote_type = None
        votes = collections.defaultdict(list)
        date = None

        for idx, line in enumerate(lines):
            line = line.rstrip().decode("utf-8")
            match = re.search(r"(\d+)/(\d+)/(\d{4,4})$", line)
            if match:
                date = datetime.datetime.strptime(match.group(0), "%m/%d/%Y")
                continue

            match = re.match(r"\s+YEAS: (\d+)\s+NAYS: (\d+)\s+NOT VOTING: (\d+)", line)
            if match:
                motion = (lines[idx - 2].strip()).decode("utf-8")
                if not motion:
                    self.warning("No motion text found for vote")
                    motion = "PASSAGE"
                yes_count, no_count, other_count = [int(g) for g in match.groups()]

                exc_match = re.search(r"EXCUSED: (\d+)", line)
                if exc_match:
                    other_count += int(exc_match.group(1))

                if line.endswith("ADOPTED") or line.endswith("PASSED"):
                    passed = True
                else:
                    passed = False

                continue

            match = re.match(
                r"(YEAS|NAYS|NOT VOTING|PAIRED|EXCUSED):\s+(\d+)\s*$", line
            )
            if match:
                vote_type = {
                    "YEAS": "yes",
                    "NAYS": "no",
                    "NOT VOTING": "other",
                    "EXCUSED": "other",
                    "PAIRED": "paired",
                }[match.group(1)]
                continue

            if vote_type == "paired":
                for part in line.split("   "):
                    part = part.strip()
                    if not part:
                        continue
                    name, pair_type = re.match(r"([^\(]+)\((YEA|NAY)\)", line).groups()
                    name = name.strip()
                    if pair_type == "YEA":
                        votes["yes"].append(name)
                    elif pair_type == "NAY":
                        votes["no"].append(name)
            elif vote_type:
                for name in line.split("   "):
                    name = name.strip()
                    if not name:
                        continue
                    votes[vote_type].append(name)
        if date:
            vote = VoteEvent(
                chamber="lower",
                start_date=date.strftime("%Y-%m-%d"),
                motion_text=motion,
                result="pass" if passed else "fail",
                classification="passage",
                bill=bill,
            )

            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("other", other_count)
            vote.add_source(url)
            vote.dedupe_key = url

            for key, values in votes.items():
                for value in values:
                    if "Committee" in value:
                        continue
                    if "*" in value:
                        value = value.replace("*", "")
                    vote.vote(key, value)

            yield vote
        else:
            self.warning("Syntax Error/Warning using 'convert_pdf'")

    def scrape_senate_vote(self, bill, url, date):
        try:
            filename, resp = self.urlretrieve(url)
        except scrapelib.HTTPError:
            self.warning("missing vote file %s" % url)
            return

        vote = VoteEvent(
            chamber="upper",
            start_date=date.strftime("%Y-%m-%d"),
            motion_text="Passage",
            # setting 'fail' for now.
            result="fail",
            classification="passage",
            bill=bill,
        )
        vote.add_source(url)
        vote.dedupe_key = url

        text = convert_pdf(filename, "text").decode("utf-8")
        os.remove(filename)

        if re.search(r"Yea:\s+\d+\s+Nay:\s+\d+\s+Absent:\s+\d+", text):
            yield from self.scrape_senate_vote_3col(bill, vote, text, url, date)
            return

        data = re.split(r"(Yea|Nay|Absent)s?:", text)[::-1]
        data = list(filter(None, data))
        keymap = dict(yea="yes", nay="no")
        actual_vote = collections.defaultdict(int)
        vote_count = {"yes": 0, "no": 0, "other": 0}
        while True:
            if not data:
                break
            vote_val = data.pop()
            key = keymap.get(vote_val.lower(), "other")
            values = data.pop()
            for name in re.split(r"(?:[\s,]+and\s|[\s,]{2,})", values):
                if name.lower().strip() == "none.":
                    continue
                name = name.replace("..", "")
                name = re.sub(r"\.$", "", name)
                name = name.strip("-1234567890 \n")
                if not name:
                    continue
                vote.vote(key, name)
                actual_vote[vote_val] += 1
                vote_count[key] += 1
            assert actual_vote[vote_val] == vote_count[key]

        for key, value in vote_count.items():
            vote.set_count(key, value)
        # updating result with actual value
        vote.result = (
            "pass"
            if vote_count["yes"] > (vote_count["no"] + vote_count["other"])
            else "fail"
        )

        yield vote

    def scrape_senate_vote_3col(self, bill, vote, text, url, date):
        """Scrape senate votes like this one:
        http://www.legis.state.wv.us/legisdocs/2013/RS/votes/senate/02-26-0001.pdf
        """
        counts = dict(re.findall(r"(Yea|Nay|Absent): (\d+)", text))
        lines = filter(None, text.splitlines())
        actual_vote = collections.defaultdict(int)
        yes_count = 0
        no_count = 0
        other_count = 0
        for line in lines:
            vals = re.findall(r"(?<!\w)(Y|N|A)\s+((?:\S+ ?)+)", line)
            for vote_val, name in vals:
                vote_val = vote_val.strip()
                name = name.strip()
                if vote_val == "Y":
                    # Fix for "Class Y special hunting" in
                    # http://www.wvlegislature.gov/legisdocs/2020/RS/votes/senate/01-27-0033.pdf
                    if "Class Y" in line:
                        continue

                    vote.yes(name)
                    yes_count += 1
                elif vote_val == "N":
                    vote.no(name)
                    no_count += 1
                else:
                    vote.vote("other", name)
                    other_count += 1
                actual_vote[vote_val] += 1
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("other", other_count)
        # updating result with actual value
        vote.result = "pass" if yes_count > (no_count + other_count) else "fail"

        assert yes_count == int(counts["Yea"])
        assert no_count == int(counts["Nay"])
        assert other_count == int(counts["Absent"])

        yield vote

    def _scrape_versions_normally(self, session, chamber, page, bill_id):
        """This first method assumes the bills versions are hyperlinked
        on the bill's status page.
        """
        for link in page.xpath("//a[starts-with(@title, 'HTML -')]"):
            # split name out of HTML - Introduced Version - SB 1
            name = link.xpath("@title")[0].split("-")[1].strip()
            yield {"note": name, "url": link.get("href"), "media_type": "text/html"}
        for link in page.xpath("//a[starts-with(@title, 'PDF -')]"):
            # split name out of HTML - Introduced Version - SB 1
            name = link.xpath("@title")[0].split("-")[1].strip()
            yield {
                "note": name,
                "url": link.get("href"),
                "media_type": "application/pdf",
            }
        for link in page.xpath("//a[starts-with(@title, 'DOCX -')]"):
            # split name out of HTML - Introduced Version - SB 1
            name = link.xpath("@title")[0].split("-")[1].strip()
            yield {
                "note": name,
                "url": link.get("href"),
                "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }

    def scrape_amendments(self, page, bill):
        for row in page.xpath(
            '//a[contains(@class,"billbundle") and contains(text(),"adopted")]'
        ):
            version_name = row.xpath("string(.)").strip()
            version_url = row.xpath("@href")[0]
            bill.add_version_link(
                version_name, version_url, media_type="text/html", on_duplicate="ignore"
            )

    def scrape_versions(self, session, chamber, page, bill_id):
        """
        Return all available version documents for this bill_id.
        """
        res = []
        cache = set()

        # Scrape .htm and .wpd versions listed in the detail page.
        for data in self._scrape_versions_normally(session, chamber, page, bill_id):
            _url = _Url(data["url"])
            if _url not in cache:
                cache.add(_url)
                res.append(data)

        return res
