# -*- coding: utf-8 -*-
import re
import collections
from operator import methodcaller

import lxml.html

import scrapelib
from billy.scrape.committees import CommitteeScraper, Committee


strip = methodcaller('strip')

# Committee codes used in action chamber text.
upper_committee_codes = [
    ('CZ09', 'Standing Committee on Floor Analyses'),
    ('CS73', 'Standing Committee on Governance and Finance'),
    ('CS71', 'Standing Committee on Energy, Utilities and Communications'),
    ('CS44', 'Standing Committee on Education'),
    ('CS61', 'Standing Committee on Appropriations'),
    ('CS51', 'Standing Committee on Labor and Industrial Relations'),
    ('CS45', 'Standing Committee on Elections and Constitutional Amendments'),
    ('CS64', 'Standing Committee on Environmental Quality'),
    ('CS55', 'Standing Committee on Natural Resources And Water'),
    ('CS56', 'Standing Committee on Public Employment and Retirement'),
    ('CS48', 'Standing Committee on Governmental Organization'),
    ('CS70', 'Standing Committee on Insurance'),
    ('CS72', 'Standing Committee on Public Safety'),
    ('CS53', 'Standing Committee on Judiciary'),
    ('CS60', 'Standing Committee on Health'),
    ('CS59', 'Standing Committee on Transportation and Housing'),
    ('CS42',
    'Standing Committee on Business, Professions and Economic Development'),
    ('CS40', 'Standing Committee on Agriculture'),
    ('CS69', 'Standing Committee on Banking and Financial Institutions'),
    ('CS66', 'Standing Committee on Veterans Affairs'),
    ('CS62', 'Standing Committee on Budget and Fiscal Review'),
    ('CS74', 'Standing Committee on Human Services'),
    ('CS58', 'Standing Committee on Rules')
    ]

lower_committee_codes = [
    ('CX20', 'standing committee on rules'),
    ('CZ01', 'assembly floor analysis'),
    ('CX19', 'standing committee on revenue and taxation'),
    ('CX16', 'standing committee on natural resources'),
    ('CX25', 'standing committee on appropriations'),
    ('CX28', 'standing committee on insurance'),
    ('CX23', 'standing committee on utilities and commerce'),
    ('CX03', 'standing committee on education'),
    ('CX18', 'standing committee on public safety'),
    ('CX04', 'standing committee on elections and redistricting'),
    ('CX13', 'standing committee on judiciary'),
    ('CX09', 'standing committee on higher education'),
    ('CX08', 'standing committee on health'),
    ('CX11', 'standing committee on human services'),
    ('CX37',
    'standing committee on arts, entertainment, sports, tourism, and internet media'),
    ('CX22', 'standing committee on transportation'),
    ('CX33',
    'standing committee on business, professions and consumer protection'),
    ('CX24', 'standing committee on water, parks and wildlife'),
    ('CX15', 'standing committee on local government'),
    ('CX31', 'standing committee on aging and long term care'),
    ('CX14', 'standing committee on labor and employment'),
    ('CX07', 'standing committee on governmental organization'),
    ('CX17',
    'standing committee on public employees, retirement and social security'),
    ('CX38', 'standing committee on veterans affairs'),
    ('CX10', 'standing committee on housing and community development'),
    ('CX05', 'standing committee on environmental safety and toxic materials'),
    ('CX01', 'standing committee on agriculture'),
    ('CX27', 'standing committee on banking and finance'),
    ('CX34', 'standing committee on jobs, economic development and the economy'),
    ('CX02', 'standing committee on accountability and administrative review'),
    ('CX29', 'standing committee on budget')
    ]


codes = {
    'upper': dict((name.lower(), code)
                  for (code, name) in upper_committee_codes),
    'lower': dict((name.lower(), code)
                  for (code, name) in lower_committee_codes)
}


def clean(s):
    '''You filthy string, you.'''
    return s.strip(u'\xa0 \n\t').replace(u'\xa0', ' ')


class CACommitteeScraper(CommitteeScraper):

    state = 'ca'

    urls = {'upper': 'http://senate.ca.gov/committees',
            'lower': 'http://assembly.ca.gov/committees'}

    base_urls = {'upper': 'http://senate.ca.gov/',
                 'lower': 'http://assembly.ca.gov/'}

    def scrape(self, chamber, term):
        url = self.urls[chamber]
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(self.base_urls[chamber])

        committee_types = {'upper': ['Standing', 'Select', 'Joint'],
                           'lower': ['Standing', 'Select']}

        for type_ in committee_types[chamber]:

            if type_ == 'Joint':
                _chamber = type_.lower()
            else:
                _chamber = chamber

            div = doc.xpath('//div[contains(@class, "view-view-%sCommittee")]' % type_)[0]
            committees = div.xpath('descendant::span[@class="field-content"]/a/text()')
            committees = map(strip, committees)
            urls = div.xpath('descendant::span[@class="field-content"]/a/@href')

            for c, _url in zip(committees, urls):
                if c.endswith('Committee'):
                    if type_ not in c:
                        c = '%s %s' % (type_, c)
                elif ('Subcommittee' not in c):
                    c = '%s Committee on %s' % (type_, c)
                else:
                    if type_ not in c:
                        c = '%s %s' % (type_, c)

                c = Committee(_chamber, c)
                c.add_source(_url)
                c.add_source(url)
                for member, role, kw in self.scrape_membernames(c, _url,
                        chamber, term):
                    c.add_member(member, role, **kw)

                _found = False
                if len(c['members']) == 0:
                    for member, role, kw in self.scrape_membernames(c,
                            _url + '/membersstaff', chamber, term):
                        _found = True
                        c.add_member(member, role, **kw)
                    if _found:
                        source = _url + '/membersstaff'
                        c.add_source(source)

                if len(c['members']) == 0:
                    cname = c['committee']
                    msg = '%r must have at least one member.'
                    raise ValueError(msg % cname)

                code = codes[chamber].get(c['committee'].lower())
                c['action_code'] = code

                self.save_committee(c)

        # Subcommittees
        div = doc.xpath('//div[contains(@class, "view-view-SubCommittee")]')[0]
        for subcom in div.xpath('div/div[@class="item-list"]'):
            committee = subcom.xpath('h4/text()')[0]
            names = subcom.xpath('descendant::a/text()')
            names = map(strip, names)
            urls = subcom.xpath('descendant::a/@href')
            committee = 'Standing Committee on ' + committee
            for n, _url in zip(names, urls):
                c = Committee(chamber, committee, subcommittee=n)
                c.add_source(_url)
                c.add_source(url)

                for member, role, kw in self.scrape_membernames(c, _url,
                        chamber, term):
                    c.add_member(member, role, **kw)

                _found = False
                if len(c['members']) == 0:
                    for member, role, kw in self.scrape_membernames(c,
                            _url + '/membersstaff', chamber, term):
                        _found = True
                        c.add_member(member, role, **kw)
                    if _found:
                        source = _url + '/membersstaff'
                        c.add_source(source)

                if len(c['members']) == 0:
                    cname = c['committee']
                    msg = '%r must have at least one member.'
                    raise ValueError(msg % cname)

                self.save_committee(c)

    def scrape_membernames(self, committee, url, chamber, term):
        '''Scrape the member names from this page.
        '''

        # Special-case senate subcomittees.
        if url == 'http://sbud.senate.ca.gov/subcommittees1':
            return self.scrape_members_senate_subcommittees(
                committee, url, chamber, term)

        # Many of the urls don't actually display members. Swap them for ones
        # that do.
        corrected_urls = (('http://autism.senate.ca.gov',
                 'http://autism.senate.ca.gov/committeemembers1'),

                ('Sub Committee on Sustainable School Facilities',
                 'http://sedn.senate.ca.gov/substainableschoolfacilities'),

                ('Sustainable School Facilities',
                 'http://sedn.senate.ca.gov/substainableschoolfacilities'),

                ('Sub Committee on Education Policy Research',
                 'http://sedn.senate.ca.gov/policyresearch'),

                ('Education Policy Research',
                 'http://sedn.senate.ca.gov/policyresearch'))

        corrected_urls = dict(corrected_urls)

        cname = committee['subcommittee']
        for key in url, cname:
            if key in corrected_urls:
                url = corrected_urls[key]
                #committee['sources'].pop()
                committee.add_source(url)
                break

        # Now actually try to get the names.
        try:
            html = self.urlopen(url)
        except scrapelib.HTTPError:
            self.warning('Bogus committee page link: %r' % url)
            return []

        doc = lxml.html.fromstring(html)

        links = doc.xpath('//a')
        names = Membernames.extract(links)
        names = Membernames.scrub(names)
        return names

    def scrape_members_senate_subcommittees(self, committee, url, chamber,
                                            term, cache={}):

        if cache:
            names = cache[committee['subcommittee']]
            return Membernames.scrub(names)

        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)

        # Commence horrific regex-based hackery to get subcommittee members.
        text = doc.xpath('//div[@class="content"]')[0].text_content()
        chunks = re.split(r'\s*Subcommittee.*', text)
        namelists = []
        for c in chunks:
            names = re.sub(r'\s*Members\s*', '', c)
            names = re.split(r'\s*(,|and)\s*', names)
            names = filter(lambda s: s not in [',', 'and'], names)
            names = map(clean, names)
            if filter(None, names):
                namelists.append(names)

        committee_names = doc.xpath('//div[@class="content"]/h3/text()')
        for _committee, _names in zip(map(clean, committee_names), namelists):
            cache[_committee] = _names

        names = cache[committee['subcommittee']]
        return Membernames.scrub(names)


class Membernames(object):

    @staticmethod
    def extract(links):
        '''Given an lxml.xpath result, extract a list of member names.
        '''
        href_rgxs = (r'(sd|a)\d+\.(senate|assembly)\.ca\.gov/$',
                     r'(senate|assembly)\.ca\.gov/(sd|a)\d+$',
                     r'(sd|a)\d+$',
                     r'dist\d+[.]',
                     r'cssrc[.]us/web/\d+',
                     r'/Wagner')

        res = collections.defaultdict(list)
        for a in links:
            try:
                href = a.attrib['href']
            except KeyError:
                continue
            for rgx in href_rgxs:
                if re.search(rgx, href, re.M):
                    res[href].append(a.text_content().strip())
        vals = [' '.join(set(lst)) for lst in res.values()]
        return [re.sub('\s+', ' ', s) for s in vals]

    @staticmethod
    def scrub(names):
        '''Separate names from roles and chambers, etc.
        '''
        role_rgxs = [r'(.+?)\s+\((.+?)\)',
                     r'(.+?),\s+(?![JS]r.)(.+)',
                     ur'(.+?)\s*[-–]\s+(.+)']

        res = []
        for name in names:
            name = clean(name)

            role = 'member'
            for rgx in role_rgxs:
                m = re.match(rgx, name)
                if m:
                    name, role = m.groups()
                    break

            kw = {}
            for s, ch in (('Senator', 'upper'),
                          ('Assemblymember', 'lower')):
                if s in name:
                    kw = {'chamber': ch}
            name = re.sub(r'^(Senator|Assemblymember)', '', name)
            name = name.strip()

            if name:
                if 'Sanator' in  name:
                    name = name.replace('Sanator', 'Senator')
                name.strip(',')
                res.append((name, role, kw))

        return res
