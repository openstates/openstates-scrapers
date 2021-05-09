import re
import datetime
from operator import itemgetter
from collections import defaultdict
import string
from openstates.scrape import Scraper, Bill, VoteEvent as Vote
from openstates.utils import convert_pdf
from .utils import parse_directory_listing, open_csv

import lxml.html


class SkipBill(Exception):
    pass


class CTBillScraper(Scraper):
    latest_only = True

    def add_vote(vote, voter):
        if vote == "Y":
            vote.yes(voter)
        elif vote == "N":
            vote.no(voter)
        else:
            vote.vote("other", voter)

    def scrape(self, chamber=None, session=None):
        print("Scraping the bill!")
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        self.bills = defaultdict(list)
        self._committee_names = {}
        self._introducers = defaultdict(set)
        self._subjects = defaultdict(list)
        self.scrape_committee_names()
        self.scrape_subjects()
        self.scrape_introducers("upper")
        self.scrape_introducers("lower")
        yield from self.scrape_bill_info(session, chambers)
        # for chamber in chambers:
        #     self.scrape_versions(chamber, session)
        self.scrape_bill_history()

        for bill in self.bills.values():
            yield bill[0]

    def scrape_bill_info(self, session, chambers):
        print("Scraping the bill info from FTP site")
        info_url = "ftp://ftp.cga.ct.gov/pub/data/bill_info.csv"
        data = self.get(info_url)
        page = open_csv(data)

        chamber_map = {"H": "lower", "S": "upper"}

        for row in page:
            if row["sess_year"] != session:
                continue
            bill_id = row["bill_num"]
            chamber = chamber_map[bill_id[0]]

            if chamber not in chambers:
                continue

            if re.match(r"^(S|H)J", bill_id):
                bill_type = "joint resolution"
            elif re.match(r"^(S|H)R", bill_id):
                bill_type = "resolution"
            else:
                bill_type = "bill"

            bill = Bill(
                identifier=bill_id,
                legislative_session=session,
                title=row["bill_title"],
                classification=bill_type,
                chamber=chamber,
            )
            bill.add_source(info_url)

            for introducer in self._introducers[bill_id]:
                introducer = string.capwords(
                    introducer.decode("utf-8").replace("Rep. ", "").replace("Sen. ", "")
                )
                if "Dist." in introducer:
                    introducer = " ".join(introducer.split()[:-2])
                bill.add_sponsorship(
                    name=introducer,
                    classification="primary",
                    primary=True,
                    entity_type="person",
                )

            try:
                for subject in self._subjects[bill_id]:
                    bill.subject.append(subject)

                self.bills[bill_id] = [bill, chamber]

                yield from self.scrape_bill_page(bill)
            except SkipBill:
                self.warning("no such bill: " + bill_id)
                pass

    def scrape_bill_page(self, bill):
        print("Scraping the bill page from web")
        # Removes leading zeroes in the bill number.
        bill_number = "".join(re.split("0+", bill.identifier, 1))

        url = (
            "https://www.cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill"
            "&bill_num=%s&which_year=%s" % (bill_number, bill.legislative_session)
        )

        page = self.get(url, verify=False).text
        if "not found in Database" in page:
            raise SkipBill()
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        bill.add_source(url)

        spon_type = "primary"
        if not bill.sponsorships:
            for sponsor in page.xpath('//h5[text()="Introduced by: "]/../text()'):
                sponsor = str(sponsor.strip())
                if sponsor:
                    sponsor = string.capwords(
                        sponsor.replace("Rep. ", "").replace("Sen. ", "")
                    )
                    if "Dist." in sponsor:
                        sponsor = " ".join(sponsor.split()[:-2])
                    bill.add_sponsorship(
                        name=sponsor,
                        classification=spon_type,
                        entity_type="person",
                        primary=spon_type == "primary",
                    )
                    # spon_type = 'cosponsor'

        for link in page.xpath("//a[contains(@href, '/FN/')]"):
            bill.add_document_link(link.text.strip(), link.attrib["href"])

        for link in page.xpath("//a[contains(@href, '/BA/')]"):
            bill.add_document_link(link.text.strip(), link.attrib["href"])

        for link in page.xpath(
            "//a[(contains(@href, '/pdf/') or contains(@href, '/PDF/')) and contains(@href, '/TOB/')]"
        ):
            bill.add_version_link(
                link.text.strip(), link.attrib["href"], media_type="application/pdf"
            )

        for link in page.xpath(
            "//a[(contains(@href, '/pdf/') or contains(@href, '/PDF/')) and contains(@href, '/VOTE/')]"
        ):
            # 2011 HJ 31 has a blank vote, others might too
            print(link.text)
            if link.text:
                pdf_link = link
                if pdf_link is not None:
                    yield from self.scrape_vote(
                        bill, pdf_link.text.strip(), link.attrib["href"]
                    )
        print("Finished scraping webpage")

    def scrape_vote(self, bill, name, url):
        if "VOTE/h" in url:
            vote_chamber = "lower"
        else:
            vote_chamber = "upper"

        (path, resp) = self.urlretrieve(url)
        pdflines = convert_pdf(path, "text")
        # os.remove(path)

        for line in pdflines.split(b"\n"):
            line = line.strip().decode()

            if line.startswith("Those voting Yea"):
                yes_count = re.match(r"[^\d]*(\d+)[^\d]*", line).group(1)

            if line.startswith("Those voting Nay"):
                no_count = re.match(r"[^\d]*(\d+)[^\d]*", line).group(1)

            if line.startswith("Those absent and not voting"):
                other_count = re.match(r"[^\d]*(\d+)[^\d]*", line).group(1)

            if line.startswith("Necessary for Passage"):
                need_count = re.match(r"[^\d]*(\d+)[^\d]*", line).group(1)

            if line.startswith("Taken on"):
                date = re.match(r".*Taken\s+on\s+(\d+/\s?\d+)", line).group(1)
                date = datetime.datetime.strptime(
                    date + " " + bill.legislative_session, "%m/%d %Y"
                ).date()

            if line.startswith("Y") or line.startswith("A") or line.startswith("N"):
                votes = re.match(
                    r"(Y|N|A)(\s+\w+)\s+(Y|N|A)(\s+\w+)\s+(Y|N|A)(\s+\w+)\s+(Y|N|A)(\s+\w+)",
                    line,
                )
                # Voter is match group 2,4,6,8
                # need to figure out edge cases in REGEX:
                # Morrin Bello
                # BERGER-GIRVALO
                # MCCARTHY VAHEY
                # SIMMONS, C.
                self.add_vote(votes.group(1), votes.group(2))
                self.add_vote(votes.group(3), votes.group(4))
                self.add_vote(votes.group(5), votes.group(6))

        # not sure about classification.
        vote = Vote(
            chamber=vote_chamber,
            start_date=date,
            motion_text=name,
            result="pass" if yes_count > need_count else "fail",
            classification="passage",
            bill=bill,
        )
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("other", other_count)
        vote.add_source(url)
        print("Finished scraping the votes")
        yield vote

    def scrape_bill_history(self):
        history_url = "ftp://ftp.cga.ct.gov/pub/data/bill_history.csv"
        page = self.get(history_url)
        page = open_csv(page)

        action_rows = defaultdict(list)

        for row in page:
            bill_id = row["bill_num"]

            if bill_id in self.bills:
                action_rows[bill_id].append(row)

        for (bill_id, actions) in action_rows.items():
            bill = self.bills[bill_id][0]

            actions.sort(key=itemgetter("act_date"))
            act_chamber = self.bills[bill_id][1]

            for row in actions:
                date = row["act_date"]
                date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date()

                action = row["act_desc"].strip()
                act_type = []

                match = re.search(r"COMM(ITTEE|\.) ON$", action)
                if match:
                    comm_code = row["qual1"]
                    comm_name = self._committee_names.get(comm_code, comm_code)
                    action = "%s %s" % (action, comm_name)
                    act_type.append("referral-committee")
                elif row["qual1"]:
                    if bill.legislative_session in row["qual1"]:
                        action += " (%s" % row["qual1"]
                        if row["qual2"]:
                            action += " %s)" % row["qual2"]
                    else:
                        action += " %s" % row["qual1"]

                match = re.search(r"REFERRED TO OLR, OFA (.*)", action)
                if match:
                    action = (
                        "REFERRED TO Office of Legislative Research"
                        " AND Office of Fiscal Analysis %s" % (match.group(1))
                    )

                if re.match(r"^ADOPTED, (HOUSE|SENATE)", action) or re.match(
                    r"^(HOUSE|SENATE) PASSED", action
                ):
                    act_type.append("passage")

                match = re.match(r"^Joint ((Un)?[Ff]avorable)", action)
                if match:
                    act_type.append("committee-passage-%s" % match.group(1).lower())

                if re.match(r"SIGNED BY GOVERNOR", action):
                    act_type.append("executive-signature")

                if re.match(r"PUBLIC ACT", action):
                    act_type.append("became-law")

                if re.match(r"^LINE ITEM VETOED", action):
                    act_type.append("executive-veto-line-item")

                if not act_type:
                    act_type = None

                if "TRANS.TO HOUSE" in action or action == "SENATE PASSED":
                    act_chamber = "lower"

                if "TRANSMITTED TO SENATE" in action or action == "HOUSE PASSED":
                    act_chamber = "upper"

                bill.add_action(
                    description=action,
                    date=date,
                    chamber=act_chamber,
                    classification=act_type,
                )

    def scrape_versions(self, chamber, session):
        chamber_letter = {"upper": "s", "lower": "h"}[chamber]
        versions_url = "ftp://ftp.cga.ct.gov/%s/tob/%s/pdf/" % (session, chamber_letter)

        page = self.get(versions_url).text
        files = parse_directory_listing(page)

        for f in files:
            match = re.match(r"^\d{4,4}([A-Z]+-\d{5,5})-(R\d\d)", f.filename)
            if not match:
                self.warning("bad version filename %s", f.filename)
                continue
            bill_id = match.group(1).replace("-", "")

            try:
                bill = self.bills[bill_id][0]
            except IndexError:
                continue

            url = versions_url + f.filename
            bill.add_version_link(
                media_type="application/pdf", url=url, note=match.group(2)
            )

    def scrape_subjects(self):
        info_url = "ftp://ftp.cga.ct.gov/pub/data/subject.csv"
        data = self.get(info_url)
        page = open_csv(data)

        for row in page:
            self._subjects[row["bill_num"]].append(row["subj_desc"])

    def scrape_committee_names(self):
        comm_url = "ftp://ftp.cga.ct.gov/pub/data/committee.csv"
        page = self.get(comm_url)
        page = open_csv(page)

        for row in page:
            comm_code = row["comm_code"].strip()
            comm_name = row["comm_name"].strip()
            comm_name = re.sub(r" Committee$", "", comm_name)
            self._committee_names[comm_code] = comm_name

    def scrape_introducers(self, chamber):
        chamber_letter = {"upper": "s", "lower": "h"}[chamber]
        url = "https://www.cga.ct.gov/asp/menu/%slist.asp" % chamber_letter

        page = self.get(url, verify=False).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'MemberBills')]"):
            name = link.xpath("../../td[2]/a/text()")[0].encode("utf-8").strip()
            # we encode the URL here because there are weird characters that
            # cause problems
            url = link.attrib["href"].encode("utf-8")
            self.scrape_introducer(name, url)

    def scrape_introducer(self, name, url):
        page = self.get(url, verify=False).text
        page = lxml.html.fromstring(page)

        for link in page.xpath("//a[contains(@href, 'billstatus')]"):
            bill_id = link.text.strip()
            self._introducers[bill_id].add(name)
