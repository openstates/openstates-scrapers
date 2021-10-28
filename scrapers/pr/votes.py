# -*- coding: utf-8 -*-
from datetime import datetime, time, timezone, timedelta
import re
import lxml.etree

from openstates.utils import convert_pdf
from openstates.scrape import Scraper, VoteEvent

_measure_classifiers = (
    ("Nombramiento", "NM"),
    ("R. del S.", "RS"),
    ("R. Conc. del S.", "RS"),
    ("P. del S.", "PS"),
    ("P. de la C.", "PC"),
    ("R. C. del S.", "RCS"),
)

_vote_classifiers = (
    ("A favor", "yes"),
    ("En contra", "no"),
    ("Ausente", "absent"),
    ("Abstenido", "abstain"),
    ("Confirmado", "yes"),
)


class PRVoteScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        # only senate votes currently scraped
        if chamber and chamber != "upper":
            return
        if session != "2021-2024":
            return

        yield from self.scrape_upper(session)

    def scrape_upper(self, session):
        url = "https://www.senado.pr.gov/Pages/VotacionMedidas.aspx"
        chamber = "upper"
        html = self.get(url).content

        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        urls = [x for x in doc.xpath("//a[@href]/@href") if x.endswith(".pdf")][::-1]

        for url in urls:
            date = re.match(r"^(.*)/(?P<datestring>\d*).pdf", url).groupdict()[
                "datestring"
            ]
            date = datetime.strptime(date, "%Y%m%d")
            date = datetime.combine(date, time(tzinfo=timezone(timedelta(hours=-5))))
            yield self.scrape_journal(url, chamber, session, date)

    def scrape_journal(self, url, chamber, session, date):
        filename = self.urlretrieve(url)[0]
        self.logger.info("Saved journal to %r", filename)
        all_text = convert_pdf(filename, type="text")

        lines = all_text.split(b"\n")
        lines = [line.decode("utf-8") for line in lines]
        lines = [line.strip() for line in lines]

        for index, line in enumerate(lines):
            if "Resultado de la Votación para la Medida" not in line:
                continue
            name_line = lines[index + 1]
            result_line = lines[index + 2]
            nomination_result_line = lines[index + 3]

            name_match = re.match(
                r"^(?P<type>.*) (?P<num>\d*) (?P<ref>.*)$", name_line
            ).groupdict()

            bill = self.classify_measure_type(name_match)
            if not bill:
                continue

            if re.match("^NM", bill):
                # Nomination
                if re.match(r"(.*)Confirmado", nomination_result_line):
                    result = "pass"
                else:
                    msg = "Unhandled nomination result of: {}. Skipping.".format(
                        nomination_result_line
                    )
                    self.logger.warning(msg)
                    continue
                name_line = result_line

            else:
                # Not a Nomination
                if re.match(r"(.*)Recibido", result_line):
                    msg = "Result was 'Recibido': {}. Skipping.".format(result_line)
                    self.logger.warning(msg)
                    continue
                try:
                    vote_result = re.match(
                        r".* (?P<yes>\d*)X(?P<no>\d*)X(?P<abstain>\d*)X(?P<absent>\d*) (?P<result>\w*)",
                        result_line,
                    ).groupdict()
                except AttributeError:
                    msg = "Could not determine voting result of: {}. Skipping.".format(
                        result_line
                    )
                    self.logger.warning(msg)
                    continue

                if vote_result["result"] == "Aprobada":
                    result = "pass"
                else:
                    result = "fail"
                    msg = "Voting result {} not guarenteed to be 'fail'. Take a look.".format(
                        vote_result["result"]
                    )
                    self.logger.warning(msg)

            vote = VoteEvent(
                chamber=chamber,
                start_date=date,
                motion_text=name_line,
                result=result,
                classification="passage",
                legislative_session=session,
                bill=bill,
                bill_chamber=chamber,
            )

            vote_index = index + 3

            while not re.match("^Votante", lines[vote_index]):
                vote_index = vote_index + 1

            vote_index = vote_index + 1

            votes = {
                "yes": 0,
                "no": 0,
                "absent": 0,
                "abstain": 0,
            }

            while lines[vote_index].strip() and not re.match(
                r"Senado de", lines[vote_index]
            ):
                name, vtype = parse_vote(lines[vote_index])
                votes[vtype] += 1
                vote.vote(vtype, name)
                vote_index = vote_index + 1

            for vtype in ("yes", "no", "absent", "abstain"):
                vote.set_count(vtype, votes[vtype])

            vote.add_source(url)
            yield vote

    def classify_measure_type(self, name_match):
        for pattern, mtype in _measure_classifiers:
            if re.match(pattern, name_match["type"]):
                bill = mtype + name_match["num"]
                return bill
        msg = "Could not determine category of result: {}. Skipping.".format(
            name_match["type"]
        )
        self.logger.warning(msg)
        return None


def parse_vote(line):
    result = re.match(r"^(?P<re_name>.*),(.*)    (?P<re_vote>.*)$", line).groupdict()
    for pattern, vtype in _vote_classifiers:
        if re.match(pattern, result["re_vote"]):
            vote = vtype
    return result["re_name"], vote
