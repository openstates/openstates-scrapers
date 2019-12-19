from pupa.scrape import Scraper, Organization

from .util import get_client, get_url, backoff, SESSION_SITE_IDS


CTTIE_URL = (
    "http://www.house.ga.gov/COMMITTEES/en-US/committee.aspx?"
    "Committee={cttie}&Session={sid}"
)


class GACommitteeScraper(Scraper):
    cservice = get_client("Committees").service
    csource = get_url("Committees")
    ctty_cache = {}

    def scrape_session(self, session, chambers):
        sid = SESSION_SITE_IDS[session]
        committees = backoff(self.cservice.GetCommitteesBySession, sid)

        # if committees.strip() == "":
        #    return  # If we get here, it's a problem.
        # Commenting this out for future debugging. - PRT

        if str(committees).strip() == "":
            raise ValueError("Error: No committee data for sid: %s" % (sid))

        committees = committees["CommitteeListing"]
        for committee in committees:
            cid = committee["Id"]
            committee = backoff(self.cservice.GetCommittee, cid)
            subctty_cache = {}

            comname, typ, guid, code, description = [
                committee[x] for x in ["Name", "Type", "Id", "Code", "Description"]
            ]
            comchamber = {"House": "lower", "Senate": "upper", "Joint": "legislature"}[
                typ
            ]
            ctty_key = "{}-{}".format(typ, code)
            if ctty_key not in self.ctty_cache:
                ctty = Organization(
                    chamber=comchamber, name=comname, classification="committee"
                )
                ctty.extras = {"code": code, "guid": guid, "description": description}
                self.ctty_cache[ctty_key] = ctty

            members = committee["Members"]["CommitteeMember"]
            for member in members:
                name = "{First} {Last}".format(**dict(member["Member"]["Name"]))
                role = member["Role"]
                membership = ctty.add_member(name, role)
                membership.extras = {"guid": member["Member"]["Id"]}
                subcoms = member["SubCommittees"] or []
                for subcom in subcoms:
                    subcom = subcom[1][0]
                    subguid = subcom["Id"]
                    subcommittee = subcom["Name"]
                    if subcommittee in subctty_cache:
                        # Add member to existing subcommittee.
                        subctty = subctty_cache[subcommittee]
                    else:
                        # Create subcommittee.
                        subctty = Organization(
                            name=subcommittee,
                            classification="committee",
                            parent_id=ctty._id,
                        )
                        subctty.extras = {"guid": subguid}
                        subctty.add_source(self.csource)
                        subctty.add_source(
                            CTTIE_URL.format(**{"sid": sid, "cttie": guid})
                        )
                        subctty_cache[subcommittee] = subctty
                    membership = subctty.add_member(name, role)
                    membership.extras = {"guid": member["Member"]["Id"]}

            for subctty in subctty_cache.values():
                yield subctty

            ctty.add_source(self.csource)
            ctty.add_source(CTTIE_URL.format(**{"sid": sid, "cttie": guid}))
            yield ctty

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        chambers = [chamber] if chamber is not None else ["upper", "lower"]

        yield from self.scrape_session(session, chambers)
