import re

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.etree


class OHCommitteeScraper(CommitteeScraper):
    state = 'oh'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            self.scrape_senate_comm(chamber, term)
        else:
            self.scrape_reps_comm(chamber, term)

    def scrape_reps_comm(self, chamber, term):
        save_chamber = chamber

        # id range for senate committees on their website
        for comm_id in range(87, 124):
            chamber = save_chamber
            comm_url = ('http://www.house.state.oh.us/index.php?option='
                        'com_displaycommittees&task=2&type=Regular&'
                        'committeeId=%d' % comm_id)

            with self.urlopen(comm_url) as page:
                page = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

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

    def scrape_senate_comm(self, chamber, term):
        committees = ["agriculture-environment-and-natural-resources",
                      "education",
                      "energy-and-public-utilities",
                      "finance",
                      "financial-institutions",
                      "government-oversight-and-reform",
                      "health-human-services-and-aging",
                      "highways-and-transportation",
                      "insurance-commerce-and-labor",
                      "judiciary-civil-justice",
                      "judiciary-criminal-justice",
                      "rules-and-reference",
                      "state-and-local-government-and-veterans-affairs",
                      "ways-and-means-and-economic-development"]

        for name in committees:
            comm_url = ('http://www.ohiosenate.gov/committees/standing/detail/'
                        '%s.html' % name)

            with self.urlopen(comm_url) as page:
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                comm_name = name
                if comm_name.startswith('agriculture'):
                    comm_name = ("Agriculture, Environment and "
                                 "Natural Resources")
                else:
                    comm_name = comm_name.replace("-", " ")
                    comm_name = comm_name.title()

                committee = Committee(chamber, comm_name)
                committee.add_source(comm_url)

                for el in root.xpath('//table/tr/td'):
                    sen_name = el.xpath('string(a[@class="senatorLN"])')
                    mark = sen_name.find('(')
                    full_name = sen_name[0:mark]
                    full_name = full_name.strip()
                    if full_name:
                        committee.add_member(full_name)

                if committee['members']:
                    self.save_committee(committee)
