import re
import pytz
import urllib
import datetime
import collections

import lxml.html
from openstates.scrape import Scraper, Bill, VoteEvent

from . import utils
from . import actions


tz = pytz.timezone("America/New_York")


class PABillScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]

        match = re.search(r"#(\d+)", session)
        for chamber in chambers:
            if match:
                yield from self.scrape_session(chamber, session, int(match.group(1)))
            else:
                yield from self.scrape_session(chamber, session)

    def scrape_session(self, chamber, session, special=0):
        url = utils.bill_list_url(chamber, session, special)

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath('//a[contains(@href, "billinfo")]'):
            yield from self.parse_bill(chamber, session, special, link)

    def parse_bill(self, chamber, session, special, link):
        bill_num = link.text.strip()
        type_abbr = re.search("type=(B|R|)", link.attrib["href"]).group(1)

        if type_abbr == "B":
            btype = ["bill"]
        elif type_abbr == "R":
            btype = ["resolution"]

        bill_id = "%s%s %s" % (utils.bill_abbr(chamber), type_abbr, bill_num)

        url = utils.info_url(chamber, session, special, type_abbr, bill_num)
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        xpath = "/".join(
            [
                '//div[contains(@class, "BillInfo-ShortTitle")]',
                'div[@class="BillInfo-Section-Data"]',
            ]
        )

        if page.xpath(xpath):
            title = page.xpath(xpath).pop().text_content().strip()
        else:
            self.warning("Skipping {} {}, No title found".format(bill_id, url))
            return

        bill = Bill(
            bill_id,
            legislative_session=session,
            title=title,
            chamber=chamber,
            classification=btype,
        )
        bill.add_source(url)

        self.parse_bill_versions(bill, page)

        self.parse_history(
            bill,
            chamber,
            utils.history_url(chamber, session, special, type_abbr, bill_num),
        )

        # only fetch votes if votes were seen in history
        # if vote_count:
        yield from self.parse_votes(
            bill, utils.vote_url(chamber, session, special, type_abbr, bill_num)
        )

        # Dedupe sources.
        sources = bill.sources
        for source in sources:
            if 1 < sources.count(source):
                sources.remove(source)

        yield bill

    def parse_bill_versions(self, bill, page):
        for row in page.xpath('//table[contains(@class, "BillInfo-PNTable")]/tbody/tr'):
            printers_number = 0
            for a in row.xpath("td[2]/a"):
                mimetype = self.mimetype_from_class(a)

                href = a.attrib["href"]
                params = urllib.parse.parse_qs(href[href.find("?") + 1 :])

                for key in ("pn", "PrintersNumber"):
                    try:
                        printers_number = params[key][0]
                        break
                    except KeyError:
                        continue

                bill.add_version_link(
                    "Printer's No. %s" % printers_number,
                    href,
                    media_type=mimetype,
                    on_duplicate="ignore",
                )

            # House and Senate Amendments
            for a in row.xpath("td[3]/a"):
                self.scrape_amendments(bill, a.attrib["href"], "House")

            for a in row.xpath("td[4]/a"):
                self.scrape_amendments(bill, a.attrib["href"], "Senate")

            # House Fiscal Notes
            for a in row.xpath("td[5]/a"):
                mimetype = self.mimetype_from_class(a)
                href = a.attrib["href"]
                bill.add_document_link(
                    "House Fiscal Note",
                    href,
                    media_type=mimetype,
                    on_duplicate="ignore",
                )

            # Senate Fiscal Notes
            for a in row.xpath("td[6]/a"):
                mimetype = self.mimetype_from_class(a)
                href = a.attrib["href"]
                bill.add_document_link(
                    "Senate Fiscal Note",
                    href,
                    media_type=mimetype,
                    on_duplicate="ignore",
                )

            # Actuarial Notes
            for a in row.xpath("td[7]/a"):
                mimetype = self.mimetype_from_class(a)
                href = a.attrib["href"]
                bill.add_document_link(
                    "Actuarial Note {}".format(printers_number),
                    href,
                    media_type=mimetype,
                    on_duplicate="ignore",
                )

    def scrape_amendments(self, bill, link, chamber_pretty):
        html = self.get(link).text
        page = lxml.html.fromstring(html)
        page.make_links_absolute(link)

        for row in page.xpath('//div[contains(@class,"AmendList-Wrapper")]'):
            version_name = row.xpath(
                'div[contains(@class,"AmendList-AmendNo")]/text()'
            )[0].strip()
            version_name = "{} Amendment {}".format(chamber_pretty, version_name)
            for a in row.xpath('div[contains(@class,"AmendList-FileTypes")]/a'):
                mimetype = self.mimetype_from_class(a)
                version_link = a.attrib["href"]
                bill.add_version_link(
                    version_name,
                    version_link,
                    media_type=mimetype,
                    on_duplicate="ignore",
                )

    def parse_history(self, bill, chamber, url):
        bill.add_source(url)
        html = self.get(url).text
        tries = 0
        while "There is a problem generating the page you requested." in html:
            html = self.get(url).text
            if tries < 2:
                self.logger.warning("Internal error")
                return
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        self.parse_sponsors(bill, doc)
        self.parse_actions(bill, chamber, doc)
        # vote count
        return len(doc.xpath('//a[contains(@href, "rc_view_action1")]/text()'))

    def parse_sponsors(self, bill, page):
        first = True

        xpath = (
            "//div[contains(@class, 'BillInfo-PrimeSponsor')]"
            "/div[@class='BillInfo-Section-Data']/a"
        )
        sponsors = page.xpath(xpath)

        first = True
        for sponsor in sponsors:
            sponsor = sponsor.text_content()
            if first:
                sponsor_type = "primary"
                first = False
            else:
                sponsor_type = "cosponsor"

            if sponsor.find(" and ") != -1:
                dual_sponsors = sponsor.split(" and ")
                bill.add_sponsorship(
                    dual_sponsors[0].strip().title(),
                    classification=sponsor_type,
                    primary=sponsor_type == "primary",
                    entity_type="person",
                )
                bill.add_sponsorship(
                    dual_sponsors[1].strip().title(),
                    classification="cosponsor",
                    primary=sponsor_type == "primary",
                    entity_type="person",
                )
            else:
                name = sponsor.strip().title()
                bill.add_sponsorship(
                    name,
                    classification=sponsor_type,
                    primary=sponsor_type == "primary",
                    entity_type="person",
                )

    def parse_actions(self, bill, chamber, page):
        for tr in page.xpath("//table[@class='DataTable']//tr"):
            action = tr.xpath("string()").replace(u"\xa0", " ").strip()

            if action == "In the House":
                chamber = "lower"
                continue
            elif action == "In the Senate":
                chamber = "upper"
                continue
            elif action.startswith("(Remarks see"):
                continue

            match = re.match(
                r"(.*),\s+(\w+\.?\s+\d{1,2},\s+\d{4})( \(\d+-\d+\))?", action
            )

            if not match:
                continue

            action = match.group(1)
            date = utils.parse_action_date(match.group(2))
            types = list(actions.categorize(action))
            bill.add_action(
                action, tz.localize(date), chamber=chamber, classification=types
            )

    def parse_votes(self, bill, url):
        bill.add_source(url)
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for url in page.xpath("//a[contains(., 'Vote')]/@href"):
            bill.add_source(url)
            page = self.get(url).text
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            if "/RC/" in url:
                yield from self.parse_chamber_votes(bill, url)
            elif "/RCC/" in url:
                yield from self.parse_committee_votes(bill, url)
            else:
                msg = "Unexpected vote url: %r" % url
                raise Exception(msg)

    def parse_chamber_votes(self, bill, url):
        bill.add_source(url)
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        xpath = "//a[contains(@href, 'rc_view_action2')]"
        chamber = "upper" if "Senate" in page.xpath("string(//h1)") else "lower"
        for link in page.xpath(xpath)[::-1]:
            date_str = link.xpath("string(../preceding-sibling::td)").strip()
            date = datetime.datetime.strptime(date_str, "%m/%d/%Y")
            yield self.parse_roll_call(bill, link, chamber, date)

    def parse_roll_call(self, bill, link, chamber, date):
        url = link.attrib["href"]
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        xpath = 'string(//div[@class="Column-OneFourth"]/div[3])'
        motion = page.xpath(xpath).strip()
        motion = re.sub(r"\s+", " ", motion)

        if motion == "FP":
            motion = "FINAL PASSAGE"

        if motion == "FINAL PASSAGE":
            type = "passage"
        elif re.match(r"CONCUR(RENCE)? IN \w+ AMENDMENTS", motion):
            type = "amendment"
        else:
            type = []
            motion = link.text_content()

        # Looks like for "YEAS" and "NAYS" counts, PA has multiple HTML
        # formats: one where the "YEAS" text node is nested within a span
        # element, and another where the text node is a direct child of the div
        # element
        yeas_elements = page.xpath("//div/span[text() = 'YEAS']/..")
        if len(yeas_elements) == 0:
            yeas_elements = page.xpath("//div[text()[normalize-space() = 'YEAS']]")
        yeas = int(yeas_elements[0].getnext().text)

        nays_elements = page.xpath("//div/span[text() = 'NAYS']/..")
        if len(nays_elements) == 0:
            nays_elements = page.xpath("//div[text()[normalize-space() = 'NAYS']]")
        nays = int(nays_elements[0].getnext().text)

        # "LVE" and "N/V" have been moved up as direct children of the div
        # element
        other = 0
        lve_elements = page.xpath('//div[text()[normalize-space() = "LVE"]]')
        if lve_elements:
            other += int(lve_elements[0].getnext().text)
        nv_elements = page.xpath('//div[text()[normalize-space() = "N/V"]]')
        if nv_elements:
            other += int(nv_elements[0].getnext().text)

        vote = VoteEvent(
            chamber=chamber,
            start_date=tz.localize(date),
            motion_text=motion,
            classification=type,
            result="pass" if yeas > (nays + other) else "fail",
            bill=bill,
        )
        # dedupe_key situation here is a bit weird, same vote can be used for
        # multiple bills see:
        # http://www.legis.state.pa.us/CFDOCS/Legis/RC/Public/rc_view_action2.cfm?sess_yr=2017&sess_ind=0&rc_body=H&rc_nbr=11       # noqa
        # so we toss the bill id onto the end of the URL
        vote.dedupe_key = url + "#" + bill.identifier
        vote.add_source(url)
        vote.set_count("yes", yeas)
        vote.set_count("no", nays)
        vote.set_count("other", other)

        for div in page.xpath('//*[contains(@class, "RollCalls-Vote")]'):
            name = div[0].tail.strip()
            name = re.sub(r"^[\s,]+", "", name)
            name = re.sub(r"[\s,]+$", "", name)
            class_attr = div.attrib["class"].lower()
            if "yea" in class_attr:
                voteval = "yes"
            elif "nay" in class_attr:
                voteval = "no"
            elif "nvote" in class_attr:
                voteval = "other"
            elif "lve" in class_attr:
                voteval = "other"
            else:
                msg = "Unrecognized vote val: %s" % class_attr
                raise Exception(msg)
            vote.vote(voteval, name)

        return vote

    def parse_committee_votes(self, bill, url):
        bill.add_source(url)
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        chamber = "upper" if "Senate" in doc.xpath("string(//h1)") else "lower"
        committee = tuple(doc.xpath("//h2")[0].itertext())[-2].strip()
        for link in doc.xpath("//a[contains(@href, 'listVoteSummary.cfm')]"):

            # Date
            for fmt in ("%m/%d/%Y", "%m-%d-%Y"):
                date = link.xpath("../../td")[0].text_content()
                try:
                    date = datetime.datetime.strptime(date, fmt)
                except ValueError:
                    continue
                break

            # Motion
            motion = link.text_content().split(" - ")[-1].strip()
            motion = "Committee vote (%s): %s" % (committee, motion)

            # Roll call
            vote_url = link.attrib["href"]
            rollcall = self.parse_upper_committee_vote_rollcall(bill, vote_url)

            vote = VoteEvent(
                chamber=chamber,
                start_date=tz.localize(date),
                motion_text=motion,
                classification=[],
                result="pass" if rollcall["passed"] else "fail",
                bill=bill,
            )
            vote.dedupe_key = vote_url
            vote.set_count("yes", rollcall["yes_count"])
            vote.set_count("no", rollcall["no_count"])
            vote.set_count("other", rollcall["other_count"])

            for voteval in ("yes", "no", "other"):
                for name in rollcall.get(voteval + "_votes", []):
                    vote.vote(voteval, name)

            vote.add_source(url)
            vote.add_source(vote_url)

            yield vote

    def parse_upper_committee_vote_rollcall(self, bill, url):
        bill.add_source(url)
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        rollcall = collections.defaultdict(list)
        for div in doc.xpath('//*[contains(@class, "RollCalls-Vote")]'):
            name = div.xpath("../preceding-sibling::td/text()")[0]
            name = re.sub(r"^[\s,]+", "", name)
            name = re.sub(r"[\s,]+$", "", name)
            class_attr = div.attrib["class"].lower()
            if "yea" in class_attr:
                voteval = "yes"
            elif "nay" in class_attr:
                voteval = "no"
            elif "nvote" in class_attr:
                voteval = "other"
            elif "lve" in class_attr:
                voteval = "other"
            else:
                msg = "Unrecognized vote val: %s" % class_attr
                raise Exception(msg)
            rollcall[voteval + "_votes"].append(name)

        for voteval, xpath in (
            ("yes", '//*[contains(@class, "RollCalls-Vote-Yeas")]'),
            ("no", '//*[contains(@class, "RollCalls-Vote-Nays")]'),
            ("other", '//*[contains(@class, "RollCalls-Vote-NV")]'),
        ):

            count = len(doc.xpath(xpath))
            rollcall[voteval + "_count"] = int(count)

        rollcall["passed"] = rollcall["yes_count"] > rollcall["no_count"]

        return dict(rollcall)

    def mimetype_from_class(self, link):
        mimetypes = {
            "icon-IE": "text/html",
            "icon-file-pdf": "application/pdf",
            "icon-file-word": "application/msword",
        }

        try:
            span = link[0]
        except IndexError:
            return
        for cls in span.attrib["class"].split():
            if cls in mimetypes:
                mimetype = mimetypes[cls]
                return mimetype
