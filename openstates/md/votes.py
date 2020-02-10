import re
import datetime
from collections import defaultdict
from openstates.utils import LXMLMixin
from openstates.utils.votes import check_counts
from pupa.scrape import Scraper, VoteEvent
from pupa.utils import convert_pdf


class MDVoteScraper(Scraper, LXMLMixin):
    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber_name = "senate" if chamber == "upper" else "house"
        url = "http://mgaleg.maryland.gov/mgawebsite/FloorActions/Index/" + chamber_name
        doc = self.lxmlize(url)
        links = doc.xpath("//table[1]/tbody/tr/td[3]/a/@href")

        # keep upping this number until we see them paginate
        if len(links) > 25:
            raise Exception("check for pagination")

        seen_urls = set()

        for link in links:
            doc = self.lxmlize(link)

            for vote_url in doc.xpath('//a[contains(@href, "/votes/")]/@href'):
                if vote_url not in seen_urls:
                    v = self.scrape_vote(vote_url, session)
                    if v:
                        yield v
                    seen_urls.add(vote_url)

    def scrape_vote(self, url, session):
        fname, _ = self.urlretrieve(url)
        text = convert_pdf(fname, type="text").decode()
        lines = text.splitlines()

        chamber = "upper" if "senate" in url else "lower"
        if "Maryland" not in text:
            self.warning(f"empty vote from {url}")
            return
        date = re.findall(r"Legislative Date: (\w+ \d+, \d{4})", text)[0]

        section = "preamble"
        motion = None
        bill_id = None
        how = None
        voters = defaultdict(list)

        for line in lines:
            if section == "preamble":
                possible_bill_id = re.findall(r"([HS]\w+ \d+)", line)
                if possible_bill_id:
                    bill_id = possible_bill_id[0]
                # need to add other motion types -- scraper will fail if we get
                # a bill_id but no motion, helping us identify these
                possible_motion = re.findall(
                    "notwithstanding the objections|On Third Reading|ON 2ND RDG|Decision of the Chair",
                    line,
                    re.I,
                )
                if possible_motion:
                    motion = possible_motion[0]
                    if motion == "notwithstanding the objections":
                        motion = "Shall the bill pass notwithstanding the objections of the Executive?"
                counts = re.findall(
                    r"(\d+) Yeas\s+(\d+) Nays\s+(\d+) Not Voting\s+(\d+) Excused\s+(\d+) Absent",
                    line,
                )
                if counts:
                    yes_count, no_count, nv_count, excused_count, absent_count = counts[
                        0
                    ]
                    yes_count = int(yes_count)
                    no_count = int(no_count)
                    nv_count = int(nv_count)
                    excused_count = int(excused_count)
                    absent_count = int(absent_count)
                    section = "votes"
            elif section == "votes":
                if line.startswith("Voting Yea"):
                    how = "yes"
                elif line.startswith("Voting Nay"):
                    how = "no"
                elif line.startswith("Not Voting"):
                    how = "not voting"
                elif line.startswith("Excused from Voting"):
                    how = "excused"
                elif line.startswith("Excused (Absent)"):
                    how = "absent"
                elif how:
                    names = re.split(r"\s{2,}", line)
                    voters[how].extend(names)

        if not bill_id and not motion:
            return
        elif bill_id and not motion:
            print(
                f"incomplete scrape of MD vote bill_id={bill_id} motion={motion} "
                "likely need to expand motion regex"
            )
            raise ValueError()
        elif motion and not bill_id:
            self.warning(f"got {motion} but no bill_id, not registering as a vote")
            return

        # bleh - result not indicated anywhere
        result = "pass" if yes_count > no_count else "fail"
        bill_chamber = "upper" if bill_id.startswith("S") else "lower"
        date = datetime.datetime.strptime(date, "%b %d, %Y").strftime("%Y-%m-%d")
        vote = VoteEvent(
            chamber=chamber,
            start_date=date,
            result=result,
            classification="passage",
            motion_text=motion,
            legislative_session=session,
            bill=bill_id,
            bill_chamber=bill_chamber,
        )
        # URL includes sequence ID, will be unique
        vote.pupa_id = url
        vote.add_source(url)
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("not voting", nv_count)
        vote.set_count("excused", excused_count)
        vote.set_count("absent", absent_count)
        for how, names in voters.items():
            for name in names:
                if (
                    name.strip()
                    and "COPY" not in name
                    and "Indicates Vote Change" not in name
                ):
                    vote.vote(how, name)
        check_counts(vote, raise_error=True)
        return vote
