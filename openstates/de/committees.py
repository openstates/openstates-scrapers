import re
import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin

class DECommitteeScraper(CommitteeScraper,LXMLMixin):
    jurisdiction = "de"

    def scrape(self, chamber, term):
        urls = {
            'upper': 'http://legis.delaware.gov/json/Committees/' +
                     'GetCommitteesByTypeId?assemblyId=%s&committeeTypeId=1',
            'lower': 'http://legis.delaware.gov/json/Committees/' +
                     'GetCommitteesByTypeId?assemblyId=%s&committeeTypeId=2',
        }

        # Mapping of term names to session numbers (see metatdata).
        term2session = {"2017-2018": "149", "2015-2016": "148",
                        "2013-2014": "147", "2011-2012": "146",
                        "2009-2010": "145", "2007-2008": "144",
                        "2005-2006": "143", "2003-2004": "142",
                        "2001-2002": "141", "1999-2000": "140"}

        session = term2session[term]

        if chamber == 'lower':
            #only scrape joint comms once
            self.scrape_joint_committees(term,session)

        url = urls[chamber] % (session,)
        data = self.post(url).json()['Data']

        for item in data:
            committee = Committee(chamber, item['CommitteeName'])
            chair_man = str(item.get('ChairName', 'No'))
            vice_chair = str(item.get('ViceChairName', 'No'))
            comm_id = item['CommitteeId']
            comm_url = 'http://legis.delaware.gov/CommitteeDetail?' + \
                        'committeeId='+ str(comm_id)
            comm_page = lxml.html.fromstring(self.get(comm_url).text)
            #all members including chair_man and vice_chair
            members = comm_page.xpath("//section[@class='section-short']/" + \
                                      "div[@class='info-horizontal']/div" + \
                                      "[@class='info-group']/div[@class" + \
                                      "='info-value']/a/text()")

            committee.add_member(chair_man,'Chairman')
            committee.add_member(vice_chair,'Vice-Chair')
            for member in members:
                #vice_chair and chair_man already added.
                if chair_man not in member and vice_chair not in member:
                    committee.add_member(member)

            committee.add_source(comm_url)
            committee.add_source(url)

            self.save_committee(committee)


    def scrape_joint_committees(self,term,session):
        url = 'http://legis.delaware.gov/json/Committees/' + \
              'GetCommitteesByTypeId?assemblyId=%s&committeeTypeId=3'%(session,)
        data = self.post(url).json()['Data']

        for item in data:
            comm_name = item['CommitteeName']
            committee = Committee('joint', comm_name)
            chair_man = str(item.get('ChairName', 'No'))
            vice_chair = str(item.get('ViceChairName', 'No'))
            #only Sunset url is not following pattern.
            if comm_name == 'Joint Legislative Oversight and Sunset Committee':
                comm_url = 'http://legis.delaware.gov/Sunset'
            else:
                comm_url = 'http://legis.delaware.gov/' + "".join(comm_name.split())

            comm_page = lxml.html.fromstring(self.get(comm_url).text)
            #all members including chair_man and vice_chair
            members = comm_page.xpath("//section[@class='section-short']/" + \
                                      "div[@class='info-horizontal']/div" + \
                                      "[@class='info-group']/div[@class" + \
                                      "='info-value']//a/text()")

            committee.add_member(chair_man,'Chairman')
            committee.add_member(vice_chair,'Vice-Chair')

            for member in members:
                #vice_chair and chair_man already added.
                if chair_man not in member and vice_chair not in member:
                    committee.add_member(member)

            committee.add_source(comm_url)
            committee.add_source(url)
            self.save_committee(committee)
