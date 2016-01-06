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
        html = self.get(url).text
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

                c = c.replace("Committee on ", "").replace(" Committee", "")
                c = Committee(_chamber, c)
                self.info(u'Saving {} committee.'.format(c['committee']))
                c.add_source(_url)
                c.add_source(url)
                for member, role in self.scrape_lower_members(_url):
                    c.add_member(member, role)

                _found = False
                if not c['members']:
                    try:
                        for member, role in self.scrape_lower_members(
                                _url + '/membersstaff'):
                            _found = True
                            c.add_member(member, role)
                        if _found:
                            source = _url + '/membersstaff'
                            c.add_source(source)
                    except requests.exceptions.HTTPError:
                        self.error(u"Unable to access member list for {} "
                            "committee.".format(c['committee']))

                if c['members']:
                    self.save_committee(c)
                else:
                    self.warning(u"No members found for {} committee."
                        .format(c['committee']))

        # Subcommittees
        div = doc.xpath('//div[contains(@class, "view-view-SubCommittee")]')[0]
        for subcom in div.xpath('div/div[@class="item-list"]'):
            committee = self.get_node(subcom, 'h4/text()')

            if committee is None:
                continue

            names = subcom.xpath('descendant::a/text()')
            names = map(strip, names)
            urls = subcom.xpath('descendant::a/@href')
            for n, _url in zip(names, urls):
                n = re.search(r'^Subcommittee.*?on (.*)$', n).group(1)
                c = Committee(chamber, committee, subcommittee=n)
                c.add_source(_url)
                c.add_source(url)

                for member, role in self.scrape_lower_members(_url):
                    c.add_member(member, role)

                _found = False
                if not c['members']:
                    try:
                        for member, role in self.scrape_lower_members(
                            _url + '/membersstaff'):
                            _found = True
                            c.add_member(member, role)
                        if _found:
                            source = _url + '/membersstaff'
                            c.add_source(source)
                    except requests.exceptions.HTTPError:
                        self.error(u"Unable to access member list for {} subcommittee."
                            .format(c['subcommittee']))

                if c['members']:
                    self.save_committee(c)
                else:
                    self.warning(u"No members found for {} subcommittee of {} "
                        "committee".format(c['subcommittee'], c['committee']))

    def scrape_lower_members(self, url):
        ''' Scrape the members from this page. '''

        doc = self.lxmlize(url)
        members = doc.xpath(
            '//table/thead/tr//*[contains(text(), "Committee Members")]/'
            'ancestor::table//tr/td[1]/a/text()')

        for member in members:
            (mem_name, mem_role) = re.search(r'''(?ux)
                    ^\s*(.+?)  # Capture the senator's full name
                    (?:\s\((.{2,}?)\))?  # There may be role in parentheses
                    \s*$
                    ''', member).groups()
            if not mem_role:
                mem_role = "member"
            yield (mem_name, mem_role)

    def scrape_upper(self, chamber, term):
        # Retrieve index list of committees.
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

        # Iterates over each committee [link] found.
        for committee in (standing_committees + sub_committees +
                          joint_committees + other_committees):
            # Get the text of the committee link, which should be the name of
            # the committee.
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

            # Special case of members list being presented in text blob.
            member_blob = comm_doc.xpath(
                'string(//div[contains(@class, "field-item") and '
                'starts-with(text(), "Senate Membership:")][1]/text()[1])')

            if member_blob:
                # Separate senate membership from assembly membership.
                # This should strip the header from assembly membership
                # string automatically.
                delimiter = 'Assembly Membership:\n'
                senate_members, delimiter, assembly_members = \
                    member_blob.partition(delimiter)

                # Strip header from senate membership string.
                senate_members = senate_members.replace('Senate Membership:\n', '')

                # Clean membership strings.
                senate_members = senate_members.strip()
                assembly_members = assembly_members.strip()

                # Parse membership strings into lists.
                senate_members = senate_members.split('\n')
                assembly_members = assembly_members.split('\n')

                members = senate_members + assembly_members
            # Typical membership list format.
            else:
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
