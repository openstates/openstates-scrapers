from billy.scrape.legislators import LegislatorScraper, Legislator
from .util import get_client, get_url
import re

def extract_nick_name(nick_name):
    """Returns a nickname string"""	
    new_nick_name = None
    
    if re.search(r'"[^"]+"', nick_name):
        # "Able" Mable
        # Pedro "Pete"
        # E. Culver "Rusty"
        new_nick_name = re.search(r'"([^"]+)"', nick_name).group(1)
    elif ' ' in nick_name:
        # Mary Margaret
        # Freddie Powell
        new_nick_name = nick_name.split(" ")[0]
    else:
        # Bill
        new_nick_name = nick_name
        
    return new_nick_name

class GALegislatorScraper(LegislatorScraper):
    jurisdiction = 'ga'
    sservice = get_client("Members").service
    ssource = get_url("Members")

    def clean_list(self,dirty_list):
        new_list = []

        for x in dirty_list:
            if x is None:
                new_list.append(x)
            else:
                new_list.append(x.strip())

        return new_list

    def scrape_session(self, term, chambers, session):
        session = self.metadata['session_details'][session]
        sid = session['_guid']
        members = self.sservice.GetMembersBySession(sid)['MemberListing']

        for member in members:

            guid = member['Id']

            member_info = self.sservice.GetMember(guid)

            nick_name, first_name, middle_name, last_name = (
                member_info['Name'][x] for x in [
                    'Nickname', 'First', 'Middle', 'Last'
                ]
            )
            
            if nick_name:
                nick_name = extract_nick_name(nick_name)
                first_name = nick_name

            if middle_name:
                full_name = "%s %s %s" % (first_name.strip(), middle_name.strip(), last_name.strip())
            else:
                full_name = "%s %s" % (first_name.strip(), last_name.strip())

            legislative_service = []
            for leg_service in member_info['SessionsInService']['LegislativeService']:
                if leg_service['Session']['Id'] == sid:
                    legislative_service = leg_service

            # legislative_service shouldn't be empty but just in case it is,
            # we set chamber, party and district to None causing an exception
            # when trying to add the legislator

            if legislative_service:	
                party = legislative_service['Party']

                if party == 'Democrat':
                    party = 'Democratic'

                if party.strip() == '':
                    party = 'other'
                
                chamber, district = (
                    legislative_service['District'][x] for x in ['Type', 'Number']
                )

                chamber = {
                    "House": 'lower',
                    "Senate": 'upper'
                }[chamber]

            else:
                party = None
                chamber, district = [None,None]
            
            # Leaving off first and last for upstream
            legislator = Legislator(
                term,
                chamber,
                str(district),
                full_name,
                party=party,
            #	last_name=last_name,
            #	first_name=first_name,
                _guid=guid
            )

            capital_address = self.clean_list([
                member_info['Address'][x] for x in ['Street', 'City', 'State', 'Zip']
            ])

            capital_address = (" ".join(addr_component for addr_component in capital_address if addr_component)).strip()

            capital_contact_info = self.clean_list([
                member_info['Address'][x] for x in [
                    'Email', 'Phone', 'Fax'
                ]
            ])

            # Sometimes email is set to a long cryptic string.
            # If it doesn't have a @ character, simply set it to None
            # examples:
            # 01X5dvct3G1lV6RQ7I9o926Q==&c=xT8jBs5X4S7ZX2TOajTx2W7CBprTaVlpcvUvHEv78GI=
            # 01X5dvct3G1lV6RQ7I9o926Q==&c=eSH9vpfdy3XJ989Gpw4MOdUa3n55NTA8ev58RPJuzA8=	

            if capital_contact_info[0] and '@' not in capital_contact_info[0]:
                capital_contact_info[0] = None

            # if we have more than 2 chars (eg state)
            # or a phone/fax/email address record the info
            if len(capital_address) > 2 or not capital_contact_info.count(None) == 3:
                legislator.add_office(
                    'capitol',
                    'Capitol Address',
                    address=capital_address,
                    phone=capital_contact_info[1],
                    fax=capital_contact_info[2],
                    email=capital_contact_info[0]
                )

            district_address = self.clean_list([
                member_info['DistrictAddress'][x] for x in [
                    'Street', 'City', 'State', 'Zip'
                ]
            ])

            district_contact_info = self.clean_list([
                member_info['DistrictAddress'][x] for x in [
                    'Email', 'Phone', 'Fax'
                ]
            ])

            # Same issue with district email. See above comment
            if district_contact_info[0] and '@' not in district_contact_info[0]:
                district_contact_info[0] = None

            district_address = (" ".join(addr_component for addr_component in district_address if addr_component)).strip()

            if len(capital_address) > 2 or not capital_contact_info.count(None) == 3:
                legislator.add_office(
                    'district',
                    'District Address',
                    address=district_address,
                    phone=district_contact_info[1],
                    fax=district_contact_info[2],
                    email=district_contact_info[0]
                )

            # Add committees
            # I don't think this is actually needed.
            # The committees scraper should take care of this.
            # Commenting out for now.

            #if hasattr(legislative_service['CommitteeMemberships'],'CommitteeMembership') and (legislative_service['CommitteeMemberships']['CommitteeMembership']) > 0:
            #	for committee_membership in legislative_service['CommitteeMemberships']['CommitteeMembership']:
            #		committee_name = committee_membership['Committee']['Name']
            #		committee_role = committee_membership['Role'].lower()

            #		legislator.add_role(
            #			role=committee_role,
            #			term=term,
            #			name=committee_name
            #		)
        
            legislator.add_source(self.ssource)
            self.save_legislator(legislator)

    def scrape(self, term, chambers):
        for t in self.metadata['terms']:
            if t['name'] == term:
                for session in t['sessions']:
                    self.scrape_session(term, chambers, session)
