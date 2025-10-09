import re
import requests

import os
import json
from datetime import datetime
import lxml.html
from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.utils import convert_pdf

from .actions import Categorizer


requests.packages.urllib3.disable_warnings()


class MABillScraper(Scraper):
    verify = False

    categorizer = Categorizer()
    session_filters = {}
    chamber_filters = {}
    house_pdf_cache = {}

    bill_list = []

    chamber_map = {"lower": "House", "upper": "Senate"}
    chamber_map_reverse = {
        "House": "lower",
        "Senate": "upper",
        "Executive": "executive",
        "Joint": "legislature",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # forcing these values so that 500s come back as skipped bills
        self.raise_errors = False
        self.verify = False
        self.retry_attempts = 0

    def format_bill_number(self, raw):
        return raw.replace("Bill ", "").replace(".", " ").strip()

    def get_refiners(self, page, refinerName):
        # Get the possible values for each category of refiners,
        # e.g. House, Senate for lawsbranchname (Branch)
        filters = page.xpath(
            "//div[@data-refinername='{}']/div/label".format(refinerName)
        )

        refiner_list = {}
        for refiner_filter in filters:
            label = re.sub(r"\([^)]*\)", "", refiner_filter.xpath("text()")[1]).strip()
            refiner = refiner_filter.xpath("input/@data-refinertoken")[0].replace(
                '"', ""
            )
            refiner_list[label] = refiner
        return refiner_list

    # bill_no can be set to a specific bill (no spaces) to scrape only one
    # os-update ma bills --scrape bill_no=H2
    # we can also scrape a "chunk" of all available bills by specifying an integer 1-12 (inclusive)
    # chunks are available to split up this long, slow scrape into 12 smaller scrapes
    # os-update ma bills --scrape scrape_chunk_number=1
    # this trades off comprehensivity for limited scope of failure/faster time to recovery
    def scrape(
        self, chamber=None, session=None, bill_no=None, scrape_chunk_number=None
    ):
        self.scrape_bill_list(session)

        # optionally scrape a single bill then exit
        if bill_no:
            single_bill_chamber = "lower" if "H" in bill_no else "upper"
            for bill_meta in self.bill_list:
                if bill_no in [bill_meta["DocketNumber"], bill_meta["BillNumber"]]:
                    yield from self.scrape_bill(session, bill_meta, single_bill_chamber)
                    self.info("Finished individual bill scrape, exiting.")
                    return

        if not chamber:
            yield from self.scrape_chamber("lower", session, scrape_chunk_number)
            yield from self.scrape_chamber("upper", session, scrape_chunk_number)
        else:
            yield from self.scrape_chamber(chamber, session, scrape_chunk_number)

    def scrape_bill_list(self, session):
        session_numeric = re.sub(r"[^0-9]", "", session)
        # note -- this returns XML to a browser, but json to curl/python
        api_url = (
            f"https://malegislature.gov/api/GeneralCourts/{session_numeric}/Documents"
        )

        list_data = self.get(api_url, verify=False).content
        for row in json.loads(list_data):
            chambers = ["H", "S"]

            # bill never flips from house to senate from docket -> intro so we're safe here
            # BillNumber can be set, but mapped to None, so use or here
            bill_id = row["BillNumber"] or row["DocketNumber"]
            # make sure the bill has an H or an S in the code
            if not any([chamber in bill_id for chamber in chambers]):
                self.error(
                    f"Unknown bill type - bill {row['BillNumber']} - docket {row['DocketNumber']}"
                )

            self.bill_list.append(
                {"BillNumber": row["BillNumber"], "DocketNumber": row["DocketNumber"]}
            )

    def scrape_chamber(self, chamber, session, scrape_chunk_number):
        chamber_code = "H" if chamber == "lower" else "S"
        chamber_bill_list = []
        for bill_meta in self.bill_list:
            bill_id = bill_meta["BillNumber"] or bill_meta["DocketNumber"]
            if chamber_code in bill_id:
                chamber_bill_list.append(bill_meta)

        # if scrape_chunk_number is specified, we are being asked to scrape
        # only a specific chunk of the total bills in this chamber
        # let's use 1-based counting so we're not doing scrape_chunk_number=0
        if scrape_chunk_number:
            # divide up the chamber_bill_list into 12 equal-sized lists
            chunk_size = (
                len(chamber_bill_list) // 12 if len(chamber_bill_list) >= 12 else 1
            )
            if len(chamber_bill_list) % 12 > 0:
                chunk_size += 1
            bill_chunks = [
                chamber_bill_list[i : i + chunk_size]
                for i in range(0, len(chamber_bill_list), chunk_size)
            ]
            chunk_number = int(scrape_chunk_number)

            chamber_bill_list = bill_chunks[chunk_number - 1]

        for chamber_bill_meta in chamber_bill_list:
            yield from self.scrape_bill(session, chamber_bill_meta, chamber)

    def scrape_bill(self, session, bill_meta, chamber):
        # https://malegislature.gov/Bills/189/SD2739
        bill_id = bill_meta["BillNumber"] or bill_meta["DocketNumber"]

        session_for_url = self.replace_non_digits(session)
        bill_url = "https://malegislature.gov/Bills/{}/{}".format(
            session_for_url, bill_id
        )

        try:
            response = self.get(bill_url, verify=False)
            self.info("GET (with `requests`) - {}".format(bill_url))
        except requests.exceptions.RequestException:
            self.warning("Server Error on {}".format(bill_url))
            return False

        html = response.text

        page = lxml.html.fromstring(html)

        if not page.xpath('//div[contains(@class, "followable")]/h1/text()'):
            self.warning("Server Error on {}".format(bill_url))
            return False

        # The state website will periodically miss a few bills' titles for a few days
        # These titles will be extant on the bill list page, but missing on the bill detail page
        # The titles are eventually populated under one of two markups
        try:
            bill_title = page.xpath('//div[@id="contentContainer"]/div/div/h2/text()')[
                0
            ]
        except IndexError:
            bill_title = None
            pass

        if bill_title is None:
            try:
                bill_title = page.xpath(
                    '//div[contains(@class,"followable")]/h1/text()'
                )[0]
                bill_title = bill_title.replace("Bill", "").strip()
            except IndexError:
                self.warning("Couldn't find title for {}; skipping".format(bill_id))
                return False

        bill_types = ["H", "HD", "S", "SD", "SRes"]
        if re.sub("[0-9]", "", bill_id) not in bill_types:
            self.warning("Unsupported bill type for {}; skipping".format(bill_id))
            return False
        classification = "proposed bill" if "D" in bill_id else "bill"

        if "SRes" in bill_id:
            bill_id = bill_id.replace("SRes", "SR")

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=bill_title,
            classification=classification,
        )

        bill_summary = None
        if page.xpath('//p[@id="pinslip"]/text()'):
            bill_summary = page.xpath('//p[@id="pinslip"]/text()')[0].strip()
        if bill_summary and bill_summary != "":
            bill.add_abstract(bill_summary, "summary")

        if bill_meta["BillNumber"] and bill_meta["DocketNumber"]:
            bill.add_related_bill(
                bill_meta["DocketNumber"],
                legislative_session=session,
                relation_type="replaces",
            )

        bill.add_source(bill_url)

        # https://malegislature.gov/Bills/189/SD2739 has a presenter
        # https://malegislature.gov/Bills/189/S2168 no sponsor
        # Find the non-blank text of the dt following Sponsor or Presenter,
        # including any child link text.
        sponsor = page.xpath(
            '//dt[text()="Sponsor:" or text()="Presenter:"]/'
            "following-sibling::dd/descendant-or-self::*/text()[normalize-space()]"
        )
        # Sponsors always have link that follows pattern <a href="/Legislators/Profile/JNR1/193">Jeffrey N. Roy</a>
        # If this is a person i.e. "legislators" it will show in sponsor_href.
        sponsor_href = page.xpath(
            '//dt[text()="Sponsor:" or text()="Presenter:"]/following-sibling::dd//a/@href'
        )
        sponsor_href = sponsor_href[0] if sponsor_href else ""
        entity_type = (
            "person" if "legislators/" in sponsor_href.lower() else "organization"
        )

        if sponsor:
            sponsor = (
                sponsor[0]
                .replace("*", "")
                .replace("%", "")
                .replace("This sponsor is an original petitioner.", "")
                .strip()
            )
            bill.add_sponsorship(
                sponsor, classification="primary", primary=True, entity_type=entity_type
            )

        self.scrape_cosponsors(bill, bill_url)

        version = page.xpath(
            "//div[contains(@class, 'modalBtnGroup')]/"
            "a[contains(text(), 'Download PDF') and not(@disabled)]/@href"
        )
        if version:
            version_url = "https://malegislature.gov{}".format(version[0])
            bill.add_version_link(
                "Bill Text", version_url, media_type="application/pdf"
            )

        self.scrape_actions(bill, bill_url, session)
        yield bill

    def scrape_cosponsors(self, bill, bill_url):
        # https://malegislature.gov/Bills/189/S1194/CoSponsor
        cosponsor_url = "{}/CoSponsor".format(bill_url)
        html = self.get_as_ajax(cosponsor_url).text
        page = lxml.html.fromstring(html)
        cosponsor_rows = page.xpath("//tbody/tr")
        for row in cosponsor_rows:
            # careful, not everyone is a linked representative
            # https://malegislature.gov/Bills/189/S740/CoSponsor
            cosponsor_name = row.xpath("string(td[1])").strip()
            # cosponsor_district = ''
            # # if row.xpath('td[2]/text()'):
            #     cosponsor_district = row.xpath('td[2]/text()')[0]

            # Filter the sponsor out of the petitioners list
            if not any(
                sponsor["name"] == cosponsor_name for sponsor in bill.sponsorships
            ):
                cosponsor_name = (
                    cosponsor_name.replace("*", "")
                    .replace("%", "")
                    .replace("This sponsor is an original petitioner.", "")
                    .strip()
                )
                bill.add_sponsorship(
                    cosponsor_name,
                    classification="cosponsor",
                    primary=False,
                    entity_type="person",
                    # district=cosponsor_district
                )

    def scrape_actions(self, bill, bill_url, session):
        # scrape_action_page adds the actions, and also returns the Page xpath object
        # so that we can check for a paginator
        page = self.get_action_page(bill_url, 1)
        # XXX: yield from
        self.scrape_action_page(bill, page)

        max_page = page.xpath(
            '//ul[contains(@class,"pagination-sm")]/li[last()]/a/@onclick'
        )
        if max_page:
            max_page = re.sub(r"[^\d]", "", max_page[0]).strip()
            for counter in range(2, int(max_page) + 1):
                page = self.get_action_page(bill_url, counter)
                # XXX: yield from
                self.scrape_action_page(bill, page)
                # https://malegislature.gov/Bills/189/S3/BillHistory?pageNumber=2

    def get_action_page(self, bill_url, page_number):
        actions_url = "{}/BillHistory?pageNumber={}".format(bill_url, page_number)
        return lxml.html.fromstring(self.get_as_ajax(actions_url).text)

    def scrape_action_page(self, bill, page):
        action_rows = page.xpath("//tbody/tr")
        for row in action_rows:
            action_date = row.xpath("td[1]/text()")[0]
            action_date = datetime.strptime(action_date, "%m/%d/%Y")
            action_year = action_date.year
            action_date = action_date.strftime("%Y-%m-%d")

            if row.xpath("td[2]/text()"):
                action_actor = row.xpath("td[2]/text()")[0]
                action_actor = self.chamber_map_reverse[action_actor.strip()]

            action_name = row.xpath("string(td[3])")

            # House votes
            if "Supplement" in action_name:
                actor = "lower"

                if not re.findall(r"(.+)-\s*\d+\s*YEAS", action_name):
                    self.warning(
                        "vote {} did not match regex, skipping".format(action_name)
                    )
                    continue

                vote_action = re.findall(r"(.+)-\s*\d+\s*YEAS", action_name)[0].strip()

                y = int(re.findall(r"(\d+)\s*YEAS", action_name)[0])
                n = int(re.findall(r"(\d+)\s*NAYS", action_name)[0])

                # get supplement number
                n_supplement = int(
                    re.findall(r"No\.\s*(\d+)", action_name, re.IGNORECASE)[0]
                )
                cached_vote = VoteEvent(
                    chamber=actor,
                    start_date=action_date,
                    motion_text=vote_action,
                    result="pass" if y > n else "fail",
                    classification="passage",
                    bill=bill,
                )
                cached_vote.set_count("yes", y)
                cached_vote.set_count("no", n)

                housevote_pdf = (
                    "https://malegislature.gov/Journal/House/{}/{}/RollCalls".format(
                        bill.legislative_session, action_year
                    )
                )
                self.scrape_house_vote(cached_vote, housevote_pdf, n_supplement)
                cached_vote.add_source(housevote_pdf)

                cached_vote.dedupe_key = "{}#{}".format(housevote_pdf, n_supplement)

                # XXX: disabled house votes on 8/1 to try to get MA importing again
                # will leaving this in and commented out once we resolve the ID issue
                # yield cached_vote

            # Senate votes
            if "Roll Call" in action_name:
                actor = "upper"
                # placeholder
                vote_action = action_name.split(" -")[0]
                # 2019 H86 Breaks our regex,
                # Ordered to a third reading --
                # see Senate   Roll Call #25 and House Roll Call 56
                if "yeas" in action_name and "nays" in action_name:
                    try:
                        y, n = re.search(
                            r"(\d+) yeas .*? (\d+) nays", action_name.lower()
                        ).groups()
                        y = int(y)
                        n = int(n)
                    except AttributeError:
                        y = int(
                            re.search(r"yeas\s+(\d+)", action_name.lower()).group(1)
                        )
                        n = int(
                            re.search(r"nays\s+(\d+)", action_name.lower()).group(1)
                        )

                    # TODO: other count isn't included, set later
                    cached_vote = VoteEvent(
                        chamber=actor,
                        start_date=action_date,
                        motion_text=vote_action,
                        result="pass" if y > n else "fail",
                        classification="passage",
                        bill=bill,
                    )
                    cached_vote.set_count("yes", y)
                    cached_vote.set_count("no", n)

                    rollcall_pdf = "http://malegislature.gov" + row.xpath(
                        "string(td[3]/a/@href)"
                    )
                    self.scrape_senate_vote(cached_vote, rollcall_pdf)
                    cached_vote.add_source(rollcall_pdf)
                    cached_vote.dedupe_key = rollcall_pdf
                    # XXX: also disabled, see above note
                    # yield cached_vote

            attrs = self.categorizer.categorize(action_name)
            action = bill.add_action(
                action_name.strip(),
                action_date,
                chamber=action_actor,
                classification=attrs["classification"],
            )
            for com in attrs.get("committees", []):
                com = com.strip()
                action.add_related_entity(com, entity_type="organization")

    def get_house_pdf(self, vurl):
        """cache house PDFs since they are done by year"""
        if vurl not in self.house_pdf_cache:
            (path, resp) = self.urlretrieve(vurl)
            pdflines = convert_pdf(path, "text")
            os.remove(path)
            self.house_pdf_cache[vurl] = pdflines.decode("utf-8").replace("\u2019", "'")
        return self.house_pdf_cache[vurl]

    def scrape_house_vote(self, vote, vurl, supplement):
        pdflines = self.get_house_pdf(vurl)
        # get pdf data from supplement number
        try:
            vote_text = pdflines.split("No. " + str(supplement))[1].split(
                "MASSACHUSETTS"
            )[0]
        except IndexError:
            self.info("No vote found in supplement for vote #%s" % supplement)
            return

        # create list of independent items in vote_text
        rows = vote_text.splitlines()
        lines = []
        for row in rows:
            lines.extend(row.split("   "))

        # retrieving votes in columns
        vote_tally = []
        voters = []
        for line in lines:
            # removes whitespace and after-vote '*' tag
            line = line.strip().strip("*").strip()

            if "NAYS" in line or "YEAS" in line or "=" in line or "/" in line:
                continue
            elif line == "":
                continue
            elif line == "N":
                vote_tally.append("n")
            elif line == "Y":
                vote_tally.append("y")
            # Not Voting
            elif line == "X":
                vote_tally.append("x")
            # Present
            elif line == "P":
                vote_tally.append("p")
            else:
                voters.append(line)

        house_votes = list(zip(voters, vote_tally))
        # iterate list and add individual names to vote.yes, vote.no
        for tup1 in house_votes:
            if tup1[1] == "y":
                vote.yes(tup1[0])
            elif tup1[1] == "n":
                vote.no(tup1[0])
            else:
                vote.vote("other", tup1[0])

    def scrape_senate_vote(self, vote, vurl):
        # download file to server
        (path, resp) = self.urlretrieve(vurl)
        pdflines = convert_pdf(path, "text")
        os.remove(path)

        # for y, n
        mode = None

        lines = pdflines.splitlines()

        # handle individual lines in pdf to id legislator votes
        for line in lines:
            line = line.strip()
            line = line.decode("utf-8").replace("\u2212", "-")
            if line == "":
                continue
            # change mode accordingly
            elif line.startswith("YEAS"):
                mode = "y"
            elif line.startswith("NAYS"):
                mode = "n"
            elif line.startswith("ABSENT OR"):
                mode = "o"
            # else parse line with names
            else:
                nameline = line.split("   ")

                for raw_name in nameline:
                    raw_name = raw_name.strip()
                    if raw_name == "":
                        continue

                    # handles vote count lines
                    cut_name = raw_name.split("-")
                    clean_name = ""
                    if cut_name[-1].strip(" .").isdigit():
                        del cut_name[-1]
                        clean_name = "".join(cut_name)
                    else:
                        clean_name = raw_name.strip()
                    # update vote object with names
                    if mode == "y":
                        vote.yes(clean_name)
                    elif mode == "n":
                        vote.no(clean_name)
                    elif mode == "o":
                        vote.vote("other", clean_name)

    def get_as_ajax(self, url):
        # set the X-Requested-With:XMLHttpRequest so the server only sends along the bits we want
        s = requests.Session()
        s.verify = False
        s.headers.update({"X-Requested-With": "XMLHttpRequest"})
        return s.get(url)

    def replace_non_digits(self, str):
        return re.sub(r"[^\d]", "", str).strip()
