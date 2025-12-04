import re
import datetime
import collections
import unicodedata

from lxml import html
import scrapelib

from urllib import parse

from openstates.scrape import Scraper, Bill, VoteEvent as Vote
from .actions import Categorizer


class OKBillScraper(Scraper):
    bill_types = ["B", "JR", "CR", "R"]
    subject_map = collections.defaultdict(list)

    categorizer = Categorizer()

    # Can be found in the session select dropdown at
    # http://www.oklegislature.gov/TextOfMeasures.aspx
    meta_session_id = {
        "2011-2012": "1200",
        "2012SS1": "121X",
        "2013SS1": "131X",
        "2013-2014": "1400",
        "2015-2016": "1600",
        "2017SS1": "171X",
        "2017SS2": "172X",
        "2017-2018": "1800",
        "2019-2020": "1900",
        "2020": "2000",
        "2020SS1": "201X",
        "2021": "2100",
        "2021SS1": "211X",
        "2022": "2200",
        "2022SS2": "222X",
        "2022SS3": "223X",
        "2023": "2300",
        "2023S1": "231X",
        "2023S2": "232X",
        "2024": "2400",
        "2024S3": "243X",
        "2024S4": "244X",
        "2025": "2500",
        "2026": "2600",
    }

    def scrape(self, chamber=None, session=None, only_bills=None):
        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session, only_bills)

    def scrape_chamber(self, chamber, session, only_bills):
        # start by building subject map
        self.scrape_subjects(chamber, session)

        url = "https://webapps.oklegislature.gov/WebApplication3/WebForm1.aspx"
        form_page = html.fromstring(self.get(url).text)

        if chamber == "upper":
            chamber_letter = "S"
        else:
            chamber_letter = "H"

        session_id = self.meta_session_id[session]
        self.debug("Using session slug `{}`".format(session_id))
        values = {
            "cbxSessionId": session_id,
            "cbxActiveStatus": "All",
            "RadioButtonList1": "On Any day",
            "Button1": "Retrieve",
        }

        lbxTypes = []
        for bill_type in self.bill_types:
            lbxTypes.append(chamber_letter + bill_type)
        values["lbxTypes"] = lbxTypes

        for hidden in form_page.xpath("//input[@type='hidden']"):
            values[hidden.attrib["name"]] = hidden.attrib["value"]

        page = self.post(url, data=values).text
        page = html.fromstring(page)
        page.make_links_absolute(url)

        bill_nums = []
        for link in page.xpath("//a[contains(@href, 'BillInfo')]"):
            bill_id = link.text.strip()
            bill_num = int(re.findall(r"\d+", bill_id)[0])
            if bill_num >= 9900:
                self.warning("skipping likely bad bill %s" % bill_id)
                continue
            if only_bills is not None and bill_id not in only_bills:
                self.warning("skipping bill we are not interested in %s" % bill_id)
                continue
            bill_nums.append(bill_num)
            yield from self.scrape_bill(chamber, session, bill_id, link.attrib["href"])

    def scrape_bill(self, chamber, session, bill_id, url):
        try:
            page = html.fromstring(self.get(url).text)
        except scrapelib.HTTPError as e:
            self.warning("error (%s) fetching %s, skipping" % (e, url))
            return

        title = page.xpath(
            "string(//span[contains(@id, 'PlaceHolder1_txtST')])"
        ).strip()
        if not title:
            self.warning("blank bill on %s - skipping", url)
            return

        if "JR" in bill_id:
            bill_type = ["joint resolution"]
        elif "CR" in bill_id:
            bill_type = ["concurrent resolution"]
        elif "R" in bill_id:
            bill_type = ["resolution"]
        else:
            bill_type = ["bill"]

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )
        bill.add_source(url)
        bill.subject = self.subject_map[bill_id]

        for link in page.xpath("//a[contains(@id, 'Auth')]"):
            name = link.xpath("string()").strip()
            if "author not found" in name.lower():
                continue

            if ":" in name:
                raise Exception(name)
            if "otherAuth" in link.attrib["id"]:
                bill.add_sponsorship(
                    name,
                    classification="cosponsor",
                    entity_type="person",
                    primary=False,
                )
            else:
                bill.add_sponsorship(
                    name, classification="primary", entity_type="person", primary=True
                )

        act_table = page.xpath("//table[contains(@id, 'Actions')]")[0]
        for tr in act_table.xpath("tr")[2:]:
            action = tr.xpath("string(td[1])").strip()
            if not action or action == "None":
                continue

            date = tr.xpath("string(td[3])").strip()
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            actor = tr.xpath("string(td[4])").strip()
            if actor == "H":
                actor = "lower"
            elif actor == "S":
                actor = "upper"

            attrs = self.categorizer.categorize(action)
            related_entities = []
            for item in attrs["committees"]:
                related_entities.append({"type": "committee", "name": item})
            for item in attrs["legislators"]:
                related_entities.append({"type": "legislator", "name": item})
            bill.add_action(
                description=action,
                date=date.strftime("%Y-%m-%d"),
                chamber=actor,
                classification=attrs["classification"],
                related_entities=related_entities,
            )

        version_table = page.xpath("//table[contains(@id, 'Versions')]")[0]
        # Keep track of already seen versions to prevent processing duplicates.
        version_urls = []
        for link in version_table.xpath(".//a[contains(@href, '.PDF')]"):
            version_url = link.attrib["href"]
            if version_url in version_urls:
                self.warning("Skipping duplicate version URL.")
                continue
            else:
                version_urls.append(version_url)

            if link.text is None:
                self.warning("Skipping unnamed version.")
                continue

            name = link.text.strip()

            if re.search("COMMITTEE REPORTS|SCHEDULED CCR", version_url, re.IGNORECASE):
                bill.add_document_link(
                    note=name, url=version_url, media_type="application/pdf"
                )
                continue

            bill.add_version_link(
                note=name, url=version_url, media_type="application/pdf"
            )

        self.scrape_amendments(bill, page)

        for link in page.xpath(".//a[contains(@href, '_VOTES')]"):
            if "HT_" not in link.attrib["href"]:
                yield from self.scrape_votes(bill, self.urlescape(link.attrib["href"]))

        # # If the bill has no actions and no versions, it's a bogus bill on
        # # their website, which appears to happen occasionally. Skip.
        has_no_title = bill.title == "Short Title Not Found."
        if has_no_title:
            # If there's no title, this is an empty page. Skip!
            return

        else:
            # Otherwise, save the bills.
            yield bill

    def scrape_amendments(self, bill, page):
        amd_xpath = (
            '//table[@id="ctl00_ContentPlaceHolder1_'
            'TabContainer1_TabPanel2_tblAmendments"]//a[contains(@href,".PDF")]'
        )

        for link in page.xpath(amd_xpath):
            version_url = link.xpath("@href")[0]
            version_name = link.xpath("string(.)").strip()
            bill.add_version_link(
                version_name, version_url, media_type="application/pdf"
            )

    def scrape_votes(self, bill, url):
        html_content = unicodedata.normalize(
            "NFKD", self.get(url).text.replace("\r\n", " ")
        )
        page = html.fromstring(html_content)

        seen_rcs = set()
        motions = {}
        headers_xpath = page.xpath('//p[contains(., "Top_of_Page")]')

        for motion in page.xpath(
            '//a[contains(@href, "#")][not(contains(@href,"Top_of_Page"))]'
        ):
            motion_text = motion.xpath("string()").strip("#").replace("_", " ")
            motion_link = motion.xpath("@href")[0].strip("#").replace("RCS", "")

            if "committee" in motion_text.lower() and "RCS" not in motion_text:
                motion_index = (
                    motion_link.lstrip("0").zfill(1)
                    if motion_link.isdigit()
                    else motion_link.split("_")[1].lstrip("0").zfill(1)
                )
                do_pass_motion = motion_link.split("_")
                do_index = do_pass_motion.index("DO") if "DO" in do_pass_motion else -1
                passed_index = (
                    do_pass_motion.index("PASSED")
                    if "PASSED" in do_pass_motion
                    else do_pass_motion.index("FAILED")
                    if "FAILED" in do_pass_motion
                    else -1
                )
                do_pass_motion = (
                    " ".join(do_pass_motion[do_index:passed_index]).strip().title()
                )
                motion_text = do_pass_motion or "Do Pass"
            else:
                motion_index = motion_link.lstrip("0").zfill(1)
                if "OKLAHOMA" in motion_text:
                    motion_text = "Committee Vote"
                else:
                    motion_text = motion_text.split("(")[0].strip().title()

            motions[motion_index] = motion_text

        for header in headers_xpath:
            bad_vote = False
            # Each chamber has the motion name on a different line of the file
            if "house" in url.lower():
                chamber = "lower"
            else:
                chamber = "upper"

            rcs_xpath = header.xpath(
                "following-sibling::p[contains(., '***')][1]/preceding-sibling::p[contains(., 'RCS#')][1]"
            )

            if rcs_xpath:
                rcs_p = rcs_xpath[0]
                rcs_line = rcs_p.xpath("string()").replace("\xa0", " ")
                rcs = re.search(r"RCS#\s+(\d+)", rcs_line).group(1)
                if rcs in seen_rcs:
                    continue
                else:
                    seen_rcs.add(rcs)
            else:
                continue
            committees = [
                "Administrative Rules",
                "Aeronautics And Transportation",
                "Aeronautics & Transportation",
                "Agriculture And Rural Affairs",
                "Agriculture & Rural Affairs",
                "Appropriations",
                "Business and Commerce",
                "Business & Commerce",
                "Education",
                "Energy And Telecommunications",
                "Energy & Telecommunications",
                "Finance",
                "General Government",
                "Health And Human Services",
                "Health & Human Services",
                "Judiciary",
                "Public Safety",
                "Retirement And Insurance",
                "Retirement & Insurance",
                "Rules",
                "Tourism And Wildlife",
                "Tourism & Wildlife",
                "Veterans And Military Affairs",
                "Veterans & Military Affairs",
                "Committee",
                "Subcommittee",
            ]

            motion_text = motions.get(rcs, "Committee Vote")
            committee_motion = ""

            if "Do Pass" in motion_text or "Committee" in motion_text:
                for line in header.xpath("following-sibling::p"):
                    line_text = (
                        line.xpath("string()").replace("  ", " ").title().strip()
                    )
                    if "*****" in line_text:
                        break
                    if not committee_motion:
                        filter_motion = [
                            committee
                            for committee in committees
                            if committee in line_text
                            and "Motion By Senator" not in line_text
                        ]
                        if len(filter_motion) > 0:
                            committee_motion = line_text
                        continue

                    if "Motion By Senator" in line_text:
                        committee_motion += ": " + line_text
                        break

                    if "Do Pass" in line_text and (
                        "Passed" in line_text or "Failed" in line_text
                    ):
                        do_pass_motion = (
                            motion_text
                            if "Do Pass" in motion_text
                            else line_text.replace("Passed", "")
                            .replace("Failed", "")
                            .replace("Recommendation:", "")
                            .replace("Strike The T", "Strike The Title")
                            .replace("Strike The E", "Strike The Enacting Clause")
                            .strip()
                        )
                        committee_motion += ": " + do_pass_motion
                        break

            motion = committee_motion or motion_text

            if not motion:
                self.warning("Motion text not found")
                continue

            passed = None

            date_line = rcs_p.getnext().xpath("string()")
            date = re.search(r"\d+/\d+/\d+", date_line)
            if not date:
                continue
            date = date.group(0)
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            vtype = None
            counts = collections.defaultdict(int)
            votes = collections.defaultdict(list)

            seen_yes = False

            for sib in header.xpath("following-sibling::p"):
                line = sib.xpath("string()").strip()
                if "*****" in line or "motion by" in line:
                    break
                regex = (
                    r"(YEAS|AYES|NAYS|EXCUSED|VACANT|CONSTITUTIONAL "
                    r"PRIVILEGE|NOT VOTING|N/V)\s*:\s*(\d+)(.*)"
                )
                match = re.match(regex, line)
                if match:
                    if (match.group(1) in ["YEAS", "AYES"]) and "RCS#" not in line:
                        vtype = "yes"
                        seen_yes = True
                    elif match.group(1) == "NAYS" and seen_yes:
                        vtype = "no"
                    elif match.group(1) == "EXCUSED" and seen_yes:
                        vtype = "excused"
                    elif match.group(1) in ["NOT VOTING", "N/V"] and seen_yes:
                        vtype = "not voting"
                    elif match.group(1) == "VACANT":
                        continue  # skip these
                    elif seen_yes:
                        vtype = "other"
                    if seen_yes and match.group(3).strip():
                        self.warning("Bad vote format, skipping.")
                        bad_vote = True
                    counts[vtype] += int(match.group(2))
                elif seen_yes:
                    for name in line.split("   "):
                        if not name:
                            continue
                        if "HOUSE" in name or "SENATE " in name:
                            continue
                        votes[vtype].append(name.strip())

            if bad_vote:
                continue

            if passed is None:
                passed = counts["yes"] > counts["no"]

            vote = Vote(
                chamber=chamber,
                start_date=date.strftime("%Y-%m-%d"),
                motion_text=motion,
                result="pass" if passed else "fail",
                bill=bill,
                classification="passage",
            )
            vote.set_count("yes", counts["yes"])
            for name in votes["yes"]:
                vote.yes(name)
            vote.set_count("no", counts["no"])
            for name in votes["no"]:
                if ":" in name:
                    raise Exception(name)
                vote.no(name)
            if "excused" in counts:
                vote.set_count("excused", counts["excused"])
                for name in votes["excused"]:
                    vote.vote("excused", name)
            if "not voting" in counts:
                vote.set_count("not voting", counts["not voting"])
                for name in votes["not voting"]:
                    vote.vote("not voting", name)
            vote.set_count("other", counts["other"])
            for name in votes["other"]:
                vote.vote("other", name)
            vote.dedupe_key = url + "#" + rcs

            vote.add_source(url)

            yield vote

    def scrape_subjects(self, chamber, session):
        form_url = "https://webapps.oklegislature.gov/WebApplication3/WebForm1.aspx"
        form_html = self.get(form_url).text
        fdoc = html.fromstring(form_html)

        # bill types
        letter = "H" if chamber == "lower" else "S"
        types = [letter + t for t in self.bill_types]

        session_id = self.meta_session_id[session]

        # do a request per subject
        for subj in fdoc.xpath('//select[@name="lbxSubjects"]/option/@value'):
            # these forms require us to get hidden session keys
            values = {
                "cbxInclude": "All",
                "Button1": "Retrieve",
                "RadioButtonList1": "On Any Day",
                "cbxSessionID": session_id,
                "lbxSubjects": subj,
                "lbxTypes": types,
            }
            for hidden in fdoc.xpath("//input[@type='hidden']"):
                values[hidden.attrib["name"]] = hidden.attrib["value"]
            # values = urllib.urlencode(values, doseq=True)
            page_data = self.post(form_url, data=values).text
            page_doc = html.fromstring(page_data)

            # all links after first are bill_ids
            for bill_id in page_doc.xpath("//a/text()")[1:]:
                self.subject_map[bill_id].append(subj)

    def urlescape(self, url):
        scheme, netloc, path, qs, anchor = parse.urlsplit(url)
        path = parse.quote(path, "/%")
        qs = parse.quote_plus(qs, ":&=")
        return parse.urlunsplit((scheme, netloc, path, qs, anchor))
