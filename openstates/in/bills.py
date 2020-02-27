import re
import datetime
import os
from collections import OrderedDict

import scrapelib
import pytz

from pupa.scrape import Scraper, Bill, VoteEvent
from pupa.utils.generic import convert_pdf

from .apiclient import ApiClient


class INBillScraper(Scraper):
    jurisdiction = "in"

    _tz = pytz.timezone("US/Eastern")

    def _get_bill_id_components(self, bill_id):
        bill_prefix = "".join([c for c in bill_id if c.isalpha()])
        bill_number = "".join([c for c in bill_id if c.isdigit()]).lstrip("0")

        return (bill_prefix, bill_number)

    def _get_name(self, random_json):
        # got sick of doing this everywhere
        return " ".join([random_json["firstName"], random_json["lastName"]])

    def _get_bill_url(self, session, bill_id):
        bill_prefix, bill_number = self._get_bill_id_components(bill_id)

        url_template = "http://iga.in.gov/legislative/{}/{}/{}"

        try:
            url_segment = self._bill_prefix_map[bill_prefix]["url_segment"]
        except KeyError:
            raise AssertionError(
                "Unknown bill type {}, don't know how to " "make url.".format(bill_id)
            )

        return url_template.format(session, url_segment, bill_number)

    def _process_votes(self, rollcalls, bill_id, original_chamber, session, proxy):
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
            proxy_link = proxy["url"] + r["link"]

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

            motion = " ".join(lines[4].split()[:-2])
            try:
                yeas = int(lines[4].split()[-1])
                nays = int(lines[5].split()[-1])
                excused = int(lines[6].split()[-1])
                not_voting = int(lines[7].split()[-1])
            except ValueError:
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

    def deal_with_version(self, version, bill, bill_id, chamber, session, proxy):
        # documents
        docs = OrderedDict()
        docs["Committee Amendment"] = version["cmte_amendments"]
        docs["Floor Amendment"] = version["floor_amendments"]
        docs["Amendment"] = version["amendments"]
        docs["Fiscal Note"] = version["fiscal-notes"]
        docs["Committee Report"] = version["committee-reports"]

        # sometimes amendments appear in multiple places
        # cmte_amendment vs amendment
        # so we're only adding once but using the more
        # specific if it's available
        urls_seen = []
        for doc_type in docs:
            doc_list = docs[doc_type]
            for doc in doc_list:
                title = "{doc_type}: {name}".format(doc_type=doc_type, name=doc["name"])
                link = proxy["url"] + doc["link"]
                if link not in urls_seen:
                    urls_seen.append(link)
                    bill.add_document_link(
                        note=title, url=link, media_type="application/pdf"
                    )

        # version
        link = proxy["url"] + version["link"]
        name = version["stageVerbose"]
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

        # votes
        votes = version["rollcalls"]
        yield from self._process_votes(votes, bill_id, chamber, session, proxy)

    def scrape(self, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

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

        api_base_url = "https://api.iga.in.gov"
        proxy = {"url": "http://in-proxy.openstates.org"}

        # ah, indiana. it's really, really hard to find
        # pdfs in their web interface. Super easy with
        # the api, but a key needs to be passed
        # in the headers. To make these documents
        # viewable to the public and our scrapers,
        # sunlight's put up a proxy service at this link
        # using our api key for pdf document access.

        client = ApiClient(self)
        r = client.get("bills", session=session)
        all_pages = client.unpaginate(r)
        for b in all_pages:
            bill_id = b["billName"]
            for idx, char in enumerate(bill_id):
                try:
                    int(char)
                except ValueError:
                    continue
                disp_bill_id = bill_id[:idx] + " " + str(int(bill_id[idx:]))
                break

            bill_link = b["link"]
            api_source = api_base_url + bill_link
            try:
                bill_json = client.get("bill", session=session, bill_id=bill_id.lower())
            except scrapelib.HTTPError:
                self.logger.warning("Bill could not be accessed. Skipping.")
                continue

            title = bill_json["description"]
            if title == "NoneNone":
                title = None
            # sometimes description is blank
            # if that's the case, we can check to see if
            # the latest version has a short description
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
                bill.add_sponsorship(
                    classification="author",
                    name=self._get_name(s),
                    entity_type="person",
                    primary=True,
                )

            for s in bill_json["coauthors"]:
                bill.add_sponsorship(
                    classification="coauthor",
                    name=self._get_name(s),
                    entity_type="person",
                    primary=False,
                )

            for s in bill_json["sponsors"]:
                bill.add_sponsorship(
                    classification="sponsor",
                    name=self._get_name(s),
                    entity_type="person",
                    primary=True,
                )

            for s in bill_json["cosponsors"]:
                bill.add_sponsorship(
                    classification="cosponsor",
                    name=self._get_name(s),
                    entity_type="person",
                    primary=False,
                )

            # actions
            action_link = bill_json["actions"]["link"]
            api_source = api_base_url + action_link

            try:
                actions = client.get(
                    "bill_actions", session=session, bill_id=bill_id.lower()
                )
            except scrapelib.HTTPError:
                self.logger.warning("Could not find bill actions page")
                actions = {"items": []}

            for a in actions["items"]:
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

                action_type = []
                d = action_desc.lower()
                committee = None

                reading = False
                if "first reading" in d:
                    action_type.append("reading-1")
                    reading = True

                if "second reading" in d or "reread second time" in d:
                    action_type.append("reading-2")
                    reading = True

                if "third reading" in d or "reread third time" in d:
                    action_type.append("reading-3")
                    if "passed" in d:
                        action_type.append("passage")
                    if "failed" in d:
                        action_type.append("failure")
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
                    action_type.append("referral-committee")

                if "committee report" in d:
                    if "pass" in d:
                        action_type.append("committee-passage")
                    if "fail" in d:
                        action_type.append("committee-failure")

                if "amendment" in d and "without amendment" not in d:
                    if "pass" in d or "prevail" in d or "adopted" in d:
                        action_type.append("amendment-passage")
                    if "fail" or "out of order" in d:
                        action_type.append("amendment-failure")
                    if "withdraw" in d:
                        action_type.append("amendment-withdrawal")

                if "signed by the governor" in d:
                    action_type.append("executive-signature")

                if len(action_type) == 0:
                    # calling it other and moving on with a warning
                    self.logger.warning(
                        "Could not recognize an action in '{}'".format(action_desc)
                    )
                    action_type = None

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
                bill.add_subject(subject)

            # Abstract
            if bill_json["latestVersion"]["digest"]:
                bill.add_abstract(bill_json["latestVersion"]["digest"], note="Digest")

            # versions and votes
            for version in bill_json["versions"][::-1]:
                try:
                    version_json = client.get(
                        "bill_version",
                        session=session,
                        bill_id=version["billName"],
                        version_id=version["printVersionName"],
                    )
                except scrapelib.HTTPError:
                    self.logger.warning("Bill version does not seem to exist.")
                    continue

                yield from self.deal_with_version(
                    version_json, bill, bill_id, original_chamber, session, proxy
                )

            yield bill
