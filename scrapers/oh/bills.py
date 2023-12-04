import datetime
from openstates.scrape import Scraper, Bill, VoteEvent
import scrapelib
import pytz
import re
import dateutil

BAD_BILLS = [("134", "SB 92")]


class OHBillScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    # Vote Motion Dictionary was created by comparing vote codes to
    # the actions tables via dates and chambers. If it made sense, the
    # vote code was added to the below dictionary.
    _vote_motion_dict = {
        "confer_713": "Conference report agreed to",
        "confer_712": "Conference report agreed to",
        "msg_506": "Refused to concur in Senate amendments",
        "motion_913": "Passed",
        "motion_909": "Motion to reconsider",
        "final_510": "Motion to reconsider",
        "imm_consid_360": "Adopted",
        "pass_300": "Pass",
        "msg_reso_503": "Adopted",
        "intro_103": "Adopted",
        "intro_108": "Adopted",
        "intro_101": "Adopted",
        "concur_606": "Concurred in Senate amendments",
        "crpt_301": "Reported - Substitute",
        "adopt_reso_110": "Adopted",
        "intro_102": "Adopted",
        "concur_608": "Refused to concur in House amendments",
        "msg_507": "Concurred in Senate amendments",
        "pass_301": "Adopted",
        "third_407": "Passed - Amended",
        "concur_602": "Concurred in Senate amendments",
        "concur_622": "Concurred in Senate amendments",
        "amend_452": "Amended",
    }

    def scrape(self, session=None, chambers=None):
        # Bills endpoint can sometimes take a very long time to load
        self.timeout = 300
        self.headers[
            "User-Agent"
        ] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"

        if int(session) < 128:
            raise AssertionError(f"No data for period {session}")

        elif int(session) < 131:
            # they changed their data format starting in 131st and added
            # an undocumented API
            yield from self.old_scrape(session)

        else:
            chamber_dict = {
                "Senate": "upper",
                "House": "lower",
                "House of Representatives": "lower",
                "house": "lower",
                "senate": "upper",
            }

            # so presumably not everything passes, but we haven't
            # seen anything not pass yet, so we'll need to wait
            # till it fails and get the right language in here
            vote_results = {
                "approved": True,
                "passed": True,
                "adopted": True,
                "true": True,
                "false": False,
                "failed": False,
                True: True,
                False: False,
            }

            action_dict = {
                "ref_ctte_100": "referral-committee",
                "intro_100": "introduction",
                "intro_101": "introduction",
                "pass_300": "passage",
                "intro_110": "reading-1",
                "refer_210": "referral-committee",
                "crpt_301": None,
                "crpt_317": None,
                "concur_606": "passage",
                "pass_301": "passage",
                "refer_220": "referral-committee",
                "intro_102": ["introduction", "passage"],
                "intro_105": ["introduction", "passage"],
                "intro_ref_ctte_100": "referral-committee",
                "refer_209": None,
                "intro_108": ["introduction", "passage"],
                "intro_103": ["introduction", "passage"],
                "msg_reso_503": "passage",
                "intro_107": ["introduction", "passage"],
                "imm_consid_360": "passage",
                "refer_213": None,
                "adopt_reso_100": "passage",
                "adopt_reso_110": "passage",
                "msg_507": "amendment-passage",
                "confer_713": None,
                "concur_603": None,
                "confer_712": None,
                "msg_506": "amendment-failure",
                "receive_message_100": "passage",
                "motion_920": None,
                "concur_611": None,
                "confer_735": None,
                "third_429": None,
                "final_501": None,
                "concur_608": None,
                "infpass_217": "passage",
            }

            base_url = "https://search-prod.lis.state.oh.us"
            first_page = base_url
            first_page += "/solarapi/v1/general_assembly_{session}/".format(
                session=session
            )
            legislators = self.get_legislator_ids(first_page)
            all_amendments = self.get_other_data_source(
                first_page, base_url, "amendments"
            )
            all_fiscals = self.get_other_data_source(first_page, base_url, "fiscals")
            all_synopsis = self.get_other_data_source(first_page, base_url, "synopsiss")
            all_analysis = self.get_other_data_source(first_page, base_url, "analysiss")

            bills = self.get_total_bills(session)
            for bill in bills:
                bill_name = bill["name"]
                bill_number = bill["number"]

                # S.R.No.1 -> SR1
                bill_id = bill_name.replace("No.", "").strip()
                bill_id = bill_id.replace(".", "").replace(" ", "").strip()
                # put one space back in between type and number
                bill_id = re.sub(r"([a-zA-Z]+)(\d+)", r"\1 \2", bill_id)

                chamber = "lower" if "H" in bill_id else "upper"
                classification = "bill" if "B" in bill_id else "resolution"

                title = (
                    bill["shorttitle"] if bill["shorttitle"] else "No title provided"
                )
                bill = Bill(
                    bill_id,
                    legislative_session=session,
                    chamber=chamber,
                    title=title,
                    classification=classification,
                )
                bill.add_source(
                    f"https://www.legislature.ohio.gov/legislation/{session}/{bill_number}"
                )

                if (session, bill_id) in BAD_BILLS:
                    self.logger.warning(
                        f"Skipping details for known bad bill {bill_id}"
                    )
                    yield bill
                    continue

                # get bill from API
                bill_api_url = (
                    "https://search-prod.lis.state.oh.us/solarapi/v1/"
                    "general_assembly_{}/{}/{}/".format(
                        session,
                        "bills" if "B" in bill_id else "resolutions",
                        bill_id.lower().replace(" ", ""),
                    )
                )
                data = self.get(bill_api_url, verify=False).json()
                if len(data["items"]) == 0:
                    self.logger.warning(
                        "Data for bill {bill_id} has empty 'items' array,"
                        " cannot process related information".format(
                            bill_id=bill_id.lower().replace(" ", "")
                        )
                    )
                    yield bill
                    continue

                # add title if no short title
                if not bill.title:
                    bill.title = data["items"][0]["longtitle"]
                bill.add_title(data["items"][0]["longtitle"], "long title")

                # this stuff is version-specific
                for version in data["items"]:
                    version_name = version["version"]
                    version_link = base_url + version["pdfDownloadLink"]
                    bill.add_version_link(
                        version_name, version_link, media_type="application/pdf"
                    )

                # we'll use the latest bill_version for everything else
                bill_version = data["items"][0]
                bill.add_source(bill_api_url)

                # subjects
                for subj in bill_version["subjectindexes"]:
                    try:
                        bill.add_subject(subj["primary"])
                    except KeyError:
                        pass
                    try:
                        secondary_subj = subj["secondary"]
                    except KeyError:
                        secondary_subj = ""
                    if secondary_subj:
                        bill.add_subject(secondary_subj)

                # sponsors
                sponsors = bill_version["sponsors"]
                for sponsor in sponsors:
                    sponsor_name = self.get_sponsor_name(sponsor)
                    bill.add_sponsorship(
                        sponsor_name,
                        classification="primary",
                        entity_type="person",
                        primary=True,
                    )

                cosponsors = bill_version["cosponsors"]
                for sponsor in cosponsors:
                    sponsor_name = self.get_sponsor_name(sponsor)
                    bill.add_sponsorship(
                        sponsor_name,
                        classification="cosponsor",
                        entity_type="person",
                        primary=False,
                    )

                try:
                    action_doc = self.get(
                        base_url + bill_version["action"][0]["link"],
                        verify=False,
                    )
                except scrapelib.HTTPError:
                    pass
                else:

                    actions = action_doc.json()
                    for action in reversed(actions["items"]):
                        actor = chamber_dict[action["chamber"]]
                        action_desc = action["description"]
                        try:
                            action_type = action_dict[action["actioncode"]]
                        except KeyError:
                            self.warning(
                                "Unknown action {desc} with code {code}."
                                " Add it to the action_dict"
                                ".".format(desc=action_desc, code=action["actioncode"])
                            )
                            action_type = None

                        date = dateutil.parser.parse(action["datetime"])
                        if date.tzinfo is None:
                            date = self._tz.localize(date)

                        date = "{:%Y-%m-%d}".format(date)

                        bill.add_action(
                            action_desc, date, chamber=actor, classification=action_type
                        )

                # attach documents gathered earlier
                self.add_document(all_amendments, bill_id, "amendment", bill, base_url)
                self.add_document(all_fiscals, bill_id, "fiscal", bill, base_url)
                self.add_document(all_synopsis, bill_id, "synopsis", bill, base_url)
                self.add_document(all_analysis, bill_id, "analysis", bill, base_url)

                # votes
                vote_url = base_url + bill_version["votes"][0]["link"]
                try:
                    vote_doc = self.get(vote_url)
                except scrapelib.HTTPError:
                    self.warning("Vote page not loading; skipping: {}".format(vote_url))
                    yield bill
                    continue
                votes = vote_doc.json()
                yield from self.process_vote(
                    votes,
                    vote_url,
                    base_url,
                    bill,
                    legislators,
                    chamber_dict,
                    vote_results,
                )

                vote_url = base_url
                vote_url += bill_version["cmtevotes"][0]["link"]
                try:
                    vote_doc = self.get(vote_url)
                except scrapelib.HTTPError:
                    self.warning("Vote page not loading; skipping: {}".format(vote_url))
                    yield bill
                    continue
                votes = vote_doc.json()
                yield from self.process_vote(
                    votes,
                    vote_url,
                    base_url,
                    bill,
                    legislators,
                    chamber_dict,
                    vote_results,
                )

                if data["items"][0]["effective_date"]:
                    effective_date = datetime.datetime.strptime(
                        data["items"][0]["effective_date"], "%Y-%m-%d"
                    )
                    effective_date = self._tz.localize(effective_date)
                    # the OH website adds an action that isn't in the action list JSON.
                    # It looks like:
                    # Effective 7/6/18
                    effective_date_oh = "{:%-m/%-d/%y}".format(effective_date)
                    effective_action = "Effective {}".format(effective_date_oh)
                    bill.add_action(
                        effective_action,
                        effective_date,
                        chamber="executive",
                        classification=["became-law"],
                    )

                # we have never seen a veto or a disapprove, but they seem important.
                # so we'll check and throw an error if we find one
                # life is fragile. so are our scrapers.
                if "veto" in bill_version:
                    veto_url = base_url + bill_version["veto"][0]["link"]
                    veto_json = self.get(veto_url).json()
                    if len(veto_json["items"]) > 0:
                        raise AssertionError(
                            "Whoa, a veto! We've never"
                            " gotten one before."
                            " Go write some code to deal"
                            " with it: {}".format(veto_url)
                        )

                if "disapprove" in bill_version:
                    disapprove_url = base_url + bill_version["disapprove"][0]["link"]
                    disapprove_json = self.get(disapprove_url).json()
                    if len(disapprove_json["items"]) > 0:
                        raise AssertionError(
                            "Whoa, a disapprove! We've never"
                            " gotten one before."
                            " Go write some code to deal "
                            "with it: {}".format(disapprove_url)
                        )

                yield bill

    def pages(self, base_url, first_page):
        page = self.get(first_page)
        page = page.json()
        yield page
        while "nextLink" in page:
            page = self.get(base_url + page["nextLink"])
            page = page.json()
            yield page

    def get_total_bills(self, session):
        bills_url = f"https://search-prod.lis.state.oh.us/solarapi/v1/general_assembly_{session}/bills"
        bill_data = self.get(bills_url, verify=False).json()
        if len(bill_data["items"]) == 0:
            self.logger.warning("No bills")

        res_url = f"https://search-prod.lis.state.oh.us/solarapi/v1/general_assembly_{session}/resolutions"
        res_data = self.get(res_url, verify=False).json()
        if len(res_data["items"]) == 0:
            self.logger.warning("No resolutions")

        total_bills = bill_data["items"] + res_data["items"]
        return total_bills

    def get_other_data_source(self, first_page, base_url, source_name):
        # produces a dictionary from bill_id to a list of
        # one of the following:
        # amendments, analysis, fiscals, synopsis
        # could pull these by bill, but doing it in bulk
        # and then matching on our end will get us by with way fewer
        # api calls

        bill_dict = {}
        for page in self.pages(base_url, first_page + source_name):
            for item in page["items"]:
                billno = item["billno"]
                if billno not in bill_dict:
                    bill_dict[billno] = []
                bill_dict[billno].append(item)

        return bill_dict

    def add_document(self, documents, bill_id, type_of_document, bill, base_url):
        try:
            documents = documents[bill_id]
        except KeyError:
            return

        leg_ver_types = {
            "IN": "Introduction",
            "RS": "Reported: Senate",
            "PS": "Passed: Senate",
            "RH": "Reported: House",
            "PH": "Passed: House",
            "": "",
            "ICS": "",
            "IC": "",
            "RCS": "",
            "EN": "Enacted",
            "RCH": "Re-referred",
            "RRH": "",
            "PHC": "",
            "CR": "",
        }

        for item in documents:
            if type_of_document == "amendment":
                name = item["amendnum"] + " " + item["version"]
            else:
                name = item["name"] or type_of_document
            link = base_url + item["link"] + "?format=pdf"
            try:
                self.head(link)
            except scrapelib.HTTPError:
                self.logger.warning(
                    "The link to doc {name}"
                    " does not exist, skipping".format(name=name)
                )
                continue
            if "legacyver" in item:
                try:
                    ver = leg_ver_types[item["legacyver"]]
                except KeyError:
                    self.logger.warning(
                        "New legacyver; check the type and add it to the "
                        "leg_ver_types dictionary: {} ({})".format(
                            item["legacyver"], item["link"]
                        )
                    )
                    ver = ""
                if ver:
                    name = name + ": " + ver
            bill.add_document_link(name, link, media_type="application/pdf")

    def get_legislator_ids(self, base_url):
        legislators = {}
        for chamber in ["House", "Senate"]:
            url = base_url + "chamber/{chamber}/legislators?per_page=100"
            doc = self.get(
                url.format(chamber=chamber),
                verify=False,
            )
            leg_json = doc.json()
            for leg in leg_json["items"]:
                if leg["med_id"]:
                    legislators[int(leg["med_id"])] = leg["displayname"]
        return legislators

    def get_sponsor_name(self, sponsor):
        return " ".join([sponsor["firstname"], sponsor["lastname"]])

    def process_vote(
        self, votes, url, base_url, bill, legislators, chamber_dict, vote_results
    ):
        for v in votes["items"]:
            try:
                v["yeas"]
            except KeyError:
                # sometimes the actual vote is buried a second layer deep
                v = self.get(base_url + v["link"]).json()
                try:
                    v["yeas"]
                except KeyError:
                    self.logger.warning("No vote info available, skipping")
                    continue

            try:
                chamber = chamber_dict[v["chamber"]]
            except KeyError:
                chamber = "lower" if "house" in v["apn"] else "upper"
            try:
                date = self._tz.localize(
                    datetime.datetime.strptime(v["date"], "%m/%d/%y")
                )
                date = "{:%Y-%m-%d}".format(date)
            except KeyError:
                try:
                    date = self._tz.localize(
                        datetime.datetime.strptime(v["occurred"], "%m/%d/%y")
                    )
                    date = "{:%Y-%m-%d}".format(date)
                except KeyError:
                    self.logger.warning("No date found for vote, skipping")
                    continue
            try:
                motion = v["action"]
            except KeyError:
                motion = v["motiontype"]

            if motion in self._vote_motion_dict:
                motion_text = self._vote_motion_dict[motion]
            else:
                self.warning(
                    "Unknown vote code {}, please add to _vote_motion_dict".format(
                        motion
                    )
                )
                motion_text = v["results"]

            # Sometimes Ohio's SOLAR will only return part of the JSON, so in that case skip
            if not motion and isinstance(v["yeas"], str) and isinstance(v["nays"], str):
                waringText = 'Malformed JSON found for vote ("revno" of {}); skipping'
                self.warning(waringText.format(v["revno"]))
                continue

            result = v.get("results") or v.get("passed")
            if result is None:
                if len(v["yeas"]) > len(v["nays"]):
                    result = "passed"
                else:
                    result = "failed"

            passed = vote_results[result.lower()]
            if "committee" in v:
                vote = VoteEvent(
                    chamber=chamber,
                    start_date=date,
                    motion_text=motion_text,
                    result="pass" if passed else "fail",
                    # organization=v["committee"],
                    bill=bill,
                    classification="committee-passage",
                )
            else:
                vote = VoteEvent(
                    chamber=chamber,
                    start_date=date,
                    motion_text=motion_text,
                    result="pass" if passed else "fail",
                    classification="passage",
                    bill=bill,
                )
            # Concatenate the bill identifier and vote identifier to avoid collisions
            vote.dedupe_key = "{}:{}".format(
                bill.identifier.replace(" ", ""), v["revno"]
            )
            # the yea and nay counts are not displayed, but vote totals are
            # and passage status is.
            yes_count = 0
            no_count = 0
            absent_count = 0
            excused_count = 0
            for voter_id in v["yeas"]:
                vote.yes(legislators[voter_id])
                yes_count += 1
            for voter_id in v["nays"]:
                vote.no(legislators[voter_id])
                no_count += 1
            if "absent" in v:
                for voter_id in v["absent"]:
                    vote.vote("absent", legislators[voter_id])
                    absent_count += 1
            if "excused" in v:
                for voter_id in v["excused"]:
                    vote.vote("excused", legislators[voter_id])
                    excused_count += 1

            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("absent", absent_count)
            vote.set_count("excused", excused_count)
            # check to see if there are any other things that look
            # like vote categories, throw a warning if so
            for key, val in v.items():
                if (
                    type(val) == list
                    and len(val) > 0
                    and key not in ["yeas", "nays", "absent", "excused"]
                ):
                    if val[0] in legislators:
                        self.logger.warning(
                            "{k} looks like a vote type that's not being counted."
                            " Double check it?".format(k=key)
                        )
            vote.add_source(url)

            yield vote
