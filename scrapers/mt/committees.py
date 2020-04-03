# -*- coding: utf-8 -*-
import re
from itertools import dropwhile
from openstates.scrape import Organization, Scraper
from openstates.utils import convert_pdf


committee_urls = {
    "lower": {
        "2013": (
            "http://leg.mt.gov/content/Committees/Session/"
            "2013%20house%20committees%20-%20columns.pdf"
        ),
        "2015": "http://leg.mt.gov/content/Sessions/64th/2015-house-committees.pdf",
        "2017": "http://leg.mt.gov/content/Committees/Session/2017-house-committees.pdf",
    },
    "upper": {
        "2013": (
            "http://leg.mt.gov/content/Committees/Session/"
            "2013%20senate%20committees%20-%20columns.pdf"
        ),
        "2015": "http://leg.mt.gov/content/Sessions/64th/2015-senate-committees.pdf",
        "2017": "http://leg.mt.gov/content/Committees/Session/2017-senate-committees.pdf",
    },
}


class MTCommitteeScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        if not session:
            session = max(committee_urls["lower"].keys())
        chambers = [chamber] if chamber else ["upper", "lower"]

        for chamber in chambers:
            url = committee_urls[chamber][session]
            fn, _ = self.urlretrieve(url)
            yield from self.scrape_committees_pdf(session, chamber, fn, url)

    def scrape_committees_pdf(self, year, chamber, filename, url):
        if chamber == "lower" and year == "2015":
            text = self._fix_house_text(filename).decode()
        else:
            text = convert_pdf(filename, type="text-nolayout").decode()

        for hotgarbage, replacement in (
            (
                r"Judicial Branch, Law Enforcement,\s+and\s+Justice",
                "Judicial Branch, Law Enforcement, and Justice",
            ),
            (
                r"Natural Resources and\s+Transportation",
                "Natural Resources and Transportation",
            ),
            (
                r"(?u)Federal Relations, Energy,?\s+and\s+Telecommunications",
                "Federal Relations, Energy, and Telecommunications",
            ),
        ):
            text = re.sub(hotgarbage, replacement, text)

        lines = iter(text.splitlines())

        # Drop any lines before the ag committee.
        lines = dropwhile(lambda s: "Agriculture" not in s, lines)

        comm = None
        for line in lines:
            # Replace Unicode variants with ASCII equivalents
            line = line.replace(" ", " ").replace("‐", "-")

            if "Subcommittees" in line:
                self.warning("Currently, we're skipping subcommittees")
                # https://github.com/openstates/openstates/issues/2099
                break
            if is_committee_name(line):
                if comm and comm._related:
                    yield comm

                committee = line.strip()
                comm = Organization(
                    name=committee, chamber=chamber, classification="committee"
                )

                comm.add_source(url)

            elif is_legislator_name(line):
                name, party = line.rsplit("(", 1)
                name = name.strip().replace("Rep. ", "").replace("Sen. ", "")
                if re.search(" Ch", party):
                    role = "chair"
                elif " VCh" in party:
                    role = "vice chair"
                elif " MVCh" in party:
                    role = "minority vice chair"
                else:
                    role = "member"
                comm.add_member(name, role)

        if comm._related:
            yield comm

    def _fix_house_text(self, filename):
        """
        TLDR: throw out bad text, replace it using different parser
        settings.

        When using `pdftotext` on the 2015 House committee list,
        the second and third columns of the second page get mixed up,
        which makes it very difficult to parse. Adding the `--layout`
        option fixes this, but isn't worth switching all parsing to
        that since the standard `pdftotext --nolayout` is easier in all
        other cases.

        The best solution to this is to throw out the offending text,
        and replace it with the correct text. The third and fourth
        columns are joint comittees that are scraped from the Senate
        document, so the only column that needs to be inserted this way
        is the second.
        """

        # Take the usable text from the normally-working parsing settings
        text = convert_pdf(filename, type="text-nolayout")
        assert "Revised: January 23, 2015" in text, (
            "House committee list has changed; check that the special-case"
            " fix is still necessary, and that the result is still correct"
        )
        text = re.sub(r"(?sm)Appropriations/F&C.*$", "", text)

        # Take the usable column from the alternate parser
        alternate_text = convert_pdf(filename, type="text")
        alternate_lines = alternate_text.split("\n")

        HEADER_OF_COLUMN_TO_REPLACE = "State Administration (cont.)      "
        (text_of_line_to_replace,) = [
            x for x in alternate_lines if HEADER_OF_COLUMN_TO_REPLACE in x
        ]
        first_line_to_replace = alternate_lines.index(text_of_line_to_replace)
        first_character_to_replace = (
            alternate_lines[first_line_to_replace].index(HEADER_OF_COLUMN_TO_REPLACE)
            - 1
        )
        last_character_to_replace = first_character_to_replace + len(
            HEADER_OF_COLUMN_TO_REPLACE
        )

        column_lines_to_add = [
            x[first_character_to_replace:last_character_to_replace]
            for x in alternate_lines[first_line_to_replace + 1 :]
        ]
        column_text_to_add = "\n".join(column_lines_to_add)

        text = text + column_text_to_add
        return text


def is_committee_name(line):
    if "(cont.)" in line.lower():
        return False
    for s in (
        "committee",
        " and ",
        "business",
        "resources",
        "legislative",
        "administration",
        "government",
        "local",
        "planning",
        "judicial",
        "natural",
        "resources",
        "general",
        "health",
        "human",
        "education",
    ):
        if s in line.lower():
            return True
    if line.istitle() and len(line.split()) == 1:
        return True
    return False


def is_legislator_name(line):
    return re.search(r"\([RD]", line)
