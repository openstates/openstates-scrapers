import logging
import datetime
from openstates.scrape import Scraper, VoteEvent as Vote
from spatula import HtmlPage


# TODO: Develop method for ingesting how each individual lawmaker voted,
#  could be from scraping the House and Senate Journal PDFs at
#  https://www.ndlegis.gov/assembly/67-2021/regular/journals/journal-index.html
class VotePage(HtmlPage):
    # url of actual page to scrape
    source = "http://www.ndlegis.gov/rollcall/rollcall.htm"
    # TODO: Delete below source reassignment when/before
    #  new session vote data appears
    # url of web archived version of page with scrape-able past content
    #  to be used for testing scraper (until new session starts)
    source = f"http://web.archive.org/web/20221115164931/{source}"

    def process_page(self):
        # TODO: Write POST request / select each of the 5 date options
        #  to get content for the full week of votes.
        #  (Note: this will not be testable on the archived page)
        date_option = self.root.xpath(".//option[@selected='selected']")
        vote_date = date_option[0].get("value")
        date_obj = datetime.datetime.strptime(vote_date, "%m/%d/%Y")
        yield from self.process_votes("Senate", date_obj)
        yield from self.process_votes("House", date_obj)

    def process_votes(self, chamber, date_obj):
        votes_xpath = (
            f".//table[@summary='View {chamber} Roll Call']" "//tr[position()>1]"
        )
        vote_list = self.root.xpath(votes_xpath)

        chamber_dict = {"Senate": "upper", "House": "lower"}
        chamber_id = chamber_dict[chamber]

        for vote_item in vote_list:
            tds = vote_item.xpath("td")
            vote_parts = [x.text_content().strip() for x in tds]
            bill_id, time, status, passage = vote_parts[0:4]

            yes, no, exc, abst = [int(x) for x in vote_parts[4:8]]

            passed = yes > no

            vote = Vote(
                chamber=chamber_id,
                start_date=date_obj.strftime("%Y-%m-%d"),
                motion_text=f"Motion for {status} on {bill_id}.",
                result="pass" if passed else "fail",
                legislative_session=self.input["session"],
                # TODO: get all possible classification types, replace below
                classification="passage",
                bill=bill_id,
                bill_chamber="lower" if bill_id[0] == "H" else "upper",
            )

            links = vote_item.xpath("td//a")
            for link in links:
                url = link.get("href")
                vote.add_source(url)

            vote.set_count("yes", yes)
            vote.set_count("no", no)
            vote.set_count("excused", exc)
            vote.set_count("absent", abst)

            yield vote


class NDVoteScraper(Scraper):
    def scrape(self, session=None):
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        vote_page = VotePage({"session": session})
        yield from vote_page.do_scrape()
