from billy.scrape.legislators import LegislatorScraper, Legislator
from .util import get_client, get_url

class GALegislatorScraper(LegislatorScraper):
    state = 'ga'
    sservice = get_client("Members").service
    ssource = get_url("Members")

    def scrape_session(self, term, chambers, session):
        session = self.metadata['session_details'][session]
        sid = session['_guid']
        members = self.sservice.GetMembersBySession(sid)['MemberListing']
        for member in members:
            guid = member['Id']
            first_name, middle_name, last_name = (
                member['Name'][x] for x in ['First', 'Middle', 'Last']
            )
            chamber, district = (
                member['District'][x] for x in ['Type', 'Number']
            )

            party = member['Party']
            if party == 'Democrat':
                party = 'Democratic'

            # print first_name, middle_name, last_name, party
            # print chamber, district
            name = "%s %s" % (first_name, last_name)

            chamber = {
                "House": 'lower',
                "Senate": 'upper'
            }[chamber]

            if party.strip() == '':
                party = 'other'

            legislator = Legislator(
                term,
                chamber,
                str(district),
                name,
                party=party,
                last_name=last_name,
                first_name=first_name
            )
            if middle_name:
                legislator['middle_name'] = middle_name

            ainfo = [
                member['DistrictAddress'][x] for x in [
                    'Street', 'City', 'State', 'Zip'
                ]
            ]
            if not None in ainfo:
                # XXX: Debug this nonsense.
                ainfo = [x.strip() for x in ainfo]
                address = " ".join(ainfo)
                email = member['DistrictAddress']['Email']
                legislator.add_office('district',
                                      'District Address',
                                      address=address,
                                      email=email)

            legislator.add_source(self.ssource)
            self.save_legislator(legislator)

    def scrape(self, term, chambers):
        for t in self.metadata['terms']:
            if t['name'] == term:
                for session in t['sessions']:
                    self.scrape_session(term, chambers, session)
