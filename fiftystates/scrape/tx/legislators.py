import re

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.tx.utils import clean_committee_name

import lxml.etree


class TXLegislatorScraper(LegislatorScraper):
    state = 'tx'

    def scrape_legislators(self, chamber, year):
        if year != '2009':
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_senators(year)
        else:
            self.scrape_reps(year)

    def scrape_senators(self, year):
        senator_url = 'http://www.senate.state.tx.us/75r/senate/senmem.htm'
        with self.urlopen_context(senator_url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            for el in root.xpath('//table[@summary="senator identification"]'):
                sen_link = el.xpath('tr/td[@headers="senator"]/a')[0]
                full_name = sen_link.text
                district = el.xpath('string(tr/td[@headers="district"])')
                party = el.xpath('string(tr/td[@headers="party"])')

                leg = Legislator('81', 'upper', district, full_name,
                                 party=party)
                leg.add_source(senator_url)

                details_url = ('http://www.senate.state.tx.us/75r/senate/' +
                               sen_link.attrib['href'])
                with self.urlopen_context(details_url) as details_page:
                    details = lxml.etree.fromstring(details_page,
                                                    lxml.etree.HTMLParser())

                    try:
                        comms = details.xpath("//h2[contains(text(), "
                                              "'Committee Membership')]")[0]
                        comms = comms.getnext()
                        for comm in comms.xpath('li/a'):
                            comm_name = comm.text
                            if comm.tail:
                                comm_name += comm.tail

                            comm_name = clean_committee_name(comm_name)
                            leg.add_role('committee member', '81',
                                         committee=comm_name)
                    except IndexError:
                        # this legislator has no committee memberships yet
                        pass

                self.save_legislator(leg)

    def scrape_reps(self, year):
        rep_url = 'http://www.house.state.tx.us/members/welcome.php'
        with self.urlopen_context(rep_url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            for el in root.xpath('//form[@name="frmMembers"]/table/tr')[1:]:
                full_name = el.xpath('string(td/a/font/span)')
                district = el.xpath('string(td[2]/span)')
                county = el.xpath('string(td[3]/span)')

                if full_name.startswith('District'):
                    # Ignore empty seats
                    continue

                leg = Legislator('81', 'lower', district, full_name)
                leg.add_source(rep_url)

                # Is there anything out there that handles meta refresh?
                redirect_url = el.xpath('td/a')[0].attrib['href']
                redirect_url = ('http://www.house.state.tx.us/members/' +
                                redirect_url)
                details_url = redirect_url
                with self.urlopen_context(redirect_url) as redirect_page:
                    redirect = lxml.etree.fromstring(redirect_page,
                                                     lxml.etree.HTMLParser())

                    try:
                        filename = redirect.xpath(
                            "//meta[@http-equiv='refresh']")[0].attrib[
                            'content']

                        filename = filename.split('0;URL=')[1]

                        details_url = details_url.replace('welcome.htm',
                                                          filename)
                    except:
                        # The Speaker's member page does not redirect.
                        # The Speaker is not on any committees
                        # so we can just continue with the next member.
                        self.save_legislator(leg)
                        continue

                with self.urlopen_context(details_url) as details_page:
                    details = lxml.etree.fromstring(details_page,
                                                    lxml.etree.HTMLParser())

                    comms = details.xpath(
                        "//b[contains(text(), 'Committee Assignments')]/"
                        "..//a")

                    for comm in comms:
                        comm_name = clean_committee_name(comm.text)

                        if re.match('Authored|Sponsored|Co-|other sessions',
                                    comm_name):
                            # A couple representative pages are broken and
                            # include links to authored/sponsored bills
                            # under committees
                            continue

                        leg.add_role('committee member', '81',
                                     committee=comm_name)

                self.save_legislator(leg)
