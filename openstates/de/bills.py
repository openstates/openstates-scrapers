import re
import itertools
from urlparse import urlparse
from datetime import datetime
from operator import methodcaller
from functools import partial


import lxml.html

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
import scrapelib

import actions


class BillIdParseError(ScrapeError):
    '''
    Raised when function `parse_bill_id` returns a string that
    doesn't remotely resmble a valid bill_id.
    '''
    pass


def get_text(doc, i, xpath):
    '''
    A shortcut to get stripped text content given 1) a document of
    type lxml.html.HtmlElement, 2) an xpath, and 3) optionaly
    an index `i` that defaults to zero.
    '''
    if not i:
        i = 0
    return doc.xpath(xpath)[i].text_content().strip()


def slugify(s):
    '''
    Turn a phrase like "Current Status:" into "current_status".
    '''
    return s.lower().replace(' ', '_').rstrip(':')


def parse_votestring(v, strptime=datetime.strptime,
    re_date=re.compile('\d{,2}/\d{,2}/\d{,4} [\d:]{,8} [AP]M'),
    chambers={'House': 'lower', 'Senate': 'upper'}):
    '''
    Parse contents of the string on the main bill detail page
    describing a vote.
    '''
    motion, _ = v.split(':', 1)
    motion = motion.strip()

    m = re_date.search(v)
    date = strptime(m.group(), '%m/%d/%Y %I:%M:%S %p')

    chamber, _ = v.split(' ', 1)
    chamber = chambers[chamber.strip()]

    passed = ('Passed' in v)

    return dict(date=date, chamber=chamber, passed=passed, motion=motion)


def extract_bill_id(bill_id, fns=(
    partial(re.compile(r'( w/.A \d{1,3}.{,200},?)+$', re.I).sub, ''),
    partial(re.compile(r'^.{,20}for ', re.I).sub, '')),
    is_valid=re.compile(r'[A-Z]{2,4} \d{1,6}$').match):
    '''
    Given a bill id string from the website's index pages, removes
    characters indicating amendments and substitutions, e.g.:

        SB 137 w/SA 1 --> SB 137
        SB 112 w/SA 1 + HA 1 --> SB 112
        SS 1 for SB 156 --> SB 156

    Complains if the result doesn't look like a normal bill id.
    '''
    _bill_id = bill_id

    for f in fns:
        bill_id = f(bill_id)

    if not is_valid(bill_id):
        msg = 'Not a valid bill id: "%s" ' % _bill_id
        raise BillIdParseError(msg)

    return bill_id


class DEBillScraper(BillScraper):
    '''
    Scrapes bills for the current session. Delware's website
    (http://legis.delaware.gov/) lists archival data separately and
    with a different (though similar) format.
    See http://legis.delaware.gov/LEGISLATURE.NSF/LookUp/LIS_archives?opendocument
    '''

    jurisdiction = 'de'

    categorizer = actions.Categorizer()

    legislation_types = {
        'House Bill': 'bill',
        'House Concurrent Resolution': 'concurrent resolution',
        'House Joint Resolution': 'joint resolution',
        'House Resolution': 'resolution',
        'Senate Bill': 'bill',
        'Senate Concurrent Resolution': 'concurrent resolution',
        'Senate Joint Resolution': 'joint resolution',
        'Senate Resolution': 'resolution',
        'Senate Nominations': 'nomination',
        }

    def _url_2_lxml(self, url, base_url='{0.scheme}://{0.netloc}'.format):
        '''
        Fetch the url and parse with lxml.
        '''
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        urldata = urlparse(url)
        doc.make_links_absolute(base_url(urldata))
        return doc

    def _cleanup_sponsors(self, string, chamber,

        # Splits at ampersands and commas.
        re_amp=re.compile(r'[,&]'),

        # Changes "Sen. Jones" into "Jones"
        re_title=re.compile(r'(Sen|Rep)s?[.;]\s?'),

        # Map to clean up sponsor name data.
        name_map={
            '{ NONE...}': '',
            },

        # Mapping of member designations to related chamber type.
        chamber_map={
            'Sen': 'upper',
            'Rep': 'lower',
            },

        chain=itertools.chain.from_iterable,
        replace=methodcaller('replace', '&nbsp', ''),
        strip=methodcaller('strip'),

        splitter=re.compile('(?:[,;] NewLine|(?<!Reps); |on behalf of all \w+)')):
        '''
        Sponsor names are sometimes joined with an ampersand,
        are '{ NONE...}', or contain '&nbsp'. This helper removes
        that stuff and returns a list minus any non-name strings found.
        '''

        # "Briggs King" is a deplorable hack to work around DE's
        # not-easily-parseable sponsorship strings.
        tokenizer = r'(?:(?:[A-Z]\.){,5} )?(?:Briggs King|[A-Z][^.]\S{,50})'
        tokenize = partial(re.findall, tokenizer)

        for string in splitter.split(string):

            # Override the chamber based on presence of "Sens." or "Rep."
            m = re_title.search(string)
            if m:
                chamber = chamber_map[m.group(1)]

            # Remove junk.
            names = re_amp.split(string)
            names = map(lambda s: re_title.sub('', s), names)
            names = map(replace, names)
            names = filter(None, [name_map.get(n, n) for n in names])
            names = map(tokenize, names)

            for n in chain(names):
                yield (strip(n), chamber)

    def _get_urls(self, chamber, session):
        '''
        A generator of urls to legislation types listed on the
        index_url page.
        '''
        re_count = re.compile(r'count=\d+', re.I)

        index_url = ('http://legis.delaware.gov/LIS/lis%s.nsf'
                     '/Legislation/?openview' % session)

        chamber_map = {'Senate': 'upper',
                       'House': 'lower'}

        legislation_types = self.legislation_types

        index_page = self._url_2_lxml(index_url)

        # The last link on the "all legis'n" page pertains to senate
        # nominations, so skip it.
        index_links = index_page.xpath('//a[contains(@href, "Expand=")]')
        index_links = index_links[:-1]

        for el in index_links:

            type_raw = el.xpath('../following-sibling::td')[0].text_content()
            type_ = legislation_types[type_raw]

            # Skip any links that aren't for this chamber.
            _chamber, _ = type_raw.split(' ', 1)
            if chamber != chamber_map[_chamber]:
                continue

            # Tweak the url to ask the server for 10000 results (i.e., all)
            url = el.attrib['href']
            url = re_count.sub('count=10000', url)

            # Get the index page.
            doc = self._url_2_lxml(url)

            for el in doc.xpath('//a[contains(@href, "OpenDocument")]'):

                title = el.xpath('./../../../td[4]')[0].text_content()

                url = el.attrib['href']

                bill_kwargs = {'type': type_,
                               'bill_id': extract_bill_id(el.text),
                               'chamber': chamber,
                               'session': session,
                               'title': title}

                yield (url, bill_kwargs)

    def scrape(self, chamber, session):

        scrape_bill = self.scrape_bill
        for url, kw in self._get_urls(chamber, session):
            scrape_bill(url, kw)

    def scrape_bill(self, url, kw,
                    re_amendment=re.compile(r'(^[A-Z]A \d{1,3}) to'),
                    re_substitution=re.compile(r'(^[A-Z]S \d{1,2}) for'),
                    re_digits=re.compile(r'\d{,5}'),
                    actions_get_actor=actions.get_actor):

        bill = Bill(**kw)
        bill.add_source(url)

        #---------------------------------------------------------------------
        # A few helpers.
        _url_2_lxml = self._url_2_lxml
        _cleanup_sponsors = self._cleanup_sponsors

        # Shortcut function partial to get text at a particular xpath:
        doc = _url_2_lxml(url)
        _get_text = partial(get_text, doc, 0)

        # Get session number--needed for fetching related documents (see below).
        xpath = '//font[contains(., "General Assembly") and @face="Arial"]'
        session_num = doc.xpath(xpath)[0].text_content()
        session_num = re_digits.match(session_num).group()

        #---------------------------------------------------------------------
        # Sponsors
        chamber = bill['chamber']

        sponsor_types = {
            'Additional Sponsor(s):': 'cosponsor',
            'CoSponsors:': 'cosponsor',
            'Primary Sponsor:': 'primary'}

        xpath = '//font[contains(., "Sponsor") and @color="#008080"]'
        headings = doc.xpath(xpath + '/text()')
        sponsors = doc.xpath(xpath + '/../../following-sibling::td/font/text()')

        for h, s in zip(headings, sponsors):

            names = _cleanup_sponsors(s, chamber)
            type_ = sponsor_types[h.strip()]

            if names:
                for name, _chamber in names:
                    bill.add_sponsor(type_, name, chamber=_chamber)

        #---------------------------------------------------------------------
        # Versions

        tmp = '/'.join([
            'http://www.legis.delaware.gov',
            'LIS/lis{session_num}.nsf/vwLegislation',
            '{moniker}/$file/{filename}{format_}?open'])

        documents = self.scrape_documents(source=url,
                                     docname="introduced",
                                     filename="Legis",
                                     tmp=tmp,
                                     session_num=session_num)

        for d in documents:
            bill.add_version(**d)

        # If bill is a substitution, add the original as a version.
        names = doc.xpath('//*[contains(text(), "Substituted '
                          'Legislation for Bill:")]/text()')
        urls = doc.xpath('//*[contains(text(), "Substituted '
                          'Legislation for Bill:")]'
                         '/following-sibling::a/@href')

        for name, url in zip(names, urls):

            name = re_substitution.match(name).group(1)
            bill.add_version(name, url,
                             description='original bill')

        #---------------------------------------------------------------------
        # Actions
        actions = doc.xpath('//font[contains(., "Actions History")]'
                            '/../following-sibling::table/descendant::td[2]')
        actions = actions[0].text_content()
        actions = filter(None, actions.splitlines())

        for a in reversed(actions):
            date, action = a.split(' - ', 1)
            try:
                date = datetime.strptime(date, '%b %d, %Y')
            except ValueError:
                date = datetime.strptime(date, '%B %d, %Y')  # XXX: ugh.

            actor = actions_get_actor(action, bill['chamber'])
            attrs = dict(actor=actor, action=action, date=date)
            attrs.update(**self.categorizer.categorize(action))
            bill.add_action(**attrs)

        #---------------------------------------------------------------------
        # Votes
        vote_strings = doc.xpath('//*[contains(text(), "vote:")]/text()')

        # Sometimes vote strings are contained in weird, separate elements. Probably
        # hand edited.
        if not all(re.search('\d', string) for string in vote_strings):
            # Use the parent's text_content instead.
            vote_strings = []
            for el in doc.xpath('//*[contains(text(), "vote:")]/..'):
                vote_strings.append(el.text_content())

        vote_urls = doc.xpath('//*[contains(text(), "vote:")]'
                              '/following-sibling::a/@href')
        for string, url in zip(vote_strings, vote_urls):

            vote_data = parse_votestring(string)
            vote = self.scrape_vote(url, **vote_data)
            if vote:
                bill.add_vote(vote)

        #---------------------------------------------------------------------
        # Amendments
        xpath = ("//font[contains(., 'Amendments')]/"
                 "../../../td[2]/font/a")

        tmp = ('http://www.legis.delaware.gov/LIS/lis{session_num}.nsf/'
               'vwLegislation/{id_}/$file/{filename}{format_}?open')

        for source, id_ in zip(doc.xpath(xpath + '/@href'),
                               doc.xpath(xpath + '/text()')):

            short_id = re_amendment.match(id_).group(1)

            documents = self.scrape_documents(
                source=source,
                docname='amendment (%s)' % short_id,
                filename='Legis',
                tmp=tmp, session_num=session_num,
                id_=id_)

            for d in documents:
                bill.add_document(**d)

        #---------------------------------------------------------------------
        # Add any related "Engrossments".
        # See www.ncsl.org/documents/legismgt/ILP/98Tab3Pt4.pdf for
        # an explanation of the engrossment process in DE.
        source = doc.xpath('//img[@alt="Engrossment"]/../@href')

        if source:

            tmp = '/'.join([
                'http://www.legis.delaware.gov',
                'LIS/lis{session_num}.nsf/EngrossmentsforLookup',
                '{moniker}/$file/{filename}{format_}?open'])

            documents = self.scrape_documents(
                source=source[0],
                docname="Engrossment",
                filename="Engross",
                tmp=tmp,
                session_num=session_num,
                id_=bill['bill_id'])

            for d in documents:
                bill.add_version(**d)

        # --------------------------------------------------------------------
        # Add any fiscal notes.
        source = doc.xpath("//img[@alt='Fiscal Note']/../@href")

        if source:

            tmp = '/'.join([
                'http://www.legis.delaware.gov',
                'LIS/lis{session_num}.nsf/FiscalforLookup',
                '{docnum}/$file/{filename}{format_}?open'])

            documents = self.scrape_documents(
                source=source[0],
                docname="Fiscal Note",
                filename="Fiscal",
                tmp=tmp,
                session_num=session_num)

            for d in documents:
                bill.add_document(**d)

        #---------------------------------------------------------------------
        # Extra fields

        # Helper to get the first td sibling of certain nodes.
        tmp = '//font[contains(., "%s")]/../../../td[2]'
        first_sibling_text = lambda heading: _get_text(tmp % heading)

        extra_fields = {
            # A long description of the legislation.
            "summary": "Synopsis",
            # Codification details for enacted legislation.
            "volume_chapter": "Volume Chapter",
            # Presumably the date of approval/veto.
            "date_governor_acted": "Date Governor Acted",
            "fiscal_notes": "Fiscal Notes",
        }

        for key, name in extra_fields.iteritems():
            try:
                bill[key] = first_sibling_text(name)
            except IndexError:
                # xpath lookup failed.
                pass

        self.save_bill(bill)

    def scrape_vote(self, url, date, chamber, passed, motion,
                    re_digit=re.compile(r'\d{1,3}'),
                    re_totals=re.compile(
                        r'(?:Yes|No|Not Voting|Absent):\s{,3}(\d{,3})', re.I)):

        namespaces = {"re": "http://exslt.org/regular-expressions"}
        try:
            doc = lxml.html.fromstring(self.urlopen(url))
        except scrapelib.HTTPError as e:
            known_fail_links = [
                "http://legis.delaware.gov/LIS/lis146.nsf/7712cf7cc0e9227a852568470077336f/cdfd8149e79c2bb385257a24006e9f7a?OpenDocument"
            ]
            if "404" in str(e.response):
                # XXX: Ugh, ok, so there's no way (that I could find quickly)
                #      to get the _actual_ response (just "ok") from the object.
                #      As a result, this. Forgive me.
                #            -PRT
                if url in known_fail_links:
                    return
            raise

        xpath = ("//font[re:match(., '^(Yes|No|Not Voting|Absent):', 'i')]"
                 "/ancestor::tr[1]")

        # Get the vote tallies.
        try:
            totals = doc.xpath(xpath, namespaces=namespaces)
            totals = totals[0].text_content()

        except IndexError:
            # Here the vote page didn't have have the typical format.
            # Maybe it's a hand edited page. Log and try to parse
            # the vitals from plain text.
            self.log('Found an unusual votes page at url: "%s"' % url)
            totals = re_totals.findall(doc.text_content())
            if len(totals) == 4:
                self.log('...was able to parse vote tallies from "%s"' % url)

        else:
            totals = re_digit.findall(totals)


        try:
            yes_count, no_count, abstentions, absent = map(int, totals)

        except ValueError:
            # There were'nt any votes listed on this page. This is probably
            # a "voice vote" lacking actual vote tallies.
            yes_count, no_count, other_count = 0, 0, 0

        else:
            other_count = abstentions + absent

        # Create the vote object.
        vote = Vote(chamber, date, motion, passed,
                    yes_count, no_count, other_count)

        # Add source.
        vote.add_source(url)

        # Get the "vote type"
        el = doc.xpath('//font[contains(., "Vote Type:")]')[0]
        try:
            vote_type = el.xpath('following-sibling::font[1]/text()')[0]
        except IndexError:
            vote_type = el.xpath('../following-sibling::font[1]/text()')[0]

        vote['vote_type'] = vote_type

        # Get an iterator like: name1, vote1, name2, vote2, ...
        xpath = ("//font[re:match(., '^[A-Z]$')]"
                 "/../../../descendant::td/font/text()")
        data = doc.xpath(xpath, namespaces=namespaces)
        data = filter(lambda s: s.strip(), data)

        # Handle the rare case where not all names have corresponding
        # text indicating vote value. See e.g. session 146 HB10.
        data_len = len(data)/2
        tally = sum(v for (k, v) in vote.items() if '_count' in k)

        if (0 < data_len) and ((data_len) != tally):
            xpath = ("//font[re:match(., '^[A-Z]$')]/ancestor::table")
            els = doc.xpath(xpath, namespaces=namespaces)[-1]
            els = els.xpath('descendant::td')
            data = [e.text_content().strip() for e in els]

        data = iter(data)

        # Add names and vote values.
        vote_map = {
            'Y': 'yes',
            'N': 'no',
            }

        while True:

            try:
                name = data.next()
                _vote = data.next()

                # Evidently, the motion for vote can be rescinded before
                # the vote is cast, perhaps due to a quorum failure.
                # (See the Senate vote (1/26/2011) for HB 10 w/HA 1.) In
                # this rare case, values in the vote col are whitespace. Skip.
                if not _vote.strip():
                    continue

                _vote = vote_map.get(_vote, 'other')
                getattr(vote, _vote)(name)

            except StopIteration:
                break

        return vote


    def scrape_documents(self, source, docname, filename, tmp, session_num,
                         re_docnum=re.compile(r'var F?docnum="(.+?)"'),
                         re_moniker=re.compile(r'var moniker="(.+?)"'),
                         **kwargs):
        '''
        Returns a generator like [{'name': 'docname', 'url': 'docurl'}, ...]
        '''
        source = source.replace(' ', '+')

        try:
            _doc = self._url_2_lxml(source)
        except scrapelib.HTTPError:
            # Grrr...there was a dead link posted. Warn and skip.
            msg = 'Related document download failed (dead link): %r' % source
            self.warning(msg)
            return

        if _doc.xpath('//font[contains(., "DRAFT INFORMATION")]'):
            # This amendment is apparently still in draft form or can't
            # be viewed for security reasons, but we can still link to
            # its status page.
            yield dict(name=docname, url=source)
            return

        # The full-text urls are generated using onlick javascript and
        # window-level vars named "moniker" and "docnum".
        if docname == "Fiscal Note":
            xpath = '//script[contains(., "var Fdocnum")]'
        else:
            xpath = '//script[contains(., "var docnum")]'
        script_text = _doc.xpath(xpath)[0].text_content()
        docnum = re_docnum.search(script_text).group(1)
        moniker = re_moniker.search(script_text).group(1)

        # Mimetypes.
        formats = ['.html', '.pdf', '.docx', '.Docx']
        mimetypes = {
            '.html': 'text/html',
            '.pdf': 'application/pdf',
            '.docx': 'application/msword'
            }

        for format_ in formats:

            el =_doc.xpath('//font[contains(., "%s%s")]' % (filename, format_))

            if not el:
                continue

            format_ = format_.lower()
            _kwargs = kwargs.copy()
            _kwargs.update(**locals())

            if format_.lower() == '.docx':
                _kwargs['filename'] = docnum
            else:
                _kwargs['filename'] = _kwargs['filename'].lower()

            url = tmp.format(**_kwargs).replace(' ', '+')

            try:
                self.urlopen(url)
            except scrapelib.HTTPError:
                msg = 'Could\'t fetch %s version at url: "%s".'
                self.warning(msg % (format_, url))
            else:
                yield dict(name=docname, url=url,
                           source=source, mimetype=mimetypes[format_])
