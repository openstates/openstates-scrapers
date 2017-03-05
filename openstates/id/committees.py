from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html


_COMMITTEE_URL = 'https://legislature.idaho.gov/committees/%scommittees/' # house/senate
_JOINT_URL = 'https://legislature.idaho.gov/sessioninfo/2017/joint/'

_CHAMBERS = {'upper':'senate', 'lower':'house'}
_REV_CHAMBERS = {'senate':'upper', 'house':'lower'}
_TD_ONE = ('committee', 'description', 'office_hours', 'secretary', 'office_email','office_phone')
_TD_TWO = ('committee', 'office_hours', 'secretary', 'office_email','office_phone')


def clean_name(name):
    return name.replace(u'\xa0', ' ')

class IDCommitteeScraper(CommitteeScraper):
    jurisdiction = 'id'

    def get_joint_committees_data(self,name,url):
        page = self.get(url).text
        html = lxml.html.fromstring(page)
        committee = Committee('joint', name)
        
        table=html.xpath("//section[@class=' row-equal-height no-padding']")
        for td in table:
            senate_members=td.xpath('div[1]/div/div/div[2]/div/p/strong')
            if(len(senate_members)>0):
                member_string=list(senate_members[0].itertext())
                if(len(member_string)>1):
                    name=member_string[0].replace('\r\n', ' ').replace(u'\xa0', ' ').replace("Sen.","").encode('ascii','ignore').strip()
                    role=member_string[1].replace('\r\n', ' ').replace(u'\xa0', ' ').replace(u',','').encode('ascii','ignore').strip()
                    committee.add_member(name,role=role,chamber='senate')
                else:
                    name=member_string[0].replace('\r\n', ' ').replace(u'\xa0', ' ').replace("Sen.","").encode('ascii','ignore').strip()
                    committee.add_member(name,chamber='senate')
            house_members=list(td.xpath('div[2]/div/div/div[2]/div/p/strong'))
            if(len(house_members)>0):
                member_string=list(house_members[0].itertext())
                if(len(member_string)>1):
                    name=member_string[0].replace('\r\n', ' ').replace(u'\xa0', ' ').replace(',', '').replace("Rep.","").encode('ascii','ignore').strip()
                    role=member_string[1].replace('\r\n', ' ').replace(u'\xa0', ' ').replace(u',','').encode('ascii','ignore').strip()
                    committee.add_member(name,role=role,chamber='house')
                else:
                    name=member_string[0].replace('\r\n', ' ').replace(u'\xa0', ' ').replace("Sen.","").encode('ascii','ignore').strip()
                    committee.add_member(name,chamber='house')
        committee.add_source(url)
        self.save_committee(committee)
    def scrape_committees(self, chamber):
        url = _COMMITTEE_URL % _CHAMBERS[chamber]
        page = self.get(url).text
        html = lxml.html.fromstring(page)
        table = html.xpath('body/section[2]/div/div/div/section[2]/div[2]/div/div/div/div')[1:]
        
        for row in table:
            # committee name, description, hours of operation,
            # secretary and office_phone
            text = list(row[0].xpath('div')[0].itertext())
            attributes= list(value.replace(u'\xa0', ' ').replace('Secretary:','').encode('ascii','ignore') for value in text if 'Email:' not in value and value!='\n' and 'Phone:' not in value) 
            for i in range(len(attributes)):
                if 'Room' in attributes[i]:
                    attributes[i]=attributes[i].split('Room')[0].replace(', ',' ')
            
            if len(attributes)>5:
                com = dict(zip(_TD_ONE, attributes))
            else:
                com = dict(zip(_TD_TWO, attributes))
            
            committee = Committee(chamber, **com)
            committee.add_source(url)

            # membership
            for td in row[1].xpath('div'):
                td_text = list(td.itertext())
                members=list(value for value in td_text if value!= ' ' and value!='\n' and value!=', ')
            role="member"
            for member in members:
                if (member in ['Chair','Vice Chair']):
                    role=member.lower()
                    continue
                else:
                    committee.add_member(member,role=role)
                    role="member"
            self.save_committee(committee)

    def scrape_joint_committees(self):
        
        page = self.get(_JOINT_URL).text
        html = lxml.html.fromstring(page)
        html.make_links_absolute(_JOINT_URL)
        joint_li = html.xpath('//div[contains(h2, "Joint")]/ul/li')
        for li in joint_li:
            name, url = li[0].text, li[0].get('href')
            
            self.get_joint_committees_data(name,url)

    def scrape(self, chamber, term):
        """
        Scrapes Idaho committees for the latest term.
        """
        self.validate_term(term, latest_only=True)

        self.scrape_committees(chamber)
        self.scrape_joint_committees()
