import re

from billy.utils import urlescape
from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

COMM_TYPES = {'joint': 'Joint',
              # 'task_force': 'Task Force',
              'upper': 'Senate',
              'lower': 'House'}


class ARCommitteeScraper(CommitteeScraper):
    state = 'ar'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod

        base_url = ("http://www.arkleg.state.ar.us/assembly/2011/2011R/"
                    "Pages/Committees.aspx?committeetype=")

        for chamber, url_ext in COMM_TYPES.iteritems():
            chamber_url = urlescape(base_url + url_ext)
            with self.urlopen(chamber_url) as page:
                page = lxml.html.fromstring(page)

                for a in page.xpath('//td[@class="dxtl dxtl__B0"]/a'):
                    if a.attrib.get('colspan') == '2':
                        # colspan=2 signals a subcommittee, but it's easier
                        # to pick those up from links on the committee page,
                        # so we do that in scrape_committee() and skip
                        # it here
                        continue

                    name = re.sub(r'\s*-\s*(SENATE|HOUSE)$', '', a.text).strip()

                    comm_url = urlescape(a.attrib['href'])
                    if chamber == 'task_force':
                        chamber = 'joint'
                    self.scrape_committee(chamber, name, comm_url)

    def scrape_committee(self, chamber, name, url, subcommittee=None):
        if subcommittee:
            subcommittee = subcommittee.split('-')[-1].strip()
            subcommittee = re.sub(r'^(HOUSE|SENATE)\s+', '', subcommittee)

        comm = Committee(chamber, name, subcommittee=subcommittee)
        comm.add_source(url)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for tr in page.xpath('//table[@class="gridtable"]/'
                                 'tr[position()>1]'):
                if tr.xpath('string(td[1])'):
                    mtype = tr.xpath('string(td[1])')
                else:
                    mtype = 'member'
                member = tr.xpath('string(td[3])').split()
                member = ' '.join(member[1:])
                comm.add_member(member, mtype)

            for a in page.xpath('//ul/li/a'):
                sub_name = a.text.strip()
                sub_url = urlescape(a.attrib['href'])
                self.scrape_committee(chamber, name, sub_url,
                                      subcommittee=sub_name)

            self.save_committee(comm)
