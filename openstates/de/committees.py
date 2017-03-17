import re
import lxml.html
from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin


class DECommitteeScraper(CommitteeScraper, LXMLMixin):
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
            # only scrape joint comms once
            self.scrape_joint_committees(session)

        # scrap upper and lower committees
        url = urls[chamber] % (session,)
        self.scrape_comm(url, chamber)

    def scrape_comm(self, url, chamber):
        data = self.post(url).json()['Data']

        for item in data:
            comm_name = item['CommitteeName']
            committee = Committee(chamber, comm_name)
            chair_man = str(item['ChairName'])
            vice_chair = str(item['ViceChairName'])
            comm_id = item['CommitteeId']
            comm_url = self.get_comm_url(chamber, comm_id, comm_name)
            members = self.scrape_member_info(comm_url)
            if vice_chair != 'None':
                committee.add_member(vice_chair, 'Vice-Chair')
            if chair_man  != 'None':
                committee.add_member(chair_man, 'Chairman')


            for member in members:
                # vice_chair and chair_man already added.
                if chair_man not in member and vice_chair not in member:
                    member = " ".join(member.split())
                    if member:
                        committee.add_member(member)

            committee.add_source(comm_url)
            committee.add_source(url)
            self.save_committee(committee)

    def scrape_joint_committees(self, session):
        chamber = 'joint'
        url = 'http://legis.delaware.gov/json/Committees/' + \
              'GetCommitteesByTypeId?assemblyId=%s&committeeTypeId=3' % (session, )
        self.scrape_comm(url, chamber)

    def scrape_member_info(self, comm_url):
        comm_page = lxml.html.fromstring(self.get(comm_url).text)
        # all members including chair_man and vice_chair
        members = comm_page.xpath("//section[@class='section-short']/div[@class='info" +
                                  "-horizontal']/div[@class='info-group']/div[@class=" +
                                  "'info-value']//a/text()")
        return members

    def get_comm_url(self, chamber, comm_id, comm_name):
        if chamber == 'joint':
            # only Sunset url is not following pattern.
            if comm_name == 'Joint Legislative Oversight and Sunset Committee':
                comm_url = 'http://legis.delaware.gov/Sunset'
            else:
                comm_url = 'http://legis.delaware.gov/' + "".join(comm_name.split())
        else:
            comm_url = 'http://legis.delaware.gov/CommitteeDetail?committeeId=' + str(comm_id)
        return comm_url
