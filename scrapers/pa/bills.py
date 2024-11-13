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
        page = self.get_page(url)

        RETRY_TIMES = 5
        for link in page.xpath('//a[@class="bill"]'):
            is_parsed = False
            for retry_time in range(0, RETRY_TIMES):
                try:
                    yield from self.parse_bill(chamber, session, special, link)
                    is_parsed = True
                    break
                except Exception as e:
                    self.logger.warning(
                        "There was an error in scraping {}: Retry {}: Error: {}".format(
                            link.attrib["href"], retry_time + 1, e
                        )
                    )
            if not is_parsed:
                self.logger.error(
                    "Bill {} did not scrape due to the page scraping error. Skip".format(
                        link.text.strip()
                    )
                )

    def parse_bill(self, chamber, session, special, link):
        bill_id = link.text.strip()
        type_abbr = re.search("(b|r)", link.attrib["href"].split("/")[-1]).group(1)

        if type_abbr == "b":
            btype = ["bill"]
        elif type_abbr == "r":
            btype = ["resolution"]

        url = utils.info_url(session, special, bill_id)
        page = self.get_page(url)

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
        page = self.get_page(link)

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
            # Floor RC urls have old domain in the website
            # We need to update the new urls
            if url.startswith(utils.old_base_url):
                url = self.fix_url_domain(url)
            # Skip the duplicated URLs
            if url in vote_urls:
                self.logger.debug("Vote URL is duplicated: {}".format(url))
                continue
            vote_urls.append(url)

            bill.add_source(url)
            if "/roll-calls/" in url:
                yield from self.parse_chamber_votes(bill, url)
            elif "/roll-call-votes/" in url:
                # TODO remove log message and uncomment self.parse_committee_votes()
                # when committee vote URLs work again, for example:
                # https://www.palegis.us/house/committees/roll-call-votes/vote-summary?committeecode=59&rollcallid=1
                self.logger.warning(
                    "Temporarily disabling committee vote ingestion "
                    "due to systemic 500 HTTP errors"
                )
                # yield from self.parse_committee_votes(bill, url)
            else:
                msg = "Unexpected vote url: %r" % url
                raise Exception(msg)

    def get_page(self, url):
        html = self.get(url).text
        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)
        return page

    def parse_chamber_votes(self, bill, url):
        page = self.get_page(url)

        chamber = "upper" if "Senate" in page.xpath("string(//h1)") else "lower"
        date_str = (
            page.xpath(
                'string(//div[contains(@class, "col-main")]//div[./div[contains(text(), "Vote Date")]])'
            )
            .replace("Vote Date", "")
            .strip()
        )
        date_str = re.sub(r"\s+", " ", date_str)
        date = tz.localize(
            datetime.datetime.strptime(date_str, "%A %b %d, %Y %I:%M %p")
        )

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

    def parse_committee_votes(self, bill, url):
        doc = self.get_page(url)

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
            'string(//div[contains(text(), "Type of Motion")]/following-sibling::div[1])'
        ).strip()
        motion = "Committee vote (%s): %s" % (committee, motion)

        # Roll call
        rollcall = self.parse_upper_committee_vote_rollcall(doc)

        vote = VoteEvent(
            chamber=chamber,
            start_date=date,
            motion_text=motion,
            classification=[],
            result="pass" if rollcall["passed"] else "fail",
            bill=bill,
        )
        vote.dedupe_key = url + "#" + bill.identifier
        vote.set_count("yes", rollcall["yes_count"])
        vote.set_count("no", rollcall["no_count"])
        vote.set_count("other", rollcall["other_count"])

        for voteval in ("yes", "no", "other"):
            for name in rollcall.get(voteval + "_votes", []):
                vote.vote(voteval, name)

        vote.add_source(url)

        yield vote

    def parse_upper_committee_vote_rollcall(self, doc):
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
            ("yes", '//ul/li//span[contains(@class, "badge")][@title="Yea"]'),
            ("no", '//ul/li//span[contains(@class, "badge")][@title="Nay"]'),
            (
                "other",
                '//ul/li//span[contains(@class, "badge")][@title="No Vote"]',
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

    def fix_url_domain(self, url):
        # Some vote urls have the old domain in the new website
        # https://www.legis.state.pa.us/cfdocs/legis/RC/Public/rc_view_action2.cfm
        # ?sess_yr=2023&sess_ind=1&rc_body=H&rc_nbr=17
        url_query = url.split("?")[1]
        url_query_obj = urllib.parse.parse_qs(url_query)
        chamber = "house" if url_query_obj["rc_body"][0] == "H" else "senate"
        return utils.vote_url(
            chamber,
            url_query_obj["sess_yr"][0],
            url_query_obj["sess_ind"][0],
            url_query_obj["rc_nbr"][0],
        )
