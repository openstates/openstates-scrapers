import re
from collections import defaultdict

from openstates.scrape import Scraper, Bill, VoteEvent

from .util import get_client, get_url, backoff, SESSION_SITE_IDS

#         Methods (7):
#            GetLegislationDetail(xs:int LegislationId, )
#
#            GetLegislationDetailByDescription(ns2:DocumentType DocumentType,
#                                              xs:int Number, xs:int SessionId)
#
#            GetLegislationForSession(xs:int SessionId, )
#
#            GetLegislationRange(ns2:LegislationIndexRangeSet Range, )
#
#            GetLegislationRanges(xs:int SessionId,
#                           ns2:DocumentType DocumentType, xs:int RangeSize, )
#
#            GetLegislationSearchResultsPaged(ns2:LegislationSearchConstraints
#                                               Constraints, xs:int PageSize,
#                                               xs:int StartIndex, )
#            GetTitles()


member_cache = {}
SOURCE_URL = "https://www.legis.ga.gov/legislation/{bid}"

vote_name_pattern = re.compile(r"(.*), (\d+(?:ST|ND|RD|TH))", re.IGNORECASE)


class GABillScraper(Scraper):
    lservice = get_client("Legislation").service
    vservice = get_client("Votes").service
    mservice = get_client("Members").service
    lsource = get_url("Legislation")
    msource = get_url("Members")
    vsource = get_url("Votes")

    def get_member(self, member_id):
        if member_id in member_cache:
            return member_cache[member_id]

        mem = backoff(self.mservice.GetMember, member_id)
        member_cache[member_id] = mem
        return mem

    def scrape(self, session=None, chamber=None):
        bill_type_map = {
            "B": "bill",
            "R": "resolution",
            "JR": "joint resolution",
            "CR": "concurrent resolution",
        }

        chamber_map = {
            "H": "lower",
            "S": "upper",
            "J": "joint",
            "E": "legislature",  # Effective date
        }

        action_code_map = {
            "HI": None,
            "SI": None,
            "HH": None,
            "SH": None,
            "HPF": ["introduction"],
            "HDSAS": None,
            "SPF": ["introduction"],
            "HSR": ["reading-2"],
            "SSR": ["reading-2"],
            "HFR": ["reading-1"],
            "SFR": ["reading-1"],
            "HRECM": ["withdrawal", "referral-committee"],
            "SRECM": ["withdrawal", "referral-committee"],
            "SW&C": ["withdrawal", "referral-committee"],
            "HW&C": ["withdrawal", "referral-committee"],
            "HRA": ["passage"],
            "SRA": ["passage"],
            "HPA": ["passage"],
            "HRECO": None,
            "SPA": ["passage"],
            "HTABL": None,  # 'House Tabled' - what is this?
            "SDHAS": None,
            "HCFR": ["committee-passage-favorable"],
            "SCFR": ["committee-passage-favorable"],
            "HRAR": ["referral-committee"],
            "SRAR": ["referral-committee"],
            "STR": ["reading-3"],
            "SAHAS": None,
            "SE": ["passage"],
            "SR": ["referral-committee"],
            "HTRL": ["reading-3", "failure"],
            "HTR": ["reading-3"],
            "S3RLT": ["reading-3", "failure"],
            "HASAS": None,
            "S3RPP": None,
            "STAB": None,
            "SRECO": None,
            "SAPPT": None,
            "HCA": None,
            "HNOM": None,
            "HTT": None,
            "STT": None,
            "SRECP": None,
            "SCRA": None,
            "SNOM": None,
            "S2R": ["reading-2"],
            "H2R": ["reading-2"],
            "SENG": ["passage"],
            "HENG": ["passage"],
            "HPOST": None,
            "HCAP": None,
            "SDSG": ["executive-signature"],
            "SSG": ["executive-receipt"],
            "Signed Gov": ["executive-signature"],
            "HDSG": ["executive-signature"],
            "HSG": ["executive-receipt"],
            "EFF": None,
            "HRP": None,
            "STH": None,
            "HTS": None,
        }
        sid = SESSION_SITE_IDS[session]

        legislation = backoff(self.lservice.GetLegislationForSession, sid)[
            "LegislationIndex"
        ]

        for leg in legislation:
            lid = leg["Id"]
            instrument = backoff(self.lservice.GetLegislationDetail, lid)
            history = [x for x in instrument["StatusHistory"][0]]

            actions = reversed(
                [
                    {
                        "code": x["Code"],
                        "action": x["Description"],
                        "_guid": x["Id"],
                        "date": x["Date"],
                    }
                    for x in history
                ]
            )

            guid = instrument["Id"]

            # A little bit hacky.
            bill_prefix = instrument["DocumentType"]
            bill_chamber = chamber_map[bill_prefix[0]]
            bill_type = bill_type_map[bill_prefix[1:]]

            bill_id = "%s %s" % (bill_prefix, instrument["Number"])
            if instrument["Suffix"]:
                bill_id += instrument["Suffix"]

            # special session bills get a suffix that doesn't show up in the site
            bill_id = bill_id.replace("EX", "")

            title = instrument["Caption"]
            description = instrument["Summary"]

            if title is None:
                continue

            bill = Bill(
                bill_id,
                legislative_session=session,
                chamber=bill_chamber,
                title=title,
                classification=bill_type,
            )
            bill.add_abstract(description, note="description")
            bill.extras = {"guid": guid}

            if instrument["Votes"]:
                for vote_ in instrument["Votes"]:
                    _, vote_ = vote_
                    vote_ = backoff(self.vservice.GetVote, vote_[0]["VoteId"])

                    vote = VoteEvent(
                        start_date=vote_["Date"].strftime("%Y-%m-%d"),
                        motion_text=vote_["Caption"] or "Vote on Bill",
                        chamber={"House": "lower", "Senate": "upper"}[vote_["Branch"]],
                        result="pass" if vote_["Yeas"] > vote_["Nays"] else "fail",
                        classification="passage",
                        bill=bill,
                    )
                    vote.set_count("yes", vote_["Yeas"])
                    vote.set_count("no", vote_["Nays"])
                    vote.set_count("other", vote_["Excused"] + vote_["NotVoting"])

                    vote.add_source(self.vsource)

                    methods = {"Yea": "yes", "Nay": "no"}

                    if vote_["Votes"] is not None:
                        for vdetail in vote_["Votes"][0]:
                            whom = vdetail["Member"]
                            how = vdetail["MemberVoted"]
                            if whom["Name"] == "VACANT":
                                continue
                            name, district = vote_name_pattern.search(
                                whom["Name"]
                            ).groups()
                            vote.vote(methods.get(how, "other"), name, note=district)

                    yield vote

            ccommittees = defaultdict(list)
            committees = instrument["Committees"]
            if committees:
                for committee in committees[0]:
                    ccommittees[
                        {"House": "lower", "Senate": "upper"}[committee["Type"]]
                    ].append(committee["Name"])

            for action in actions:
                action_chamber = chamber_map[action["code"][0]]

                try:
                    action_types = action_code_map[action["code"]]
                except KeyError:
                    error_msg = (
                        "Code {code} for action {action} not recognized.".format(
                            code=action["code"], action=action["action"]
                        )
                    )

                    self.logger.warning(error_msg)

                    action_types = None

                committees = []
                if action_types and any(("committee" in x for x in action_types)):
                    committees = [str(x) for x in ccommittees.get(action_chamber, [])]

                act = bill.add_action(
                    action["action"],
                    action["date"].strftime("%Y-%m-%d"),
                    classification=action_types,
                    chamber=action_chamber,
                )
                for committee in committees:
                    act.add_related_entity(committee, "organization")
                act.extras = {"code": action["code"], "guid": action["_guid"]}

            sponsors = []
            if instrument["Authors"]:
                sponsors = instrument["Authors"]["Sponsorship"]
                if "Sponsors" in instrument and instrument["Sponsors"]:
                    sponsors += instrument["Sponsors"]["Sponsorship"]

            # 4976 is Sheila McNeill
            # whose profile is currently causing 500 errors
            sponsors = [
                (x["Type"], self.get_member(x["MemberId"]))
                for x in sponsors
                if x["MemberId"] != 4976
            ]

            for typ, sponsor in sponsors:
                name = "{First} {Last}".format(**dict(sponsor["Name"]))
                bill.add_sponsorship(
                    name,
                    entity_type="person",
                    classification="primary" if "Author" in typ else "secondary",
                    primary="Author" in typ,
                )

            for version in instrument["Versions"]["DocumentDescription"]:
                name, url, doc_id, version_id = [
                    version[x] for x in ["Description", "Url", "Id", "Version"]
                ]
                link = bill.add_version_link(name, url, media_type="application/pdf")
                link["extras"] = {
                    "_internal_document_id": doc_id,
                    "_version_id": version_id,
                }

            bill.add_source(self.msource)
            bill.add_source(self.lsource)
            bill.add_source(SOURCE_URL.format(**{"session": session, "bid": guid}))

            yield bill
