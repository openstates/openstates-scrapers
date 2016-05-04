import re
import urlparse
import datetime
import requests

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.etree, lxml.html

COMM_BLACKLIST = [
    "Constitutional and Regulatory Issues"
    # This page is timing out. This is most likely an issue with Upstream,
    # it seems to happen all over the place.
]


def clean(stream):
    return re.sub(
        "\s+",
        " ",
        stream.encode('ascii', errors='ignore')
    ).strip()


class RICommitteeScraper(CommitteeScraper):
    jurisdiction = 'ri'

    def scrape(self, chamber, term_name):
        self.validate_term(term_name, latest_only=True)

        self._session = requests.Session()

        if chamber == 'upper':
            self.scrape_senate_comm()
            # scrape joint committees under senate
            self.scrape_joint_comm()
        elif chamber == 'lower':
            self.scrape_reps_comm()

    def scrape_comm_list(self, ctype):
        url = 'http://webserver.rilin.state.ri.us/CommitteeMembers/'
        page = self._session.get(url).text
        root = lxml.html.fromstring(page)
        root.make_links_absolute(url)
        return root.xpath("//a[contains(@href,'"+ctype+"')]")

    def add_members(self,comm,url):
        # We do this twice because the first request should create the
        # session cookie we need.
        for x in range(2):
            page = self._session.get(url).text
        root = lxml.html.fromstring(page)
        # The first <tr> in the table of members
        membertable=root.xpath('//p[@class="style28"]/ancestor::table[1]')[0]
        members = membertable.xpath("*")[1:]

        order = {
            "name" : 0,
            "appt" : 1,
            "email" : 2
        }

        for member in members:
            name = member[order['name']].text_content().strip()
            name = name.replace("Senator","").replace("Representative","").strip()
            appt = member[order['appt']].text_content().strip()
            self.log("name "+ name +" role " + appt)
            comm.add_member(name, appt)

    def scrape_reps_comm(self):
        linklist = self.scrape_comm_list('ComMemr')
        if linklist is not None:
            for a in linklist:
                link=a.attrib['href']
                commName=clean(a.text_content())
                self.log("url "+ link)
                c=Committee('lower',commName)
                self.add_members(c,link)
                c.add_source(link)
                self.save_committee(c)

    def scrape_senate_comm(self):
        linklist = self.scrape_comm_list('ComMemS')
        if linklist is not None:
            for a in linklist:
                link=a.attrib['href']
                commName=clean(a.text_content())
                self.log( commName )
                if commName in COMM_BLACKLIST:
                    self.log( "XXX: Blacklisted" )
                    continue
                self.log("url "+link)
                c=Committee('upper',commName)
                self.add_members(c,link)
                c.add_source(link)
                self.save_committee(c)

    def scrape_joint_comm(self):
        linklist = self.scrape_comm_list('ComMemJ')
        if linklist is not None:
            for a in linklist:
                link=a.attrib['href']
                commName=clean(a.text_content())
                self.log("url "+link)
                c=Committee('joint',commName)
                self.add_members(c,link)
                c.add_source(link)
                self.save_committee(c)

