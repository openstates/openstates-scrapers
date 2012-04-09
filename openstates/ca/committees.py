'''
California has Joint Committees.
'''
import re
import pdb
from operator import methodcaller
import pprint

import lxml.html

import scrapelib
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

        committee_types = {'upper': ['Standing', 'Select', 'Sub', 'Joint'],
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
                    if 'Subcommittee' not in c:
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

        for member, role, kw in self.scrape_membernames(committee, url, chamber, term):
            committee.add_member(member, role, **kw)

        if len(committee['members']) == 0:
            for member, role, kw in self.scrape_membernames(committee, 
                    url + '/membersstaff', chamber, term):
                committee.add_member(member, role, **kw)

        if len(committee['members']) == 0:
            import pdb
            pdb.set_trace()

        return committee
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

        for member, role, kw in self.scrape_membernames(committee, url, chamber, term):
            committee.add_member(member, role, **kw)

        if len(committee['members']) == 0:
            for member, role, kw in self.scrape_membernames(committee, 
                    url + '/membersstaff', chamber, term):
                committee.add_member(member, role, **kw)

        if len(committee['members']) == 0:
            import pdb
            pdb.set_trace()
        return committee

    # The same selections work on both upper chamber comm's and joint comm's.
    scrape_joint_members = scrape_upper_members

    def scrape_membernames_generic(self, doc):
        names = doc.xpath('//a/text()')
        names = filter(lambda n: 'Senator' in n, names)
        return names

    def scrape_membernames_senate_autism(self, committee, url, chamber, term):
        '''The Senate Autism committee has its own wierd format.
        '''
        url = 'http://autism.senate.ca.gov/committeemembers1'
        html = self.urlopen(url)
        html = html.decode(self.encoding)
        doc = lxml.html.fromstring(html)
        return self.scrape_membernames_generic(doc)

    def scrape_senate_sedn_subs(committee, url, chamber, term):
         links = doc.xpath('//div[@class="content"]')[0].xpath('descendant::a')

    def scrape_membernames(self, committee, url, chamber, term):
        '''Scrape the member names from this page. 
        '''
        href_rgxs = (r'(sd|a)\d+$',
                     r'dist\d+[.]',
                     r'cssrc[.]us/web/\d+')

        if url == 'http://sbud.senate.ca.gov/subcommittees1':
            return self.scrape_members_senate_subcommittees(
                committee, url, chamber, term)

        urls = (('http://autism.senate.ca.gov', 
                 'http://autism.senate.ca.gov/committeemembers1'),)

        urls = dict(urls)

        if url in urls:
            self.warning('swapping url!')
            url = urls.get(url, url)

        try:
            html = self.urlopen(url)
        except scrapelib.HTTPError:
            self.warning('Bogus committee page link: %r' % url)
            return []

        html = html.decode(self.encoding)
        doc = lxml.html.fromstring(html)

        names = Membernames.extract(doc.xpath('//a'))
        names = Membernames.scrub(names)
        return names

    def scrape_members_senate_subcommittees(self, committee, url, chamber, term, cache={}):

        if cache:
            pdb.set_trace()
            return 

        html = self.urlopen(url)
        html = html.decode(self.encoding)
        doc = lxml.html.fromstring(html)

        def nwise(n, iterable):
            it = iter(iterable)
            _n = range(n)
            while True:
                res = []
                for _ in _n:
                    try:
                        res.append(next(it))
                    except StopIteration:
                        return
                yield res

        for h3, h5, p in nwise(3, doc.xpath('//div[@class="content"]')[0]):
            _committee = h3.text_content().strip()
            names = Membernames.extract(h5.xpath('a'))
            names = list(Membernames.scrub(names))
            cache[_committee] = names
            pdb.set_trace()



class Membernames(object):

    @staticmethod
    def extract(links):
        '''Given an lxml.xpath result, extract a list of member names.
        '''
        href_rgxs = (r'(sd|a)\d+$',
             r'dist\d+[.]',
             r'cssrc[.]us/web/\d+')

        for a in links:
            try:
                href = a.attrib['href']
            except KeyError:
                continue
            for rgx in href_rgxs:
                if re.search(rgx, href, re.M):
                    yield a.text_content()

    @staticmethod
    def scrub(names):
        '''Separate names from roles and chambers, etc. 
        '''
        role_rgxs = [r'(.+?)\s+\((.+?)\)',
                     r'(.+?),\s+(.+)']
        
        for name in names:
            role = 'member'
            for rgx in role_rgxs:
                m = re.match(rgx, name)
                if m:
                    name, role = m.groups()

            kw = {}
            for s, ch in (('Senator', 'upper'),
                          ('Assemblymember', 'lower')):
                if s in name:
                    kw = {'chamber': ch}
            name = re.sub(r'^(Senator|Assemblymember)', '', name)
            name = name.strip()

            print '  ', name, role, kw
            if name:
                yield name, role, kw