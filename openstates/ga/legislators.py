from billy.scrape.legislators import LegislatorScraper, Legislator
from .util import get_client, get_url


class GALegislatorScraper(LegislatorScraper):
    jurisdiction = 'ga'
    sservice = get_client("Members").service
    ssource = get_url("Members")

    def scrape_session(self, term, chambers, session):
        session = self.metadata['session_details'][session]
        sid = session['_guid']
        members = self.sservice.GetMembersBySession(sid)['MemberListing']
        for member in members:
            guid = member['Id']
            # print member['Name']
            nick_name, first_name, middle_name, last_name = (
                member['Name'][x] for x in [
                    'Nickname', 'First', 'Middle', 'Last'
                ]
            )
            chamber, district = (
                member['District'][x] for x in ['Type', 'Number']
            )

            party = member['Party']
            if party == 'Democrat':
                party = 'Democratic'

            # print first_name, middle_name, last_name, party
            # print chamber, district
            first_name = nick_name if nick_name else first_name
            # XXX: Due to the upstream handling...

            # if middle_name:
            #     name = "%s %s %s" % (first_name, middle_name, last_name)
            # else:
            # blocked out due to GA putting middle_name in first_name ...
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
#                last_name=last_name,
#                first_name=first_name,
                _guid=guid
            )
#            if middle_name:
#                legislator['middle_name'] = middle_name

#           Sadly, upstream isn't good about keeping first names first only,
#           so I'm blocking this out.

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
