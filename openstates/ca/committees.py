'''
California has Joint Committees.
'''
import re
import pdb
from operator import methodcaller
import pprint

import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee 

strip = methodcaller('strip')

class CACommitteeScraper(CommitteeScraper):
    
    state = 'ca'
    encoding = 'utf-8'

    urls = {'upper': 'http://senate.ca.gov/committees',
            'lower': 'http://assembly.ca.gov/committees'}

    def scrape(self, chamber, term):

        url = self.urls[chamber]
        html = self.urlopen(url).decode(self.encoding)
        doc = lxml.html.fromstring(html)

        committee_types = {'upper': ['Standing', 'Select', 'Joint'],
                           'lower': ['Standing', 'Select']}

        for type_ in committee_types[chamber]:

            if type_ == 'Joint':
                chamber = type_.lower()

            div = doc.xpath('//div[contains(@class, "view-view-%sCommittee")]' % type_)[0]
            committees = div.xpath('descendant::span[@class="field-content"]/a/text()')
            committees = map(strip, committees)
            urls = div.xpath('descendant::span[@class="field-content"]/a/@href')

            for c, _url in zip(committees, urls):
                
                if c.endswith('Committee'):
                    c = '%s %s' % (type_, c)
                else:
                    c = '%s Committee on %s' % (type_, c)
                    
                c = Committee(chamber, c)
                c.add_source(_url)
                c.add_source(url)
                scrape_members = getattr(self, 'scrape_%s_members' % chamber.lower())
                c = scrape_members(c, _url, chamber, term)

                self.save_committee(c)

                
        # Subcommittees
        div = doc.xpath('//div[contains(@class, "view-view-SubCommittee")]')[0]
        for subcom in div.xpath('div/div[@class="item-list"]'):
            committee = subcom.xpath('h4/text()')
            names = subcom.xpath('descendant::a/text()')
            names = map(strip, names)
            urls = subcom.xpath('descendant::a/@href')
            for n, _url in zip(names, urls):
                c = Committee(chamber, n)
                c.add_source(_url)
                c.add_source(url)
                scrape_members = getattr(self, 'scrape_%s_members' % chamber.lower())
                c = scrape_members(c, _url, chamber, term)
                
                #pprint.pprint(c)
                self.save_committee(c)

    def scrape_lower_members(self, committee, url, chamber, term,
        re_name=re.compile(r'^(Senator|Assemblymember)'),):

        try:
            # Some committees display the members @ /memberstaff
            html = self.urlopen(url + '/membersstaff')
        except:
            # Others display the members table on the homepage.
            html = self.urlopen(url)

        html = html.decode(self.encoding)
        doc = lxml.html.fromstring(html)
        members = doc.xpath('//table/descendant::td/a/text()')
        members = map(strip, members)
        members = filter(None, members)[::2]


        if not members:
            self.warning('Dind\'t find any committe members at url: %s' % url)
        
        for member in members:
            
            if ' - ' in member:
                member, role = member.split(' - ')
            else:
                role = 'member'
            
            member = re_name.sub('', member)
            member = member.strip()
            committee.add_member(member, role)
            
        return committee
        

    def scrape_upper_members(self, committee, url, chamber, term,
        re_name=re.compile(r'^(Senator|Assemblymember)'),
        roles=[re.compile(r'(.+?)\s+\((.+?)\)'),
               re.compile(r'(.+?),\s+(.+)')]):

        html = self.urlopen(url).decode(self.encoding)
        doc = lxml.html.fromstring(html)

        if url == 'http://autism.senate.ca.gov':
            members = doc.xpath('//h2[contains(., "Member Roster")]/'
                                'following-sibling::ul[1]/descendant::strong')
            members = [e.text_content() for e in members]
        else:
            members = doc.xpath('//h2[contains(., "Members")]/'
                                'following-sibling::p[1]/descendant::a/text()')
        members = map(strip, members)

        if not members:
            self.warning('Didn\'t find any committe members at url: %s' % url)

        for member in members:
            role = 'member'
            for rgx in roles:
                m = rgx.match(member)
                if m:
                    member, role = m.groups()

            kw = {}
            for s, ch in (('Senator', 'upper'),
                          ('Assemblymember', 'lower')):
                if s in member:
                    kw = {'chamber': ch}
            member = re_name.sub('', member)
            member = member.strip()
                    
            committee.add_member(member, role, **kw)

        return committee

    # The same selections work on both upper chamber comm's and joint comm's.
    scrape_joint_members = scrape_upper_members
        
        
