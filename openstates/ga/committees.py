import time

from billy.scrape.committees import CommitteeScraper, Committee
from .util import get_client, get_url, backoff


CTTIE_URL = ("http://www.house.ga.gov/COMMITTEES/en-US/committee.aspx?"
             "Committee={cttie}&Session={sid}")


class GACommitteeScraper(CommitteeScraper):
    jurisdiction = 'ga'
    latest_only = True

    cservice = get_client("Committees").service
    csource = get_url("Committees")
    ctty_cache = {}

    def scrape_session(self, term, chambers, session):
        sid = self.metadata['session_details'][session]['_guid']
        committees = backoff(self.cservice.GetCommitteesBySession, sid)

        #if committees.strip() == "":
        #    return  # If we get here, it's a problem.
        # Commenting this out for future debugging. - PRT

        if str(committees).strip() == "":
            raise ValueError("Error: No committee data for sid: %s" % (sid))

        committees = committees['CommitteeListing']
        for committee in committees:
            cid = committee['Id']
            committee = backoff(self.cservice.GetCommittee, cid)
            subctty_cache = {}

            comname, typ, guid, code, description = [committee[x] for x in [
                'Name', 'Type', 'Id', 'Code', 'Description'
            ]]
            chamber = {
                "House": "lower",
                "Senate": "upper",
                "Joint": "joint"
            }[typ]
            ctty = None
            if code in self.ctty_cache:
                ctty = self.ctty_cache[code]
                if (ctty['chamber'] != chamber) and (description and
                        'joint' in description.lower()):
                    ctty['chamber'] = 'joint'
                else:
                    ctty = None

            if ctty is None:
                ctty = Committee(
                    chamber,
                    comname,
                    code=code,
                    _guid=guid,
                    description=description
                )
                self.ctty_cache[code] = ctty

            members = committee['Members']['CommitteeMember']
            for member in members:
                name = "{First} {Last}".format(**dict(member['Member']['Name']))
                role = member['Role']
                ctty.add_member(name, role, _guid=member['Member']['Id'])
                subcoms = member['SubCommittees']
                if subcoms != None:
                    for subcom in subcoms:
                        subcom = subcom[1][0]
                        subguid = subcom['Id']
                        subcommittee = subcom['Name']
                        if subcommittee in subctty_cache:
                            # Add member to existing subcommittee.
                            subctty = subctty_cache[subcommittee]
                        else:
                            # Create subcommittee.
                            subctty = Committee(
                                chamber,
                                comname,
                                _guid=subguid,
                                subcommittee=subcommittee
                            )
                            subctty.add_source(self.csource)
                            subctty.add_source(CTTIE_URL.format(**{
                                "sid": sid,
                                "cttie": guid,
                            }))
                            subctty_cache[subcommittee] = subctty
                        subctty.add_member(
                            name, role, _guid=member['Member']['Id'])

            for subctty in subctty_cache.values():
                self.save_committee(subctty)

            ctty.add_source(self.csource)
            ctty.add_source(CTTIE_URL.format(**{
                "sid": sid,
                "cttie": guid,
            }))
            self.save_committee(ctty)

    def scrape(self, term, chambers):
        for t in self.metadata['terms']:
            if t['name'] == term:
                for session in t['sessions']:
                    self.scrape_session(term, chambers, session)
