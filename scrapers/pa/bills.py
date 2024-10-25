import re
import urllib.parse
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

        match = re.search(r"[S#](\d+)", session)
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

        for link in page.xpath('//a[@class="bill"]'):
            yield from self.parse_bill(chamber, session, special, link)

    def parse_bill(self, chamber, session, special, link):
        bill_id = link.text.strip()
        type_abbr = re.search("(b|r)", link.attrib["href"].split("/")[-1]).group(1)

        if type_abbr == "b":
            btype = ["bill"]
        elif type_abbr == "r":
            btype = ["resolution"]

        url = utils.info_url(session, special, bill_id)
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        xpath = (
            '//div[contains(@class, "header ")]/following-sibling::*[1]'
            '/div[@class="col-md-9"]/div[1]'
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
            page,
        )

        # only fetch votes if votes were seen in history
        yield from self.parse_votes(bill, page)

        # Dedupe sources.
        sources = bill.sources
        for source in sources:
            if 1 < sources.count(source):
                sources.remove(source)

        yield bill

    def parse_bill_versions(self, bill, page):
        for row in page.xpath('//div[@id="section-pn"]/div'):
            printers_number = 0
            for a in row.xpath(
                './/div[contains(@class, "btn-group")][@aria-label="Supporting Documents"]/a'
            ):
                mimetype = self.mimetype_from_class(a)

                doc_url = a.attrib["href"]
                params = doc_url.split("/")

                printers_number = params[-1]

                bill.add_version_link(
                    "Printer's No. %s" % printers_number,
                    doc_url,
                    media_type=mimetype,
                    on_duplicate="ignore",
                )

            for a in row.xpath(
                './/div[@class="accordion"]//div[@aria-label="Supporting Documents"]/a'
            ):
                doc_url = a.attrib["href"]
                doc_title = a.text_content()

                if "Amendments" in doc_title:
                    # House and Senate Amendments
                    if "/amendments/amendment-list?searchby=amendment&" not in doc_url:
                        self.logger.error(
                            "Amendments URL is invalid: {} - {}".format(
                                doc_title, doc_url
                            )
                        )
                        continue
                    amend_chamber = doc_title.replace("Amendments", "").strip()
                    self.scrape_amendments(bill, doc_url, amend_chamber)
                elif "Fiscal Note" in doc_title:
                    # Senate & House Fiscal Notes
                    mimetype = self.mimetype_from_class(a)
                    bill.add_document_link(
                        doc_title,
                        doc_url,
                        media_type=mimetype,
                        on_duplicate="ignore",
                    )
                elif "Actuarial Note" in doc_title:
                    # Actuarial Notes
                    mimetype = self.mimetype_from_class(a)
                    bill.add_document_link(
                        "Actuarial Note {}".format(printers_number),
                        doc_url,
                        media_type=mimetype,
                        on_duplicate="ignore",
                    )

    def scrape_amendments(self, bill, link, chamber_pretty):
        html = self.get(link).text
        page = lxml.html.fromstring(html)
        page.make_links_absolute(link)

        for row in page.xpath('//div[contains(@class, "card shadow")]'):
            version_name = "".join(
                row.xpath(
                    './/div[contains(@class, "sponsor-details")]//div[contains(@class, " h5")]//text()'
                )
            ).strip()
            version_name = "{} Amendment {}".format(chamber_pretty, version_name)
            for a in row.xpath('.//div[contains(@class, "position-md-absolute")]//a'):
                mimetype = self.mimetype_from_class(a)
                version_link = a.attrib["href"]
                bill.add_version_link(
                    version_name,
                    version_link,
                    media_type=mimetype,
                    on_duplicate="ignore",
                )

    def parse_history(self, bill, chamber, doc):
        self.parse_sponsors(bill, doc)
        self.parse_actions(bill, chamber, doc)

    def parse_sponsors(self, bill, page):
        # Primary Sponsors
        xpath = (
            '//div[contains(@class, "h3 ")][contains(text(), "Prime Sponsor")]'
            "/following-sibling::div[1]//strong"
        )
        primary_sponsors = page.xpath(xpath)
        for sponsor in primary_sponsors:
            sponsor = sponsor.text_content()
            bill.add_sponsorship(
                utils.clean_sponsor_name(sponsor),
                classification="primary",
                chamber=utils.get_sponsor_chamber(sponsor),
                primary=True,
                entity_type="person",
            )

        # Co-Sponsors
        xpath = (
            '//div[contains(@class, "h3 ")][text()="Co-Sponsors"]'
            "/following-sibling::div[1]//strong"
        )
        co_sponsors = page.xpath(xpath)
        for sponsor in co_sponsors:
            sponsor = sponsor.text_content()
            bill.add_sponsorship(
                utils.clean_sponsor_name(sponsor),
                classification="cosponsor",
                chamber=utils.get_sponsor_chamber(sponsor),
                primary=False,
                entity_type="person",
            )
        # Collapsed Co-Sponsors
        xpath = '//div[@id="coSponsAdd"]//strong'
        co_sponsors = page.xpath(xpath)
        for sponsor in co_sponsors:
            sponsor = sponsor.text_content()
            bill.add_sponsorship(
                utils.clean_sponsor_name(sponsor),
                classification="cosponsor",
                chamber=utils.get_sponsor_chamber(sponsor),
                primary=False,
                entity_type="person",
            )

    def parse_actions(self, bill, chamber, page):
        for tr in page.xpath(
            '//div[@id="billActions"]//div[@id="collapseActions"]//table//tr'
        ):
            action = tr[1].xpath("string()").replace("\xa0", " ").strip()

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

    def parse_votes(self, bill, page):
        vote_urls = []

        for url in page.xpath(
            '//div[contains(text(), "Votes")]/following-sibling::div[1]//a/@href'
        ):
            # the floor rc urls are old now. we need to update the new urls
            url = url.strip()
            if url.startswith(utils.old_base_url):
                url = self.update_new_url(url)

            # remove duplicates of urls
            if "roll-calls" not in url and "roll-call-votes" not in url:
                if "?committeecode=" in url:
                    # this is the bug for a committe URL in this website scraping
                    # like /house/senate/senate/senate?committeecode=64&rollcallid=259
                    self.logger.warning("Invalid committe vote url: {}".format(url))
                    rc_chamber = url.replace("https://www.palegis.us/", "").split("/")[
                        0
                    ]
                    url = "https://www.palegis.us/{}/committees/roll-call-votes/vote-summary?{}".format(
                        rc_chamber, url.split("?")[1]
                    )
                    self.logger.warning("is updated to {}".format(url))
                elif "rcNum" in url:
                    # like /house/senate/senate/senate?sessYr=2023&sessInd=0&rcNum=1321
                    self.logger.warning("Invalid floor vote url: {}".format(url))
                    rc_chamber = url.replace("https://www.palegis.us/", "").split("/")[
                        0
                    ]
                    url = "https://www.palegis.us/{}/roll-calls/summary?{}".format(
                        rc_chamber, url.split("?")[1]
                    )
                    self.logger.warning("is updated to {}".format(url))
                else:
                    self.logger.warning("Vote URL is invalid: {}".format(url))
                    continue
            if url in vote_urls:
                self.logger.debug("Vote URL is duplicated: {}".format(url))
                continue
            vote_urls.append(url)

            bill.add_source(url)
            html = self.get(url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            if "/roll-calls/" in url:
                yield from self.parse_chamber_votes(bill, doc, url)
            elif "/roll-call-votes/" in url:
                yield from self.parse_committee_votes(bill, doc, url)
            else:
                msg = "Unexpected vote url: %r" % url
                self.logger.warning(msg)
                continue

    def parse_chamber_votes(self, bill, page, url):
        chamber = "upper" if "Senate" in page.xpath("string(//h1)") else "lower"
        date_str = (
            page.xpath(
                'string(//div[contains(@class, "col-main")]//div[./div[contains(text(), "Vote Date")]])'
            )
            .replace("Vote Date", "")
            .strip()
        )
        date_str = re.sub(r"\s+", " ", date_str)
        if date_str:
            self.logger.info("URL: {}, Date: {}".format(url, date_str))
            date = tz.localize(
                datetime.datetime.strptime(date_str, "%A %b %d, %Y %I:%M %p")
            )
        else:
            date_href = page.xpath(
                '//div[contains(@class, "col-main")]//div[./div[contains(text(), "Vote Date")]]//a/@href'
            )
            if not date_href:
                self.logger.warning("Vote date format is invalid: {}".format(url))
                return
            date_href = date_href[0]
            date_str = date_href.split("=")[-1].strip()
            self.logger.info("URL: {}, Date: {}".format(url, date_str))
            date = tz.localize(datetime.datetime.strptime(date_str, "%Y-%m-d"))

        xpath = 'string(//div[contains(@class,h6)][contains(text(), "Action")]/..)'
        motion = page.xpath(xpath).replace("Action", "").strip()
        motion = re.sub(r"\s+", " ", motion).upper()
        if motion == "FP":
            motion = "FINAL PASSAGE"

        if motion == "FINAL PASSAGE":
            type = "passage"
        elif re.match(r"CONCUR(RENCE)? IN \w+ AMENDMENTS", motion):
            type = "amendment"
        else:
            type = []
            if not motion:
                xpath = '//div[contains(@class,h6)][contains(text(), "Bill")]/../a'
                motion = page.xpath(xpath)[1].text_content().strip()
                motion = re.sub(r"\s+", " ", motion)

        yeas_elements = page.xpath(
            '//div[@id="voteSummary"]//div[contains(., "Yea")]/div[2]'
        )[0]
        yeas = int(yeas_elements.text_content())

        nays_elements = page.xpath(
            '//div[@id="voteSummary"]//div[contains(., "Nay")]/div[2]'
        )[0]
        nays = int(nays_elements.text_content())
        # element
        other = 0
        lve_elements = page.xpath(
            '//div[@id="voteSummary"]//div[contains(., "Leave")]/div[2]'
        )
        if lve_elements:
            other += int(lve_elements[0].text_content())
        nv_elements = page.xpath(
            '//div[@id="voteSummary"]//div[contains(., " No Vote")]/div[2]'
        )
        if nv_elements:
            other += int(nv_elements[0].text_content())

        vote = VoteEvent(
            chamber=chamber,
            start_date=date,
            motion_text=motion,
            classification=type,
            result="pass" if yeas > (nays + other) else "fail",
            bill=bill,
        )
        # dedupe_key situation here is a bit weird, same vote can be used for
        # multiple bills see:
        # so we toss the bill id onto the end of the URL
        vote.dedupe_key = url + "#" + bill.identifier
        vote.add_source(url)
        vote.set_count("yes", yeas)
        vote.set_count("no", nays)
        vote.set_count("other", other)

        for div in page.xpath(
            '//div[contains(@class, "rc-member ")][./div[contains(@class, "rc-member-display ")]]'
        ):
            name = div.xpath("string(.//strong)") or div.xpath(
                'string(.//div[contains(@class, "rc-member-print")])'
            )
            name = utils.clean_sponsor_name(name)
            if not name:
                msg = "voter name is none. Referrer url: %s" % url
                raise Exception(msg)
            badge = (
                "".join(div.xpath('.//span[contains(@class, "badge")][@title]/@title'))
                .replace(" ", "")
                .lower()
            )
            if "yea" in badge:
                voteval = "yes"
            elif "nay" in badge:
                voteval = "no"
            elif "novote" in badge:
                voteval = "other"
            elif "leave" in badge:
                voteval = "other"
            else:
                msg = "Unrecognized vote val: %s" % badge
                raise Exception(msg)
            vote.vote(voteval, name)

        yield vote

    def parse_committee_votes(self, bill, doc, url):
        chamber = "upper" if "Senate" in doc.xpath("string(//h1)") else "lower"
        committee = doc.xpath(
            'string(//div[contains(@class, "detailsLabel")][contains(., "Committe")]/following-sibling::div/a)'
        ).strip()

        date = doc.xpath(
            'string(//div[contains(@class, "detailsLabel")][contains(., "Date")]/following-sibling::div/a)'
        ).strip()
        date = tz.localize(datetime.datetime.strptime(date, "%B %d, %Y"))
        self.logger.info("Committe Vote Date: {}, URL: {}".format(date, url))
        # Motion
        motion = doc.xpath(
            'string(//div[contains(@class, "portlet ")]//div[contains(@class, "h5 ")][contains(., "Motion:")]/span[2])'
        ).strip()
        motion = "Committee vote (%s): %s" % (committee, motion)

        # Roll call
        rollcall = self.parse_upper_committee_vote_rollcall(bill, doc)

        vote = VoteEvent(
            chamber=chamber,
            start_date=date,
            motion_text=motion,
            classification=[],
            result="pass" if rollcall["passed"] else "fail",
            bill=bill,
        )
        vote.dedupe_key = url
        vote.set_count("yes", rollcall["yes_count"])
        vote.set_count("no", rollcall["no_count"])
        vote.set_count("other", rollcall["other_count"])

        for voteval in ("yes", "no", "other"):
            for name in rollcall.get(voteval + "_votes", []):
                vote.vote(voteval, name)

        vote.add_source(url)
        yield vote

    def parse_upper_committee_vote_rollcall(self, bill, doc):
        rollcall = collections.defaultdict(list)

        for div in doc.xpath(
            '//div[contains(., "Member Votes")][contains(@class, "card-header")]/following-sibling::div[1]//ul/li'
        ):
            name = utils.clean_sponsor_name(div.xpath(".//a/text()")[0])
            badge = (
                "".join(div.xpath('.//span[contains(@class, "badge")][@title]/@title'))
                .replace(" ", "")
                .lower()
            )
            if "yea" in badge:
                voteval = "yes"
            elif "nay" in badge:
                voteval = "no"
            elif "novote" in badge:
                voteval = "other"
            elif "leave" in badge:
                voteval = "other"
            else:
                msg = "Unrecognized vote val: %s" % badge
                raise Exception(msg)
            rollcall[voteval + "_votes"].append(name)

        for voteval, xpath in (
            ("yes", '//ul/li//span[contains(@class, "badge ")][@aria-label="Yea"]'),
            ("no", '//ul/li//span[contains(@class, "badge ")][@aria-label="Nay"]'),
            (
                "other",
                '//ul/li//span[contains(@class, "badge ")][@aria-label="No Vote"]',
            ),
        ):
            count = len(doc.xpath(xpath))
            rollcall[voteval + "_count"] = int(count)

        rollcall["passed"] = rollcall["yes_count"] > rollcall["no_count"]

        return dict(rollcall)

    def mimetype_from_class(self, link):
        mimetypes = {
            "fa-edge": "text/html",
            "fa-file-pdf": "application/pdf",
            "fa-file-word": "application/msword",
        }

        try:
            span = link[0]
        except IndexError:
            return
        for cls in span.attrib["class"].split():
            if cls in mimetypes:
                mimetype = mimetypes[cls]
                return mimetype

    def update_new_url(self, url):
        url_query = url.split("?")[1]
        url_query_obj = urllib.parse.parse_qs(url_query)
        chamber = "house" if url_query_obj["rc_body"][0] == "H" else "senate"
        return utils.vote_url(
            chamber,
            url_query_obj["sess_yr"][0],
            url_query_obj["sess_ind"][0],
            url_query_obj["rc_nbr"][0],
        )
