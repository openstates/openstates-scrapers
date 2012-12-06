from billy.scrape.committees import CommitteeScraper, Committee
from .util import get_client, get_url


class GACommitteeScraper(CommitteeScraper):
    jurisdiction = 'ga'
    latest_only = True

    cservice = get_client("Committees").service
    csource = get_url("Committees")
    ctty_cache = {}

    def scrape_session(self, term, chambers, session):
        sid = self.metadata['session_details'][session]['_guid']
        committees = self.cservice.GetCommitteesBySession(
            sid
        )['CommitteeListing']
        for committee in committees:
            cid = committee['Id']
            committee = self.cservice.GetCommittee(cid)

            name, typ, guid, code, description = [committee[x] for x in [
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
                    name,
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

            ctty.add_source(self.csource)
            self.save_committee(ctty)

    def scrape(self, term, chambers):
        for t in self.metadata['terms']:
            if t['name'] == term:
                for session in t['sessions']:
                    self.scrape_session(term, chambers, session)
