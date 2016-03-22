import time

from openstates.utils import LXMLMixin
from billy.scrape.legislators import LegislatorScraper, Legislator
from .util import get_client, get_url, backoff

import lxml


HOMEPAGE_URLS = {
    "lower": ("http://www.house.ga.gov/Representatives/en-US/"
             "member.aspx?Member={code}&Session={sid}"),
    "upper": ("http://www.senate.ga.gov/SENATORS/en-US/"
              "member.aspx?Member={code}&Session={sid}")
}


class GALegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ga'
    sservice = get_client("Members").service
    ssource = get_url("Members")

    def clean_list(self, dirty_list):
        new_list = []
        for x in dirty_list:
            if x is None:
                new_list.append(x)
            else:
                new_list.append(x.strip())
        return new_list

    def scrape_homepage(self, url, kwargs):
        url = url.format(**kwargs)
        page = self.lxmlize(url)
        images = page.xpath("//img[contains(@src, 'SiteCollectionImages')]")

        if len(images) != 1:
            raise Exception

        return url, images[0].attrib['src']

    def scrape_session(self, term, chambers, session):
        session = self.metadata['session_details'][session]
        sid = session['_guid']
        members = backoff(
            self.sservice.GetMembersBySession,
            sid
        )['MemberListing']

        for member in members:
            guid = member['Id']
            member_info = backoff(self.sservice.GetMember, guid)

            # Check to see if the member has vacated; skip if so:
            try:
                legislative_service = next(service for service
                    in member_info['SessionsInService']['LegislativeService']
                    if service['Session']['Id'] == sid)
            except IndexError:
                raise Exception("Something very bad is going on with the "
                                "Legislative service")

            if legislative_service['DateVacated']:
                continue

            nick_name, first_name, middle_name, last_name = (
                member_info['Name'][x] for x in [
                    'Nickname', 'First', 'Middle', 'Last'
                ]
            )

            first_name = nick_name if nick_name else first_name

            if middle_name:
                full_name = "%s %s %s" % (first_name, middle_name, last_name)
            else:
                full_name = "%s %s" % (first_name, last_name)

            party = legislative_service['Party']

            if party == 'Democrat':
                party = 'Democratic'

            elif party.strip() == '':
                party = 'other'

            chamber, district = (
                legislative_service['District'][x] for x in [
                    'Type', 'Number'
                ]
            )

            chamber = {
                "House": 'lower',
                "Senate": 'upper'
            }[chamber]

            url, photo = self.scrape_homepage(HOMEPAGE_URLS[chamber],
                                              {"code": guid, "sid": sid})


            legislator = Legislator(
                term,
                chamber,
                str(district),
                full_name,
                party=party,
                last_name=last_name,
                first_name=first_name,
                url=url,
                photo_url=photo,
                _guid=guid
            )

            capital_address = self.clean_list([
                member_info['Address'][x] for x in [
                    'Street', 'City', 'State', 'Zip'
                ]
            ])

            capital_address = (" ".join(
                addr_component for addr_component
                    in capital_address if addr_component
            )).strip()

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
                if (capital_contact_info[0] \
                        and 'quickrxdrugs@yahoo.com' in capital_contact_info[0]):
                    self.warning("XXX: GA SITE WAS HACKED.")
                    capital_contact_info[1] = None

                if capital_address.strip() != "":
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

            district_address = (
                " ".join(
                    addr_component for addr_component
                        in district_address if addr_component
                )).strip()

            if len(capital_address) > 2 or not capital_contact_info.count(None) == 3:
                if (district_contact_info[1] and \
                        'quickrxdrugs@yahoo.com' in district_contact_info[1]):
                    self.warning("XXX: GA SITE WAS HACKED.")
                    district_contact_info[1] = None

                if district_address.strip() != "":
                    legislator.add_office(
                        'district',
                        'District Address',
                        address=district_address,
                        phone=district_contact_info[1],
                        fax=district_contact_info[2],
                        email=district_contact_info[0]
                    )

            legislator.add_source(self.ssource)
            legislator.add_source(HOMEPAGE_URLS[chamber].format(
                **{"code": guid, "sid": sid}))

            self.save_legislator(legislator)

    def scrape(self, term, chambers):
        for t in self.metadata['terms']:
            if t['name'] == term:
                for session in t['sessions']:
                    self.scrape_session(term, chambers, session)
