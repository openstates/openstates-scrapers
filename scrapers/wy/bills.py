import re
import pytz
import datetime
import json

from openstates.scrape import Scraper, Bill, VoteEvent
import scrapelib

from utils import LXMLMixin


TIMEZONE = pytz.timezone("US/Mountain")


def categorize_action(action):
    categorizers = (
        ("Introduced and Referred", ("introduction", "referral-committee")),
        ("Rerefer to", "referral-committee"),
        ("Do Pass Failed", "committee-failure"),
        ("2nd Reading:Passed", "reading-2"),
        ("3rd Reading:Passed", ("reading-3", "passage")),
        ("Failed 3rd Reading", ("reading-3", "failure")),
        ("Did Not Adopt", "amendment-failure"),
        ("Withdrawn by Sponsor", "withdrawal"),
        ("Line Item Veto", "executive-veto-line-item"),
        ("Governor Signed", "executive-signature"),
        ("Recommend (Amend and )?Do Pass", "committee-passage-favorable"),
        ("Recommend (Amend and )?Do Not Pass", "committee-passage-unfavorable"),
        ("Received for Introduction", "filing"),
    )

    for pattern, types in categorizers:
        if re.findall(pattern, action):
            return types
    return None


class WYBillScraper(Scraper, LXMLMixin):
    chamber_abbrev_map = {"H": "lower", "S": "upper"}
    is_special = False

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber_abbrev = {"upper": "S", "lower": "H"}[chamber]

        # pull the current session's details to tell if it's a special
        session_details = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )

        if session_details["classification"] == "special":
            self.is_special = True
            bill_json_url = (
                "http://wyoleg.gov/LsoService/api/BillInformation?"
                "$filter=Year%20eq%202020%20and%20SpecialSessionValue%20ne%20null&$orderby=BillNum".format(session[0:4])
            )
        else:
            bill_json_url = (
                "http://wyoleg.gov/LsoService/api/BillInformation?"
                "$filter=Year%20eq%20{}&$orderby=BillNum".format(session)
            )

        response = self.get(bill_json_url)
        bill_list = json.loads(response.content.decode("utf-8"))

        for bill_json in bill_list:
            if bill_json["billType"][0] == chamber_abbrev:
                yield from self.scrape_bill(bill_json["billNum"], session)

    def scrape_bill(self, bill_num, session):
        chamber_map = {"House": "lower", "Senate": "upper", "LSO": "executive"}
        # Sample with all keys: https://gist.github.com/showerst/d6cd03eff3e8b12ab01dbb219876db45
        bill_json_url = (
            "http://wyoleg.gov/LsoService/api/BillInformation/{}/"
            "{}?calendarDate=".format(session, bill_num)
        )

        if self.is_special == True:
            bill_json_url = (
                "http://wyoleg.gov/LsoService/api/BillInformation/{}/"
                "{}?specialSessionValue=1&calendarDate=".format(session[0:4], bill_num)
            )

        try:
            response = self.get(bill_json_url)
            bill_json = json.loads(response.content.decode("utf-8"))
        except scrapelib.HTTPError:
            return None

        chamber = "lower" if bill_json["bill"][0] else "upper"

        bill = Bill(
            identifier=bill_json["bill"],
            legislative_session=session,
            title=bill_json["catchTitle"],
            chamber=chamber,
            classification="bill",
        )

        bill.add_title(bill_json["billTitle"])

        source_url = "http://lso.wyoleg.gov/Legislation/{}/{}".format(
            session, bill_json["bill"]
        )

        if self.is_special == True:
            source_url = "http://lso.wyoleg.gov/Legislation/{}/{}?specialSessionValue=1".format(
                session[0:4], bill_json["bill"]
            )

        bill.add_source(source_url)

        for action_json in bill_json["billActions"]:
            utc_action_date = self.parse_local_date(action_json["statusDate"])

            actor = None
            if action_json["location"] and action_json["location"] in chamber_map:
                actor = chamber_map[action_json["location"]]

            action = bill.add_action(
                chamber=actor,
                description=action_json["statusMessage"],
                date=utc_action_date,
                classification=categorize_action(action_json["statusMessage"]),
            )

            action.extras = {"billInformationID": action_json["billInformationID"]}

        if bill_json["introduced"]:
            url = "http://wyoleg.gov/{}".format(bill_json["introduced"])

            bill.add_version_link(
                note="Introduced",
                url=url,
                media_type="application/pdf",  # optional but useful!
            )

        if bill_json["enrolledAct"]:
            url = "http://wyoleg.gov/{}".format(bill_json["enrolledAct"])

            bill.add_version_link(
                note="Enrolled",
                url=url,
                media_type="application/pdf",  # optional but useful!
            )

        if bill_json["fiscalNote"]:
            url = "http://wyoleg.gov/{}".format(bill_json["fiscalNote"])

            bill.add_document_link(
                note="Fiscal Note",
                url=url,
                media_type="application/pdf",  # optional but useful!
            )

        if bill_json["digest"]:
            url = "http://wyoleg.gov/{}".format(bill_json["digest"])

            bill.add_document_link(
                note="Bill Digest",
                url=url,
                media_type="application/pdf",  # optional but useful!
            )

        if bill_json["vetoes"]:
            for veto in bill_json["vetoes"]:
                url = "http://wyoleg.gov/{}".format(veto["vetoLinkPath"])
                bill.add_version_link(
                    note=veto["vetoLinkText"],
                    url=url,
                    media_type="application/pdf",  # optional but useful!
                )

        for amendment in bill_json["amendments"]:
            # http://wyoleg.gov/2018/Amends/SF0050H2001.pdf
            url = "http://wyoleg.gov/{}/Amends/{}.pdf".format(
                session[0:4], amendment["amendmentNumber"]
            )

            if amendment["sponsor"] and amendment["status"]:
                title = "Amendment {} ({}) - {} ({})".format(
                    amendment["amendmentNumber"],
                    amendment["order"],
                    amendment["sponsor"],
                    amendment["status"],
                )
            else:
                title = "Amendment {} ({})".format(
                    amendment["amendmentNumber"], amendment["order"]
                )
            # add versions of the bill text
            version = bill.add_version_link(
                note=title, url=url, media_type="application/pdf"
            )
            version["extras"] = {
                "amendmentNumber": amendment["amendmentNumber"],
                "sponsor": amendment["sponsor"],
            }

        for sponsor in bill_json["sponsors"]:
            status = "primary" if sponsor["primarySponsor"] else "cosponsor"
            sponsor_type = "person" if sponsor["sponsorTitle"] else "organization"
            bill.add_sponsorship(
                name=sponsor["name"],
                classification=status,
                entity_type=sponsor_type,
                primary=sponsor["primarySponsor"],
            )

        if bill_json["summary"]:
            bill.add_abstract(note="summary", abstract=bill_json["summary"])

        if bill_json["enrolledNumber"]:
            bill.extras["wy_enrolled_number"] = bill_json["enrolledNumber"]

        if bill_json["chapter"]:
            bill.extras["chapter"] = bill_json["chapter"]

        if bill_json["effectiveDate"]:
            eff = datetime.datetime.strptime(bill_json["effectiveDate"], "%m/%d/%Y")
            bill.extras["effective_date"] = eff.strftime("%Y-%m-%d")

        bill.extras["wy_bill_id"] = bill_json["id"]

        for vote_json in bill_json["rollCalls"]:
            yield from self.scrape_vote(bill, vote_json, session[0:4])

        yield bill

    def scrape_vote(self, bill, vote_json, session):

        if vote_json["amendmentNumber"]:
            motion = "{}: {}".format(vote_json["amendmentNumber"], vote_json["action"])
        else:
            motion = vote_json["action"]

        result = (
            "pass" if vote_json["yesVotesCount"] > vote_json["noVotesCount"] else "fail"
        )

        v = VoteEvent(
            chamber=self.chamber_abbrev_map[vote_json["chamber"]],
            start_date=self.parse_local_date(vote_json["voteDate"]),
            motion_text=motion,
            result=result,
            legislative_session=session,
            bill=bill,
            classification="other",
        )

        v.set_count(option="yes", value=vote_json["yesVotesCount"])
        v.set_count("no", vote_json["noVotesCount"])
        v.set_count("absent", vote_json["absentVotesCount"])
        v.set_count("excused", vote_json["excusedVotesCount"])
        v.set_count("other", vote_json["conflictVotesCount"])

        for name in vote_json["yesVotes"].split(","):
            if name:
                name = name.strip()
                v.yes(name)

        for name in vote_json["noVotes"].split(","):
            if name:
                name = name.strip()
                v.no(name)

        # add votes with other classifications
        # option can be 'yes', 'no', 'absent',
        # 'abstain', 'not voting', 'paired', 'excused'
        for name in vote_json["absentVotes"].split(","):
            if name:
                name = name.strip()
                v.vote(option="absent", voter=name)

        for name in vote_json["excusedVotes"].split(","):
            if name:
                name = name.strip()
                v.vote(option="excused", voter=name)

        for name in vote_json["conflictVotes"].split(","):
            if name:
                name = name.strip()
                v.vote(option="other", voter=name)

        source_url = "http://lso.wyoleg.gov/Legislation/{}/{}".format(
            session, vote_json["billNumber"]
        )
        v.add_source(source_url)

        yield v

    def parse_local_date(self, date_str):
        # provided dates are ISO 8601, but in mountain time
        # and occasionally have fractional time at the end
        if "." not in date_str:
            date_str = date_str + ".0"

        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
        # Truncate microseconds; schema limits action date to 25 characters
        date_obj = date_obj.replace(microsecond=0)
        local_date = TIMEZONE.localize(date_obj)
        utc_action_date = local_date.astimezone(pytz.utc)
        return utc_action_date
