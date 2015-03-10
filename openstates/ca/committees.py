# -*- coding: utf-8 -*-
import re
import collections
from operator import methodcaller

import lxml.html
import scrapelib
import requests.exceptions

from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin
from .utils import Urls


strip = methodcaller('strip')


def clean(s):
    s = s.strip(u'\xa0 \n\t').replace(u'\xa0', ' ')
    s = re.sub(r'[\s+\xa0]', ' ', s)
    return s.strip()


class CACommitteeScraper(CommitteeScraper, LXMLMixin):

    jurisdiction = 'ca'

    urls = {'upper': 'http://senate.ca.gov/committees',
            'lower': 'http://assembly.ca.gov/committees'}

    base_urls = {'upper': 'http://senate.ca.gov/',
                 'lower': 'http://assembly.ca.gov/'}

    def scrape(self, chamber, term):
        #as of 1/26, committees seem to be in place!
        #raise Exception("CA Committees aren't in place yet")

        if chamber == 'lower':
            self.scrape_lower(chamber, term)
        elif chamber == 'upper':
            # Also captures joint committees
            self.scrape_upper(chamber, term)


    def scrape_lower(self, chamber, term):
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

            for xpath in [
                '//div[contains(@class, "view-view-%sCommittee")]' % type_,
                '//div[contains(@id, "block-views-view_StandingCommittee-block_1")]',
                '//div[contains(@class, "views-field-title")]',
                ]:
                div = doc.xpath(xpath)
                if div:
                    break

            div = div[0]
            committees = div.xpath('descendant::span[@class="field-content"]/a/text()')
            committees = map(strip, committees)
            urls = div.xpath('descendant::span[@class="field-content"]/a/@href')

            for c, _url in zip(committees, urls):

                if 'autism' in _url:
                    # The autism page takes a stunning 10 minutes to respond
                    # with a 403. Skip it.
                    continue

                if c.endswith('Committee'):
                    if type_ not in c:
                        c = '%s %s' % (type_, c)
                elif ('Subcommittee' not in c and 'Committee on' not in c):
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
                    # Some committees weren't staff in early
                    # 2013; opting to skip rather than blow
                    # up the whole scrape.
                    return
                    cname = c['committee']
                    msg = '%r must have at least one member.'
                    raise ValueError(msg % cname)

                if c['members']:
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
                    # Some committees weren't staff in early
                    # 2013; opting to skip rather than blow
                    # up the whole scrape.
                    return
                    cname = c['committee']
                    msg = '%r must have at least one member.'
                    raise ValueError(msg % cname)

                if c['members']:
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
        except (scrapelib.HTTPError, requests.exceptions.ConnectionError):
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
        committee_names = filter(None, map(clean, committee_names))
        for _committee, _names in zip(committee_names, namelists):
            if _committee:
                cache[_committee] = _names

        names = cache[committee['subcommittee']]
        return Membernames.scrub(names)

    def scrape_upper(self, chamber, term):
        url = 'http://senate.ca.gov/committees'
        doc = self.lxmlize(url)

        standing_committees = doc.xpath(
            '//h2[text()="Standing Committees"]/../following-sibling::div//a')
        sub_committees = doc.xpath(
            '//h2[text()="Sub Committees"]/../following-sibling::div//a')
        joint_committees = doc.xpath(
            '//h2[text()="Joint Committees"]/../following-sibling::div//a')
        other_committees = doc.xpath(
            '//h2[text()="Other"]/../following-sibling::div//a')

        for committee in (standing_committees + sub_committees +
                          joint_committees + other_committees):
            (comm_name, ) = committee.xpath('text()')
            comm = Committee(
                chamber=chamber,
                committee=comm_name
            )

            (comm_url, ) = committee.xpath('@href')
            comm.add_source(comm_url)
            comm_doc = self.lxmlize(comm_url)

            if comm_name.startswith("Joint"):
                comm['chamber'] = 'joint'
                comm['committee'] = (comm_name.
                                     replace("Joint ", "").
                                     replace("Committee on ", "").
                                     replace(" Committee", ""))

            if comm_name.startswith("Subcommittee"):
                (full_comm_name, ) = comm_doc.xpath(
                    '//div[@class="banner-sitename"]/a/text()')
                full_comm_name = re.search(
                    r'^Senate (.*) Committee$', full_comm_name).group(1)
                comm['committee'] = full_comm_name

                comm_name = re.search(
                    r'^Subcommittee.*?on (.*)$', comm_name).group(1)
                comm['subcommittee'] = comm_name

            members = comm_doc.xpath(
                '//a[(contains(@href, "/sd") or '
                'contains(@href, "assembly.ca.gov/a")) and '
                '(starts-with(text(), "Senator") or '
                'starts-with(text(), "Assembly Member"))]/text()')
            for member in members:
                if not member.strip():
                    continue

                (mem_name, mem_role) = re.search(r'''(?ux)
                    ^(?:Senator|Assembly\sMember)\s  # Legislator title
                    (.+?)  # Capture the senator's full name
                    (?:\s\((.{2,}?)\))?  # There may be role in parentheses
                    (?:\s\([RD]\))?  # There may be a party affiliation
                    \s*$
                    ''', member).groups()
                comm.add_member(
                    legislator=mem_name,
                    role=mem_role if mem_role else 'member'
                )

            assert comm['members'], "No members found for committee {}".format(
                comm_name)
            self.save_committee(comm)


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
                     r'(.+?),\s+(?![III])(.+)',
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

            # Special case for Isadore hall. This entire hot mess needs
            # a re-write at some point.
            if role == 'III':
                role = 'member'

            kw = {}
            for s, ch in (('Senator', 'upper'),
                          ('Assemblymember', 'lower')):
                if s in name:
                    kw = {'chamber': ch}
            name = re.sub(r'^(Senator|Assemblymember)', '', name)
            name = name.strip()

            if name:
                if 'Sanator' in name:
                    name = name.replace('Sanator', 'Senator')
                if name.endswith(' (Chair'):
                    role = 'chair'
                    name = name.replace(' (Chair', '')
                name.strip(',').strip()
                res.append((name, role, kw))

        return res
