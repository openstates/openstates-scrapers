import re
import datetime
from urllib.parse import urljoin
import os
from collections import OrderedDict

import scrapelib
import pytz

from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.utils import convert_pdf

from .apiclient import ApiClient
from .actions import Categorizer

settings = dict(SCRAPELIB_TIMEOUT=600)

PROXY_BASE_URL = "https://in-proxy.openstates.org"
SCRAPE_WEB_VERSIONS = "INDIANA_SCRAPE_WEB_VERSIONS" in os.environ


class INBillScraper(Scraper):
    categorizer = Categorizer()

    jurisdiction = "in"

    _tz = pytz.timezone("US/Eastern")

    def _get_bill_id_components(self, bill_id):
        bill_prefix = "".join([c for c in bill_id if c.isalpha()])
        bill_number = "".join([c for c in bill_id if c.isdigit()]).lstrip("0")

        return (bill_prefix, bill_number)

    def _add_sponsor_if_not_blank(self, bill, sponsor, classification):
        primary = classification in ("author", "sponsor")
        name = " ".join([sponsor["firstName"], sponsor["lastName"]]).strip()
        if name:
            bill.add_sponsorship(
                classification=classification,
                name=name,
                entity_type="person",
                primary=primary,
            )

    def _get_bill_url(self, session, bill_id):
        bill_prefix, bill_number = self._get_bill_id_components(bill_id)

        url_template = "https://iga.in.gov/legislative/{}/{}/{}"

        try:
            url_segment = self._bill_prefix_map[bill_prefix]["url_segment"]
        except KeyError:
            raise AssertionError(
                "Unknown bill type {}, don't know how to " "make url.".format(bill_id)
            )

        return url_template.format(session, url_segment, bill_number)

    def _process_votes(self, rollcalls, bill_id, original_chamber, session):
        result_types = {
            "FAILED": False,
            "DEFEATED": False,
            "PREVAILED": True,
            "PASSED": True,
            "SUSTAINED": True,
            "NOT SECONDED": False,
            "OVERRIDDEN": True,
            "ADOPTED": True,
        }

        for r in rollcalls:
            proxy_link = PROXY_BASE_URL + r["link"]

            try:
                (path, resp) = self.urlretrieve(proxy_link)
            except scrapelib.HTTPError as e:
                self.warning(e)
                self.warning(
                    "Unable to contact openstates proxy, skipping vote {}".format(
                        r["link"]
                    )
                )
                continue

            text = convert_pdf(path, "text").decode("utf-8")

            lines = text.split("\n")
            os.remove(path)

            chamber = (
                "lower" if "house of representatives" in lines[0].lower() else "upper"
            )
            date_parts = lines[1].strip().split()[-3:]
            date_str = " ".join(date_parts).title() + " " + lines[2].strip()
            vote_date = datetime.datetime.strptime(date_str, "%b %d, %Y %I:%M:%S %p")
            vote_date = pytz.timezone("America/Indiana/Indianapolis").localize(
                vote_date
            )
            vote_date = vote_date.isoformat()

            passed = None

            for res, val in result_types.items():
                # We check multiple lines now because the result of the
                # roll call vote as parsed can potentially be split.
                # PDF documents suck.
                for line in lines[3:5]:
                    if res in line.upper():
                        passed = val
                        break
            if passed is None:
                raise AssertionError("Missing bill passage type")

            for line_num in range(4, 8):
                if "Yea " in lines[line_num]:
                    break
            motion = " ".join(lines[line_num].split()[:-2]).strip()

            yeas, nays, excused, not_voting = [""] * 4
            for line in lines[4:10]:
                if "Yea " in line:
                    yeas = int(line.split()[-1])
                elif "Nay" in line:
                    nays = int(line.split()[-1])
                elif "Excused " in line:
                    excused = int(line.split()[-1])
                elif "Not Voting " in line:
                    not_voting = int(line.split()[-1])

            if any(val == "" for val in [yeas, nays, excused, not_voting]):
                self.logger.warning("Vote format is weird, skipping")
                continue

            vote = VoteEvent(
                chamber=chamber,
                legislative_session=session,
                bill=bill_id,
                bill_chamber=original_chamber,
                start_date=vote_date,
                motion_text=motion,
                result="pass" if passed else "fail",
                classification="passage",
            )

            vote.set_count("yes", yeas)
            vote.set_count("no", nays)
            vote.set_count("excused", excused)
            vote.set_count("not voting", not_voting)
            vote.add_source(proxy_link)

            currently_counting = ""

            possible_vote_lines = lines[8:]
            for line in possible_vote_lines:
                line = line.replace("NOT\xc2\xa0VOTING", "NOT VOTING")
                line = line.replace("\xc2\xa0", " -")
                if "yea-" in line.lower().replace(" ", ""):
                    currently_counting = "yes"
                elif "nay-" in line.lower().replace(" ", ""):
                    currently_counting = "no"
                elif "excused-" in line.lower().replace(" ", ""):
                    currently_counting = "excused"
                elif "notvoting-" in line.lower().replace(" ", ""):
                    currently_counting = "not voting"
                elif currently_counting == "":
                    pass
                elif re.search(r"v\. \d\.\d", line):
                    # this gets rid of the version number
                    # which is often found at the bottom of the doc
                    pass
                else:
                    voters = line.split("  ")
                    for v in voters:
                        if v.strip():
                            vote.vote(currently_counting, v.strip())

            yield vote

    def deal_with_latest_version(
        self,
        version,
        bill,
        api_base_url,
    ):
        # documents
        docs = OrderedDict()
        docs["Committee Amendment"] = version.get("cmte_amendments", [])
        docs["Floor Amendment"] = version.get("floor_amendments", [])
        docs["Amendment"] = version.get("amendments", [])
        docs["Fiscal Note"] = version.get("fiscal-notes", [])
        docs["Committee Report"] = version.get("committee-reports", [])

        # sometimes amendments appear in multiple places
        # cmte_amendment vs amendment
        # so we're only adding once but using the more
        # specific if it's available
        urls_seen = []
        for doc_type in docs:
            doc_list = docs[doc_type]
            for doc in doc_list:
                title = "{doc_type}: {name}".format(doc_type=doc_type, name=doc["name"])
                link = f"{api_base_url}{doc['link']}?format=pdf"
                if link not in urls_seen:
                    urls_seen.append(link)
                    bill.add_document_link(
                        note=title, url=link, media_type="application/pdf"
                    )

        # version which can sometimes have the wrong stageVerbose
        # add check that last letter of printVersionName matches
        # ex: stageVerbose being House Bill (H)
        # and printVersionName being HB1189.03.COMS and the link
        # being for HB1189.03.COMS which is the Senate bill
        # some example bills in 2020 are HB1189, SB241, SB269, HC18
        versions_match = True
        # get version chamber and api name, check chamber
        version_chamber = version["printVersionName"][-1]
        api_version_name = version["stageVerbose"]
        # check any versions not enrolled or introduced which are correct
        api_name_chamber = re.search(
            r"^(?:Engrossed |)(?:House|Senate) (?:Bill|Resolution) \((.)\)",
            api_version_name,
        )
        if api_name_chamber is not None:
            if version_chamber != api_name_chamber[1]:
                versions_match = False

        link = f"{api_base_url}{version['link']}?format=pdf"
        # if the chambers don't match, swap the chamber on version name
        # ex: Engrossed Senate Bill (S) to Engrossed Senate Bill (H)
        name = (
            api_version_name
            if versions_match
            else api_version_name[:-2] + version_chamber + api_version_name[-1:]
        )
        if link not in urls_seen:
            urls_seen.append(link)
            update_date = version["updated"]
            create_date = version["created"]
            intro_date = version["introduced"]
            file_date = version["filed"]
            for d in [update_date, create_date, intro_date, file_date]:
                try:
                    # pupa choked when I passed datetimes, so passing dates only.
                    # If we figure out how to make pupa not choke, here's the line you want:
                    # ## #
                    # self._tz.localize(datetime.datetime.strptime(d, "%Y-%m-%dT%H:%M:%S"))
                    update_date = datetime.datetime.strptime(
                        d, "%Y-%m-%dT%H:%M:%S"
                    ).date()
                except TypeError:
                    continue
                else:
                    break

            bill.add_version_link(
                note=name, url=link, media_type="application/pdf", date=update_date
            )

    def scrape(self, session=None):
        self._bill_prefix_map = {
            "HB": {"type": "bill", "url_segment": "bills/house"},
            "HR": {"type": "resolution", "url_segment": "resolutions/house/simple"},
            "HCR": {
                "type": "concurrent resolution",
                "url_segment": "resolutions/house/concurrent",
            },
            "HJR": {
                "type": "joint resolution",
                "url_segment": "resolutions/house/joint",
            },
            "HC": {
                "type": "concurrent resolution",
                "url_segment": "resolutions/house/concurrent",
            },
            "HJ": {
                "type": "joint resolution",
                "url_segment": "resolutions/house/joint",
            },
            "SB": {"type": "bill", "url_segment": "bills/senate"},
            "SR": {"type": "resolution", "url_segment": "resolutions/senate/simple"},
            "SCR": {
                "type": "concurrent resolution",
                "url_segment": "resolutions/senate/concurrent",
            },
            "SJR": {
                "type": "joint resolution",
                "url_segment": "resolutions/senate/joint",
            },
            "SC": {
                "type": "concurrent resolution",
                "url_segment": "resolutions/senate/concurrent",
            },
            "SJ": {
                "type": "joint resolution",
                "url_segment": "resolutions/senate/joint",
            },
        }

        # ah, indiana. it's really, really hard to find
        # pdfs in their web interface. Super easy with
        # the api, but a key needs to be passed
        # in the headers. To make these documents
        # viewable to the public and our scrapers,
        # we've put up a proxy service at this link
        # using our api key for pdf document access.

        client = ApiClient(self)
        api_base_url = client.root
        self.session_no = client.get_session_no(session)
        r = client.get("bills", session=session)
        all_pages = client.unpaginate(r)

        # if you need to test a single bill:
        # all_pages = [
        #     {"billName": "SB0001", "displayName": "SB 1", "link": "/2023/bills/sb0001/"}
        # ]

        for b in all_pages:
            bill_id = b["billName"]
            disp_bill_id = b["displayName"]
            bill_link = b["link"]

            api_source = urljoin(api_base_url, bill_link)

            try:
                bill_json = client.get("bill", session=session, bill_link=bill_link)
            except scrapelib.HTTPError:
                self.logger.warning("Bill could not be accessed. Skipping.")
                continue

            # vehicle bill
            if len(list(bill_json.keys())) == 0:
                self.logger.warning("Vehicle Bill: {}".format(bill_id))
                continue
            # sometimes description is blank
            # if that's the case, we can check to see if
            # the latest version has a short description
            title = bill_json["description"]
            if "NoneNone" in title:
                title = None
            if not title:
                title = bill_json["latestVersion"]["shortDescription"]
            # and if that doesn't work, use the bill_id but throw a warning
            if not title:
                title = bill_id
                self.logger.warning("Bill is missing a title, using bill id instead.")

            bill_prefix = self._get_bill_id_components(bill_id)[0]

            original_chamber = (
                "lower" if bill_json["originChamber"].lower() == "house" else "upper"
            )
            bill_type = self._bill_prefix_map[bill_prefix]["type"]
            bill = Bill(
                disp_bill_id,
                legislative_session=session,
                chamber=original_chamber,
                title=title,
                classification=bill_type,
            )

            bill.add_source(self._get_bill_url(session, bill_id))
            bill.add_source(api_source)

            # sponsors
            for s in bill_json["authors"]:
                self._add_sponsor_if_not_blank(bill, s, classification="author")
            for s in bill_json["coauthors"]:
                self._add_sponsor_if_not_blank(bill, s, classification="coauthor")
            for s in bill_json["sponsors"]:
                self._add_sponsor_if_not_blank(bill, s, classification="sponsor")
            for s in bill_json["cosponsors"]:
                self._add_sponsor_if_not_blank(bill, s, classification="cosponsor")

            # actions
            action_link = bill_json["actions"]["link"]
            api_source = urljoin(api_base_url, action_link)

            try:
                actions = client.get(
                    "bill_actions", session=session, action_link=action_link
                )
                actions = client.unpaginate(actions)
            except scrapelib.HTTPError:
                self.logger.warning("Could not find bill actions page")
                actions = []

            for a in actions:
                action_desc = a["description"]
                if "governor" in action_desc.lower():
                    action_chamber = "executive"
                elif a["chamber"]["name"].lower() == "house":
                    action_chamber = "lower"
                else:
                    action_chamber = "upper"
                date = a["date"]

                if not date:
                    self.logger.warning("Action has no date, skipping")
                    continue

                # convert time to pupa fuzzy time
                date = date.replace("T", " ")
                # TODO: if we update pupa to accept datetimes we can drop this line
                date = date.split()[0]

                d = action_desc.lower()
                committee = None

                reading = False
                attrs = self.categorizer.categorize(action_desc)
                action_type = attrs["classification"]

                if "first reading" in d:
                    reading = True

                if "second reading" in d or "reread second time" in d:
                    reading = True

                if "third reading" in d or "reread third time" in d:
                    action_type.append("reading-3")
                    reading = True

                if "adopted" in d and reading:
                    action_type.append("passage")

                if (
                    "referred" in d
                    and "committee on" in d
                    or "reassigned" in d
                    and "committee on" in d
                ):
                    committee = d.split("committee on")[-1].strip()

                a = bill.add_action(
                    chamber=action_chamber,
                    description=action_desc,
                    date=date,
                    classification=action_type,
                )
                if committee:
                    a.add_related_entity(committee, entity_type="organization")

            # subjects
            subjects = [s["entry"] for s in bill_json["latestVersion"]["subjects"]]
            for subject in subjects:
                subject = (
                    subject
                    if not subject.startswith("PENSIONS AND RETIREMENT BENEFITS")
                    else "PENSIONS AND RETIREMENT BENEFITS; Public Retirement System (INPRS)"
                )
                bill.add_subject(subject)

            # Abstract
            if bill_json["latestVersion"]["digest"]:
                bill.add_abstract(bill_json["latestVersion"]["digest"], note="Digest")

            # votes
            yield from self._process_votes(
                bill_json["all_rollcalls"],
                disp_bill_id,
                original_chamber,
                session,
            )

            for v in bill_json["versions"]:
                # note there are a number of links in the API response that won't work with just a browser, they need an api key
                # https://iga.in.gov/pdf-documents/123/2024/house/resolutions/HC0001/HC0001.01.INTR.pdf
                category = "resolutions" if "resolution" in bill_type else "bills"
                url = f"https://iga.in.gov/pdf-documents/{self.session_no}/{bill_json['year']}/{bill_json['originChamber']}/{category}/{v['billName']}/{v['printVersionName']}.pdf"
                bill.add_version_link(
                    v["stageVerbose"],
                    url,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

            self.deal_with_latest_version(
                bill_json["latestVersion"],
                bill,
                api_base_url,
            )

            yield bill
