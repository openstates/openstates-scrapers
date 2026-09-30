import concurrent.futures
import datetime
import re

import lxml.html

from openstates.scrape import Scraper, VoteEvent


class KSVoteScraper(Scraper):
    BASE_URL = "https://www.kslegislature.gov"

    # Number of vote detail pages to fetch concurrently. The old scraper
    # fetched every ~100 KB vote page one-at-a-time, which meant a full
    # biennium took well over a day to complete. Fetching several pages in
    # parallel dramatically cuts the wall-clock time without changing what
    # gets parsed or the order in which votes are emitted.
    VOTE_FETCH_WORKERS = 12

    def scrape(self, session=None):
        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )

        # Kansas' redesigned site stores votes under biennium-specific
        # URLs such as:
        #   /b2025_26/votes/
        #   /b2023_24/votes/
        #
        # Convert the OpenStates session identifier (2025-2026)
        # into the site biennium format (b2025_26).
        years = meta["identifier"].split("-")
        biennium = f"b{years[0]}_{years[1][-2:]}"

        page = 1

        while True:
            # Vote listings are loaded via the HTMX fragment endpoint.
            # Paginate until no vote rows are returned.
            list_url = (
                f"{self.BASE_URL}/{biennium}/votes/fragment/"
                f"?page={page}&per_page=100"
            )

            try:
                response = self.get(list_url)
            except Exception as e:
                self.warning(f"Failed to fetch vote listing page {page}: {e}")
                break

            doc = lxml.html.fromstring(response.text)

            vote_rows = doc.xpath("//tr[@data-href]")

            if not vote_rows:
                break

            # Collect all (bill, vote_url) pairs on this listing page first so
            # the individual vote detail pages can be downloaded concurrently.
            # The listing order is preserved below so the emitted output is
            # identical to the previous sequential implementation.
            page_votes = []
            for row in vote_rows:
                bill = row.xpath(".//td[@data-label='Measure']//a/text()")
                bill = bill[0].strip() if bill else None

                vote_url = row.attrib["data-href"]

                if not vote_url.startswith("http"):
                    vote_url = f"{self.BASE_URL}{vote_url}"

                page_votes.append((bill, vote_url))

            # Fetch the vote detail pages in parallel. Fetching (network I/O)
            # is the slow part; parsing stays on the main thread so the scrape
            # generator continues to yield in the original listing order.
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.VOTE_FETCH_WORKERS
            ) as pool:
                fetched = list(
                    pool.map(
                        lambda bv: (bv[0], bv[1], self._fetch_vote(bv[1])),
                        page_votes,
                    )
                )

            for bill, vote_url, text in fetched:
                yield from self.parse_vote(
                    bill,
                    vote_url,
                    session,
                    text,
                )

            page += 1

    def _fetch_vote(self, link):
        # Download a single vote detail page. Returns the response text, or
        # None if the page could not be fetched. Kept separate from parse_vote
        # so many pages can be fetched concurrently.
        #
        # scrapelib (the base Scraper) already retries on connection errors
        # with exponential backoff and HTTP resilience handling, so we no
        # longer need a manual 10-attempt loop with fixed 10s sleeps that
        # could waste up to 100 seconds on a single flaky vote.
        try:
            response = self.get(
                link,
                timeout=60,
            )
        except Exception as e:
            self.warning(f"Skipping vote after repeated failures: {link}: {e}")
            return None

        return response.text

    def parse_vote(self, bill, link, session, text):
        if text is None:
            return

        if "Page Not Found" in text or "Page Unavailable" in text:
            self.warning(f"Missing vote page: {link}")
            return

        if "502: Bad gateway" in text:
            self.warning(f"Bad gateway error, skipping {bill} at {link}")
            return

        doc = lxml.html.fromstring(text)

        # The motion/short title lives in the vote hero's short-title span.
        # Older/alternate layouts used a "list-hero-sub" paragraph, so fall
        # back to that when the primary element is absent.
        motion_text = doc.xpath(
            "string(//span[contains(@class,'vote-hero-shorttitle')])"
        ).strip()

        if not motion_text:
            motion_text = doc.xpath(
                "string(//p[contains(@class,'list-hero-sub')])"
            ).strip()

        # Fall back to the roll call heading so votes are never emitted with
        # an empty motion_text.
        if not motion_text:
            motion_text = doc.xpath(
                "string(//h1[contains(@class,'list-hero-title')])"
            ).strip()

        chamber_text = doc.xpath(
            "string(//span[contains(@class,'list-kicker')])"
        ).strip()

        vote_date = None

        # Vote metadata contains both icon text and actual date text,
        # e.g. "event April 10, 2026". Extract only the date portion.
        for item in doc.xpath("//span[contains(@class,'vote-hero-meta-item')]"):
            item_text = " ".join(item.xpath(".//text()")).strip()

            match = re.search(
                r"([A-Za-z]+ \d{1,2}, \d{4})",
                item_text,
            )

            if match:
                vote_date = datetime.datetime.strptime(
                    match.group(1),
                    "%B %d, %Y",
                )
                break

        if vote_date is None:
            self.warning(f"No date found for {link}")
            return

        chamber = "upper" if "Senate" in chamber_text else "lower"

        yes_count = 0
        no_count = 0
        absent_count = 0

        # Kansas displays tally counts as:
        #   Yea
        #   Nay
        #   Other
        #
        # The "Other" bucket currently corresponds to absent members.
        for box in doc.xpath("//div[contains(@class,'vote-tally-num')]"):
            label = (
                box.xpath("string(.//span[contains(@class,'vote-tally-num-label')])")
                .strip()
                .lower()
            )

            value_text = box.xpath(
                "string(.//span[contains(@class,'vote-tally-num-value')])"
            ).strip()

            try:
                count = int(value_text)
            except ValueError:
                continue

            if label == "yea":
                yes_count = count
            elif label == "nay":
                no_count = count
            elif label == "other":
                absent_count = count

        members = doc.xpath("//li[contains(@class,'vote-member')]")

        if not members:
            self.warning(f"No votes found for {link}")
            return

        vote = VoteEvent(
            bill=bill,
            start_date=vote_date.strftime("%Y-%m-%d"),
            chamber=chamber,
            motion_text=motion_text,
            legislative_session=session,
            result="pass" if yes_count > no_count else "fail",
            classification="passage",
        )

        vote.dedupe_key = link

        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("absent", absent_count)

        vote.add_source(link)

        # Individual member votes are stored as:
        #   data-status="yea"
        #   data-status="nay"
        #   data-status="absent"
        for member in members:
            status = member.attrib.get(
                "data-status",
                "",
            ).lower()

            name = member.xpath(
                "string(.//span[contains(@class,'vote-member-name')]//a)"
            ).strip()

            # Remove chamber prefix to match legislator names
            # already present in OpenStates.
            name = re.sub(
                r"^(Rep\.|Sen\.)\s*",
                "",
                name,
            )

            if status == "yea":
                vote.vote("yes", name)
            elif status == "nay":
                vote.vote("no", name)
            elif status == "absent":
                vote.vote("absent", name)
            else:
                vote.vote("other", name)

        yield vote
