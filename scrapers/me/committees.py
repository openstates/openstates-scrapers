import re

import xlrd
import lxml.html
from openstates.scrape import Scraper, Organization


class MECommitteeScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber in ["upper", None]:
            yield from self.scrape_senate_comm()
        if chamber in ["lower", None]:
            yield from self.scrape_reps_comm()
            yield from self.scrape_joint_comm()

    def scrape_reps_comm(self):
        # As of 1/27/15, the committee page has the wrong
        # session number (126th) at the top, but
        # has newly elected people, so we're rolling with it.

        url = "http://legislature.maine.gov/house/hsecoms.htm"
        page = self.get(url).text
        root = lxml.html.fromstring(page)

        count = 0

        for n in range(1, 12, 2):
            path = "string(//body/center[%s]/h1/a)" % (n)
            comm_name = root.xpath(path)
            committee = Organization(
                chamber="lower", name=comm_name, classification="committee"
            )
            count = count + 1

            path2 = "/html/body/ul[%s]/li/a" % (count)

            for el in root.xpath(path2):
                rep = el.text
                if rep.find("(") != -1:
                    mark = rep.find("(")
                    rep = rep[15:mark].strip()
                if "chair" in rep.lower():
                    role = "chair"
                    rep = re.sub(r"(?i)[\s,]*chair\s*$", "", rep).strip()
                else:
                    role = "member"
                committee.add_member(rep, role)
            committee.add_source(url)

            yield committee

    senate_committee_pattern = re.compile(r"^Senator (.*?) of .*?(, Chair)?$")

    def scrape_senate_comm(self):
        url = (
            "http://legislature.maine.gov/committee-information/"
            "standing-committees-of-the-senate"
        )
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        headings = doc.xpath("//p/strong")
        for heading in headings:
            committee = Organization(
                chamber="upper",
                name=heading.text.strip(":"),
                classification="committee",
            )
            committee.add_source(url)
            par = heading.getparent().getnext()
            while True:
                link = par.xpath("a")
                if len(link) == 0:
                    break
                res = self.senate_committee_pattern.search(link[0].text)
                name, chair = res.groups()
                committee.add_member(name, "chair" if chair is not None else "member")
                par = par.getnext()

            yield committee

    def scrape_joint_comm(self):
        fileurl = "http://legislature.maine.gov/house/commlist.xlsx"
        fname, resp = self.urlretrieve(fileurl)

        wb = xlrd.open_workbook(fname)
        sh = wb.sheet_by_index(0)

        # Special default dict.
        class Committees(dict):
            def __missing__(self, key):
                val = Organization(
                    chamber="legislature", name=key, classification="committee"
                )
                self[key] = val
                return val

        committees = Committees()

        for rownum in range(1, sh.nrows):

            comm_name = sh.cell(rownum, 0).value
            committee = committees[comm_name]

            ischair = sh.cell(rownum, 1).value
            role = "chair" if ischair else "member"
            first = sh.cell(rownum, 3).value
            middle = sh.cell(rownum, 4).value
            last = sh.cell(rownum, 5).value
            suffix = sh.cell(rownum, 6).value

            name = filter(None, [first, middle, last])
            name = " ".join(name)
            if suffix:
                name += ", " + suffix

            name = name.strip()
            committee.add_member(name, role)

        for _, committee in committees.items():
            committee.add_source(fileurl)
            yield committee
