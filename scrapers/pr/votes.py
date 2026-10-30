from openstates.scrape import Scraper, VoteEvent
from openstates.exceptions import EmptyScrape

API = "https://public.senado.evotepr.com/api"

_measure_types = {
    "P. del S.": "PS",
    "P. de la C.": "PC",
    "R. del S.": "RS",
    "R. de la C.": "RC",
    "R. C. del S.": "RCS",
    "R. C. de la C.": "RCC",
    "R. Conc. del S.": "RKS",
    "R. Conc. de la C.": "RKC",
    "Nombramiento": "NM",
}

_vote_types = {
    "infavor": "yes",
    "against": "no",
    "abstention": "abstain",
    "absent": "absent",
}


class PRVoteScraper(Scraper):
    # Senate roll calls from its e-vote reports app,
    # https://votaciones.senado.evotepr.com/measures
    def scrape(self, chamber=None, session=None):
        # only the Senate publishes roll calls
        if chamber and chamber != "upper":
            raise EmptyScrape

        assemblies = self.get(f"{API}/assemblies?loadLastDate=true").json()
        assembly = next(
            a["idAssembly"] for a in assemblies if a["startDate"][:4] == session[:4]
        )
        measures = self.post(
            f"{API}/reports/measures", json={"filter": {"assemblyId": assembly}}
        ).json()
        ids = [m["id"] for m in measures]
        # the API times out returning a whole session's votes at once
        for i in range(0, len(ids), 200):
            batch = self.post(
                f"{API}/reports/measures?loadVotes=true",
                json={"filter": {"measureIds": ids[i : i + 200]}},
            ).json()
            for measure in batch:
                yield from self.scrape_vote(session, measure)

    def scrape_vote(self, session, measure):
        code = _measure_types.get(measure["measureType"])
        # measureName can name two measures voted together, e.g. "1173 y 1183"
        if not code or not measure["measureName"].isdigit():
            self.warning(
                "Skipping vote on %s %s",
                measure["measureType"],
                measure["measureName"],
            )
            return

        motion = " ".join(
            x.strip()
            for x in (
                measure["measureType"],
                measure["measureName"],
                measure["measureReference"],
                measure["measureAmendment"],
            )
            if x.strip()
        )
        vote = VoteEvent(
            chamber="upper",
            # every vote is timestamped 12:xx UTC; only the date is real
            start_date=measure["date"][:10],
            motion_text=motion,
            result="pass" if measure["measureStatus"] == "approved" else "fail",
            classification="passage",
            legislative_session=session,
            bill=f"{code}{int(measure['measureName']):04d}",
            bill_chamber="lower" if code.endswith("C") else "upper",
        )
        vote.dedupe_key = f"{API}/reports/measures#{measure['id']}"
        vote.set_count("yes", measure["inFavor"])
        vote.set_count("no", measure["against"])
        vote.set_count("abstain", measure["abstention"])
        vote.set_count("absent", measure["absent"])
        for v in measure["votes"]:
            # names are "Last,  First"
            last, _, first = v["name"].partition(",")
            vote.vote(_vote_types[v["vote"]], f"{first.strip()} {last.strip()}")
        vote.add_source("https://votaciones.senado.evotepr.com/measures")
        yield vote
