import re
import datetime
import requests
import feedparser

import lxml.html
from scrapelib import HTTPError
from openstates.scrape import Scraper, VoteEvent


class KSVoteScraper(Scraper):
    special_slugs = {"2020S1": "li_2020s", "2021S1": "li_2021s"}

    def scrape(self, session=None):
        yield from self.scrape_bill_list(session)

    def scrape_bill_list(self, session):
        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )
        if meta["classification"] == "special":
            list_slug = self.special_slugs[session]
        else:
            list_slug = "li"

        list_url = f"https://kslegislature.org/{list_slug}/data/feeds/rss/bill_info.xml"
        xml = self.get(list_url).content
        feed = feedparser.parse(xml)
        for item in feed.entries:
            bill_re = re.compile(r"(?P<prefix>\D+)(?P<number>\d+)")
            bill_data = bill_re.search(item.title).groupdict()
            bill_id = f'{bill_data["prefix"]} {bill_data["number"]}'
            yield from self.scrape_vote_from_bill(session, bill_id, item.guid)

    def scrape_vote_from_bill(self, session, bill, url):
        try:
            vote_response = self.get(url, retry_on_404=True)
        except HTTPError as e:
            # 500 error on HCR 5011 for some reason
            # temporarily swallow this exception to allow scrape to finish
            if bill == "HCR 5011":
                self.logger.warning(
                    f"Swallowing HTTPError for {bill} as a temporary fix: {e}"
                )
                return
            else:
                raise e
        doc = lxml.html.fromstring(vote_response.text)
        doc.make_links_absolute(url)
        all_links = doc.xpath(
            "//table[@class='bottom']/tbody[@class='tab-content-sub']/tr/td/a/@href"
        )
        vote_members_urls = []
        for i in all_links:
            if "vote_view" in i:
                vote_members_urls.append(str(i))
        if len(vote_members_urls) > 0:
            for link in vote_members_urls:
                yield from self.parse_vote(bill, link, session)

    def parse_vote(self, bill, link, session):
        # Server sometimes sends proper error headers,
        # sometimes not
        try:
            self.info("Get {}".format(link))
            text = requests.get(link).text
        except requests.exceptions.HTTPError as err:
            self.warning("{} fetching vote {}, skipping".format(err, link))
            return

        if "Varnish cache server" in text:
            self.warning(
                "Scrape rate is too high, try re-scraping with "
                "The --rpm set to a lower number"
            )
            return

        if "Page Not Found" in text or "Page Unavailable" in text:
            self.warning("missing vote, skipping")
            return
        member_doc = lxml.html.fromstring(text)
        motion = member_doc.xpath("//div[@id='main_content']/h4/text()")
        chamber_date_line = "".join(
            member_doc.xpath("//div[@id='main_content']/h3[1]//text()")
        )
        chamber_date_line_words = chamber_date_line.split()
        vote_chamber = chamber_date_line_words[0]
        vote_date = datetime.datetime.strptime(chamber_date_line_words[-1], "%m/%d/%Y")
        vote_status = " ".join(chamber_date_line_words[2:-2])
        opinions = member_doc.xpath(
            "//div[@id='main_content']/h3[position() > 1]/text()"
        )
        if len(opinions) > 0:
            vote_status = vote_status if vote_status.strip() else motion[0]
            vote_chamber = "upper" if vote_chamber == "Senate" else "lower"

            for i in opinions:
                try:
                    count = int(i[i.find("(") + 1 : i.find(")")])
                except ValueError:
                    # This is likely not a vote-count text chunk
                    # It's probably '`On roll call the vote was:`
                    pass
                else:
                    if "yea" in i.lower():
                        yes_count = count
                    elif "nay" in i.lower():
                        no_count = count
                    elif "present" in i.lower():
                        p_count = count
                    elif "absent" in i.lower():
                        a_count = count

            vote = VoteEvent(
                bill=bill,
                start_date=vote_date.strftime("%Y-%m-%d"),
                chamber=vote_chamber,
                motion_text=vote_status,
                legislative_session=session,
                result="pass" if yes_count > no_count else "fail",
                classification="passage",
            )
            vote.dedupe_key = link

            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("abstain", p_count)
            vote.set_count("absent", a_count)

            vote.add_source(link)

            a_links = member_doc.xpath("//div[@id='main_content']/a/text()")
            for i in range(1, len(a_links)):
                if i <= yes_count:
                    vote.vote("yes", re.sub(",", "", a_links[i]).split()[0])
                elif no_count != 0 and i > yes_count and i <= yes_count + no_count:
                    vote.vote("no", re.sub(",", "", a_links[i]).split()[0])
                else:
                    vote.vote("other", re.sub(",", "", a_links[i]).split()[0])
            yield vote
        else:
            self.warning("No Votes for: %s", link)
