import re
import urlparse
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.etree, lxml.html

class RICommitteeScraper(CommitteeScraper):
    state = 'ri'

    def scrape(self, chamber, term_name):
        self.validate_term(term_name, latest_only=True)

        if chamber == 'upper':
            self.scrape_senate_comm()
            # scrape joint committees under senate
            self.scrape_joint_comm()
        elif chamber == 'lower':
            self.scrape_reps_comm()

    def scrape_comm_list(self, ctype):
        url = 'http://www.rilin.state.ri.us/Sitemap.html'
        self.log("looking for "+ctype)
        with self.urlopen(url) as page:
            root = lxml.html.fromstring(page)
            return root.xpath("//a[contains(@href,'"+ctype+"')]")

    def add_members(self,comm,url):
        with self.urlopen(url) as page:
            self.log(comm)
            root = lxml.html.fromstring(page)
            # The first <tr> in the table of members
            membertable=root.xpath('//p[@class="style28"]')[0].getparent().getparent().getnext()
            while membertable is not None and membertable.tag == 'tr':
                flds=membertable.xpath('td//text()')
                mname = flds[0]
                role = flds[1][2:]
                idx = mname.find("Senator ")
                if idx == -1: continue
                membername=mname[idx+8:]
                self.log("name "+membername+" role "+role)
                comm.add_member(membername, role)
                membertable = membertable.getnext()
        
    def scrape_reps_comm(self):
       base = 'http://www.rilin.state.ri.us'

       linklist = self.scrape_comm_list('ComMemR')
       for a in linklist:
           link=a.attrib['href']
           commName=a.text
           url=base+link
           self.log("url "+url)
           c=Committee('lower',commName)
           self.add_members(c,url)
           c.add_source(url)
           self.save_committee(c)

    def scrape_senate_comm(self):
       base = 'http://www.rilin.state.ri.us'

       linklist = self.scrape_comm_list('ComMemS')
       for a in linklist:
           link=a.attrib['href']
           commName=a.text
           url=base+link
           self.log("url "+url)
           c=Committee('upper',commName)
           self.add_members(c,url)
           c.add_source(url)
           self.save_committee(c)

    def scrape_joint_comm(self):
       base = 'http://www.rilin.state.ri.us'

       linklist = self.scrape_comm_list('ComMemJ')
       for a in linklist:
           link=a.attrib['href']
           commName=a.text
           url=base+link
           self.log("url "+url)
           c=Committee('joint',commName)
           self.add_members(c,url)
           c.add_source(url)
           self.save_committee(c)

