import datetime
import lxml.html
import pytz
import re

from openstates.scrape import VoteEvent, Scraper


class USVoteScraper(Scraper):
    _TZ = pytz.timezone("US/Eastern")

    chamber_code = {"S": "upper", "H": "lower", "J": "legislature"}
    vote_codes = {
        "Yea": "yes",
        "Nay": "no",
        "Not Voting": "not voting",
        "Present": "other",
        "Present, Giving Live Pair": "other",
    }

    senate_statuses = {
        "Agreed to": "pass",
        "Bill Passed": "pass",
        "Confirmed": "pass",
        "Rejected": "fail",
        "Passed": "pass",
        "Nomination Confirmed": "pass",
        "Cloture Motion Agreed to": "pass",
        "Cloture Motion Rejected": "fail",
        "Cloture on the Motion to Proceed Rejected": "fail",
        "Cloture on the Motion to Proceed Agreed to": "pass",
        "Amendment Rejected": "fail",
        "Decision of Chair Sustained": "pass",
        "Motion Agreed to": "pass",
        "Motion to Discharge Agreed to": "pass",
        "Motion to Table Failed": "fail",
        "Motion to Table Agreed to": "pass",
        "Motion to Table Motion to Recommit Agreed to": "pass",
        "Motion to Proceed Agreed to": "pass",
        "Motion to Proceed Rejected": "fail",
        "Bill Defeated": "fail",
        "Joint Resolution Passed": "pass",
    }

    vote_classifiers = (
        (".*Introduction and first reading.*", ["introduction", "reading-1"]),
        (".*First reading.*", ["introduction", "reading-1"]),
        (".*Second reading.*", ["reading-2"]),
        (".*Referred to .*", ["referral-committee"]),
        (".*Assigned to Subcommittee.*", ["referral-committee"]),
        (".*Recommendation: Do pass.*", ["committee-passage-favorable"]),
        (".*Governor signed.*", ["executive-signature"]),
        (".*Third reading.* Passed", ["passage", "reading-3"]),
        (".*Third reading.* Failed", ["failure", "reading-3"]),
        (".*President signed.*", ["passage"]),
        (".*Speaker signed.*", ["passage"]),
        (".*Final reading.* Adopted", ["passage"]),
        (".*Read third time .* Passed", ["passage", "reading-3"]),
        (r".*Read\. .* Adopted.*", ["passage"]),
    )

    def scrape(self, session=None, chamber=None, year=None, start=None):
        if start:
            start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%I:%S")
        else:
            start = datetime.datetime(1980, 1, 1, 0, 0, 1)

        if chamber is None:
            yield from self.scrape_votes(session, "lower", start, year)
            yield from self.scrape_votes(session, "upper", start, year)
        else:
            yield from self.scrape_votes(session, chamber, start, year)

    def scrape_votes(self, session, chamber, start, year):
        if chamber == "upper":
            yield from self.scrape_senate_votes(session, start, year)
        elif chamber == "lower":
            yield from self.scrape_house_votes(session, start, year)

    def scrape_house_votes(self, session, start, year):
        if not year:
            self.error("year is a required argument for house votes. eg: year=2020")

        index_url = "https://clerk.house.gov/evs/{}/index.asp".format(year)
        page = lxml.html.fromstring(self.get(index_url).content)
        page.make_links_absolute(index_url)

        for row in page.xpath('//a[contains(@href, "ROLL_")]/@href'):
            yield from self.scrape_house_rolls_page(session, start, year, row)

    def scrape_house_rolls_page(self, session, start, year, url):
        # url eg: https://clerk.house.gov/evs/2020/ROLL_200.asp
        page = lxml.html.fromstring(self.get(url).content)
        page.make_links_absolute(url)

        for row in page.xpath("//table/tr"):
            # header or special message
            if not row.xpath("td[1]/a"):
                continue

            vote_url = row.xpath("td[1]/a/@href")[0]

            # Dates are in the format of 20-Nov, so add the year
            vote_date = row.xpath("td[2]/font/text()")[0]
            vote_date = "{}-{}".format(vote_date, year)
            vote_date = datetime.datetime.strptime(vote_date, "%d-%b-%Y")

            if vote_date < start:
                self.info("No more votes found before start date.")
                return

            vote = self.scrape_house_vote(vote_url)
            yield vote

    def scrape_house_vote(self, url):
        page = lxml.html.fromstring(self.get(url).content)
        page.make_links_absolute(url)

        vote_date = page.xpath("//rollcall-vote/vote-metadata/action-date/text()")[0]
        vote_time = page.xpath("//rollcall-vote/vote-metadata/action-time/@time-etz")[0]

        when = self._TZ.localize(
            datetime.datetime.strptime(
                "{} {}".format(vote_date, vote_time), "%d-%b-%Y %H:%M"
            )
        )

        motion = page.xpath("//rollcall-vote/vote-metadata/vote-question/text()")[0]
        result = page.xpath("//rollcall-vote/vote-metadata/vote-result/text()")[0]
        if result == "Passed":
            result = "pass"
        else:
            result = "fail"

        session = page.xpath("//rollcall-vote/vote-metadata/congress/text()")[0]

        bill_id = page.xpath("//rollcall-vote/vote-metadata/legis-num/text()")[0]

        # for some reason these are "H R 123" which nobody uses, so fix to "HR 123"
        bill_id = re.sub(r"([A-Z])\s([A-Z])", r"\1\2", bill_id)

        roll_call = page.xpath("//rollcall-vote/vote-metadata/rollcall-num/text()")[0]

        vote_id = "us-{}-lower-{}".format(when.year, roll_call)

        vote = VoteEvent(
            start_date=when,
            bill_chamber="lower" if bill_id[0] == "H" else "upper",
            motion_text=motion,
            classification="passage",  # TODO
            result=result,
            legislative_session=session,
            identifier=vote_id,
            bill=bill_id,
            chamber="lower",
        )
        vote.add_source(url)

        vote.extras["house-rollcall-num"] = roll_call

        yeas = page.xpath(
            "//rollcall-vote/vote-metadata/vote-totals/totals-by-vote/yea-total/text()"
        )[0]
        nays = page.xpath(
            "//rollcall-vote/vote-metadata/vote-totals/totals-by-vote/nay-total/text()"
        )[0]
        nvs = page.xpath(
            "//rollcall-vote/vote-metadata/vote-totals/totals-by-vote/not-voting-total/text()"
        )[0]
        presents = page.xpath(
            "//rollcall-vote/vote-metadata/vote-totals/totals-by-vote/present-total/text()"
        )[0]

        vote.set_count("yes", int(yeas))
        vote.set_count("no", int(nays))
        vote.set_count("not voting", int(nvs))
        vote.set_count("abstain", int(presents))

        # vote.yes vote.no vote.vote
        for row in page.xpath("//rollcall-vote/vote-data/recorded-vote"):
            bioguide = row.xpath("legislator/@name-id")[0]
            name = row.xpath("legislator/@sort-field")[0]
            choice = row.xpath("vote/text()")[0]

            vote.vote(self.vote_codes[choice], name, note=bioguide)
        return vote

    def scrape_senate_votes(self, session, start, year):
        # odd years are first period of a 2-year congress, even are second
        period = 1 if int(year) % 2 == 1 else 2
        # ex: https://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_116_2.xml
        index_url = (
            "https://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_{}_{}.xml"
        )
        index_url = index_url.format(session, period)
        page = lxml.html.fromstring(self.get(index_url).content)

        for row in page.xpath("//vote_summary/votes/vote"):
            # Dates are in the format of 20-Nov, so add the year
            vote_date = row.xpath("vote_date/text()")[0]
            vote_date = "{}-{}".format(vote_date, year)
            vote_date = datetime.datetime.strptime(vote_date, "%d-%b-%Y")

            if vote_date < start:
                self.info("No more votes found before start date.")
                return

            roll_call = row.xpath("vote_number/text()")[0]
            yield from self.scrape_senate_vote(session, period, roll_call)

    def scrape_senate_vote(self, session, period, roll_call):
        url = (
            "https://www.senate.gov/legislative/LIS/roll_call_votes/vote{session}{period}/"
            "vote_{session}_{period}_{vote_id}.xml"
        )
        url = url.format(session=session, period=period, vote_id=roll_call)
        page = lxml.html.fromstring(self.get(url).content)

        vote_date = page.xpath("//roll_call_vote/vote_date/text()")[0].strip()
        when = self._TZ.localize(
            datetime.datetime.strptime(vote_date, "%B %d, %Y, %H:%M %p")
        )

        roll_call = page.xpath("//roll_call_vote/vote_number/text()")[0]
        vote_id = "us-{}-upper-{}".format(when.year, roll_call)

        # note: not everthing the senate votes on is a bill, this is OK
        # non bills include nominations and impeachments
        doc_type = page.xpath("//roll_call_vote/document/document_type/text()")[0]

        if page.xpath("//roll_call_vote/amendment/amendment_to_document_number/text()"):
            bill_id = page.xpath(
                "//roll_call_vote/amendment/amendment_to_document_number/text()"
            )[0].replace(".", "")
        else:
            bill_id = page.xpath("//roll_call_vote/document/document_name/text()")[
                0
            ].replace(".", "")

        motion = page.xpath("//roll_call_vote/vote_question_text/text()")[0]

        result_text = page.xpath("//roll_call_vote/vote_result/text()")[0]

        result = self.senate_statuses[result_text]

        vote = VoteEvent(
            start_date=when,
            bill_chamber="lower" if doc_type[0] == "H" else "upper",
            motion_text=motion,
            classification="passage",  # TODO
            result=result,
            legislative_session=session,
            identifier=vote_id,
            bill=bill_id,
            chamber="upper",
        )

        vote.add_source(url)

        vote.extras["senate-rollcall-num"] = roll_call

        yeas = page.xpath("//roll_call_vote/count/yeas/text()")[0]
        nays = page.xpath("//roll_call_vote/count/nays/text()")[0]

        if page.xpath("//roll_call_vote/count/absent/text()"):
            absents = page.xpath("//roll_call_vote/count/absent/text()")[0]
        else:
            absents = 0

        if page.xpath("//roll_call_vote/count/present/text()"):
            presents = page.xpath("//roll_call_vote/count/present/text()")[0]
        else:
            presents = 0

        vote.set_count("yes", int(yeas))
        vote.set_count("no", int(nays))
        vote.set_count("absent", int(absents))
        vote.set_count("abstain", int(presents))

        for row in page.xpath("//roll_call_vote/members/member"):
            lis_id = row.xpath("lis_member_id/text()")[0]
            name = row.xpath("member_full/text()")[0]
            choice = row.xpath("vote_cast/text()")[0]

            vote.vote(self.vote_codes[choice], name, note=lis_id)

        yield vote
