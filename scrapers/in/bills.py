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

    def _process_votes(self, rollcalls, bill_id, original_chamber, session, client):
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
            # each value in rollcalls is an API metadata object describing the rollcall:
            # it does not include the PDF link explicitly (this can be requested from the "link" url)
            # but you can add ?format=pdf to the end of the "link" url to synthesize it
            # {
            # 	"target": "HB1001.03.COMH",
            # 	"chamber": {
            # 		"link": "/2024/chambers/house",
            # 		"name": "House"
            # 	},
            # 	"rollcall_number": "26",
            # 	"results": {
            # 		"yea": 80,
            # 		"nay": 17
            # 	},
            # 	"link": "/2024/rollcalls/{ID_GOES_HERE}}",
            # 	"type": "BILL"
            # }
            # however the PDF url does not return the PDF content immediately
            # it returns a 302 redirect to the actual PDF url
            # AND the actual PDF url is sensitive to the incoming User Agent header
            vote_url = client.identify_redirect_url(r["link"] + "?format=pdf")
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0"
                }
                path, ret_response = self.urlretrieve(vote_url, headers=headers)
            except scrapelib.HTTPError:
                self.logger.warning(
                    "HTTP error fetching vote URL, skipping vote {}".format(vote_url)
                )
                continue

            # Looks like a missing PDF file ends up being displayed as "404" content in HTML
            # instead of server returning a proper 404
            # so sanity check to see if content appears to be HTML instead of PDF
            if ret_response.headers["Content-Type"] != "application/pdf":
                self.logger.warning(
                    f"Got unexpected response type {ret_response.headers.get('Content-Type')},"
                    f" skipping {vote_url}"
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

            # Historically we've counted yeas/nays/excused/NV from parsing the PDF
            # but now the API response provides yea and nay counts
            # let's prefer those counts and log if a difference is found
            api_yea = int(r["results"]["yea"])
            api_nay = int(r["results"]["nay"])
            if yeas != api_yea:
                self.warning(
                    f"API yea count {api_yea} does not match PDF parse {yeas} "
                    f"at API {r['link']}, PDF {vote_url}"
                )
                yeas = api_yea
            if nays != api_nay:
                self.warning(
                    f"API nay count {api_nay} does not match PDF parse {nays} "
                    f"at API {r['link']}, PDF {vote_url}"
                )
                nays = api_nay
            vote.set_count("yes", yeas)
            vote.set_count("no", nays)
            vote.set_count("excused", excused)
            vote.set_count("not voting", not_voting)
            vote.add_source(vote_url)

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
                # vehicle bill
                if not bill_json:
                    self.logger.warning("Vehicle Bill: {}".format(bill_id))
                    continue
            except scrapelib.HTTPError:
                self.logger.warning("Bill could not be accessed. Skipping.")
                continue

            title = bill_json["description"]
            # Check if the title is "NoneNone" (indicating a placeholder) and set it to None
            if "NoneNone" in title:
                title = None
            # If the title is still empty or None, try to get the short description from the latest version
            if not title:
                title = bill_json["latestVersion"].get("shortDescription")
            # If the title is still not available, use the bill ID and log a warning
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
            bill.add_source(api_source, note="API details")

            # sponsors
            for category in ["authors", "coauthors", "sponsors", "cosponsors"]:
                for sponsor in bill_json.get(category, []):
                    self._add_sponsor_if_not_blank(
                        bill, sponsor, classification=category[:-1]
                    )

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

            committee_name_match_regex = r"committee on (.*?)( pursuant to|$)"
            for action in actions:
                action_desc = action["description"]

                # Determine action chamber
                if "governor" in action_desc.lower():
                    action_chamber = "executive"
                elif action["chamber"]["name"].lower() == "house":
                    action_chamber = "lower"
                else:
                    action_chamber = "upper"

                # Process action date
                date = action.get("date")
                if not date:
                    self.logger.warning("Action has no date, skipping")
                    continue

                # Convert date to pupa fuzzy time format
                date = date.replace("T", " ").split()[0]  # Extract date part only

                action_desc_lower = action_desc.lower()
                committee = None
                reading = False
                action_type = self.categorizer.categorize(action_desc)["classification"]

                # Identify reading actions
                if any(
                    phase in action_desc_lower
                    for phase in [
                        "first reading",
                        "second reading",
                        "third reading",
                        "reread second time",
                        "reread third time",
                    ]
                ):
                    reading = True
                    if (
                        "third reading" in action_desc_lower
                        or "reread third time" in action_desc_lower
                    ):
                        action_type.append("reading-3")

                # Mark passage if adopted during reading
                if "adopted" in action_desc_lower and reading:
                    action_type.append("passage")

                # Identify related committee
                committee_matches = re.search(
                    committee_name_match_regex, action_desc, re.IGNORECASE
                )
                if committee_matches:
                    committee = committee_matches[1].strip()

                # Add action to bill
                action_instance = bill.add_action(
                    chamber=action_chamber,
                    description=action_desc,
                    date=date,
                    classification=action_type,
                )

                # Add committee as related entity if present
                if committee:
                    action_instance.add_related_entity(
                        committee, entity_type="organization"
                    )

            # Extract subjects from the latest version of the bill
            latest_subjects = bill_json["latestVersion"]["subjects"]
            for subject_entry in latest_subjects:
                subject = subject_entry["entry"]
                if subject.startswith("PENSIONS AND RETIREMENT BENEFITS"):
                    subject = "PENSIONS AND RETIREMENT BENEFITS; Public Retirement System (INPRS)"
                # Add the processed subject to the bill
                bill.add_subject(subject)

            # Abstract
            digest = bill_json["latestVersion"]["digest"]
            if digest:
                bill.add_abstract(digest, note="Digest")

            # votes
            yield from self._process_votes(
                bill_json["all_rollcalls"],
                disp_bill_id,
                original_chamber,
                session,
                client,
            )

            for v in bill_json["versions"]:
                # https://iga.in.gov/pdf-documents/123/2024/house/resolutions/HC0001/HC0001.01.INTR.pdf
                category = "resolutions" if "resolution" in bill_type else "bills"
                url = (
                    f"https://iga.in.gov/pdf-documents/{self.session_no}/"
                    f"{bill_json['year']}/{bill_json['originChamber']}/"
                    f"{category}/{v['billName']}/{v['printVersionName']}.pdf"
                )
                # PROXY URL
                # url = urljoin(PROXY_BASE_URL, v['link'])
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
