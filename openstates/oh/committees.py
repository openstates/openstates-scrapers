import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class OHCommitteeScraper(CommitteeScraper):
    state = 'oh'
    latest_only = True

    def scrape(self, chamber, term):
        if chamber == 'upper':
            self.scrape_upper_committees()
        else:
            self.scrape_lower_committees()

    def scrape_lower_committees(self):
        # id range for senate committees on their website
        for comm_id in range(87, 124):
            comm_url = ('http://www.house.state.oh.us/index.php?option='
                        'com_displaycommittees&task=2&type=Regular&'
                        'committeeId=%d' % comm_id)

            with self.urlopen(comm_url) as page:
                page = lxml.html.fromstring(page)

                comm_name = page.xpath(
                    'string(//table/tr[@class="committeeHeader"]/td)')
                comm_name = comm_name.replace("/", " ").strip()

                if not comm_name:
                    continue

                if comm_id < 92:
                    chamber = "joint"

                committee = Committee(chamber, comm_name)
                committee.add_source(comm_url)

                for link in page.xpath("//a[contains(@href, 'district')]"):
                    name = link.text
                    if name and name.strip():
                        committee.add_member(name.strip())

                self.save_committee(committee)

    def scrape_upper_committees(self):
        url = ("http://www.ohiosenate.gov/education/"
               "about-senate-committees.html")
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, '/committees/')]"):
                self.scrape_upper_committee(link.attrib['href'])

    def scrape_upper_committee(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            comm_name = page.xpath(
                "string(//div[@class='contentheading'])")

            committee = Committee('upper', comm_name)
            committee.add_source(url)

            for el in page.xpath('//table/tr/td'):
                sen_name = el.xpath('string(a[@class="senatorLN"])')
                mark = sen_name.find('(')
                full_name = sen_name[0:mark]
                full_name = full_name.strip()
                if full_name:
                    committee.add_member(full_name)

            if committee['members']:
                self.save_committee(committee)
