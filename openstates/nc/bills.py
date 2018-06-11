import pytz
import datetime as dt
import lxml.html
from pupa.scrape import Scraper, Bill, VoteEvent

eastern = pytz.timezone('US/Eastern')


class NCBillScraper(Scraper):

    _action_classifiers = {
        'Vetoed': 'executive-veto',
        'Signed By Gov': 'executive-signature',
        'Signed by Gov': 'executive-signature',
        'Pres. To Gov.': 'executive-receipt',
        'Withdrawn from ': 'withdrawal',
        'Ref ': 'referral-committee',
        'Re-ref ': 'referral-committee',
        'Reptd Fav': 'committee-passage-favorable',
        'Reptd Unfav': 'committee-passage-unfavorable',
        'Passed 1st Reading': 'reading-1',
        'Passed 2nd Reading': 'reading-2',
        'Passed 3rd Reading': ['passage', 'reading-3'],
        'Passed 2nd & 3rd Reading': ['passage', 'reading-2',
                                     'reading-3'],
        'Failed 3rd Reading': ['failure', 'reading-3'],
        'Filed': 'introduction',
        'Adopted': 'passage',       # resolutions
        'Concurred In': 'amendment-passage',
        'Com Amend Adopted': 'amendment-passage',
        'Assigned To': 'referral-committee',
        'Amendment Withdrawn': 'amendment-withdrawal',
        'Amendment Offered': 'amendment-introduction',
        'Amend Failed': 'amendment-failure',
        'Amend Adopted': 'amendment-passage',
        'Became Law W/o Signature': 'became-law',
        'Ch.': 'became-law',
        'Veto Overridden': 'veto-override-passage',
    }

    def scrape_bill(self, chamber, session, bill_id):
        # there will be a space in bill_id if we're doing a one-off bill scrape
        # convert HB 102 into H102
        if ' ' in bill_id:
            bill_id = bill_id[0] + bill_id.split(' ')[-1]

        # if chamber comes in as House/Senate convert to lower/upper
        if chamber == 'Senate':
            chamber = 'upper'
        elif chamber == 'House':
            chamber = 'lower'

        bill_detail_url = ('http://www.ncleg.net/gascripts/'
                           'BillLookUp/BillLookUp.pl?Session=%s&BillID=%s&votesToView=all') % (
                               session, bill_id)

        # parse the bill data page, finding the latest html text
        data = self.get(bill_detail_url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(bill_detail_url)

        title_div_txt = doc.xpath('//div[contains(@class, "h2")]/text()')[0]
        if 'Joint Resolution' in title_div_txt:
            bill_type = 'joint resolution'
            bill_id = bill_id[0] + 'JR ' + bill_id[1:]
        elif 'Resolution' in title_div_txt:
            bill_type = 'resolution'
            bill_id = bill_id[0] + 'R ' + bill_id[1:]
        elif 'Bill' in title_div_txt:
            bill_type = 'bill'
            bill_id = bill_id[0] + 'B ' + bill_id[1:]

        bill_title = doc.xpath('//div[contains(@class, "h5")]')[0].text_content().strip()

        bill = Bill(bill_id, legislative_session=session, title=bill_title, chamber=chamber,
                    classification=bill_type)
        bill.add_source(bill_detail_url)

        # skip first PDF link (duplicate link to cur version)
        if chamber == 'lower':
            link_xpath = '//a[contains(@href, "/Bills/House/PDF/")]'
        else:
            link_xpath = '//a[contains(@href, "/Bills/Senate/PDF/")]'
        for vlink in doc.xpath(link_xpath)[1:]:
            # get the name from the PDF link...
            version_name = vlink.text.replace(u'\xa0', ' ')
            version_url = vlink.attrib['href']
            bill.add_version_link(version_name, version_url, media_type='text/html',
                                  on_duplicate='ignore')

        # sponsors
        spon_row = doc.xpath('//div[contains(text(), "Sponsors")]/following-sibling::div')[0]
        # first sponsors are primary, until we see (Primary)
        spon_type = 'primary'
        for leg in spon_row.text_content().split(';'):
            name = leg.replace(u'\xa0', ' ').strip()
            if name.startswith('(Primary)'):
                name = name.replace('(Primary)', '').strip()
                spon_type = 'cosponsor'
            if not name:
                continue
            bill.add_sponsorship(name, classification=spon_type, entity_type='person',
                                 primary=(spon_type == 'primary'))

        # keywords
        kw_row = doc.xpath('//div[contains(text(), "Keywords:")]/following-sibling::div')[0]
        for subject in kw_row.text_content().split(', '):
            bill.add_subject(subject)

        # actions
        action_tr_xpath = (
            '//h6[contains(text(), "History")]'
            '/ancestor::div[contains(@class, "gray-card")]'
            '//div[contains(@class, "card-body")]'
            '/div[@class="row"]'
        )
        # skip two header rows
        for row in doc.xpath(action_tr_xpath):
            cols = row.xpath('div')
            act_date = cols[1].text
            actor = cols[3].text or ''
            # if text is blank, try diving in
            action = (cols[5].text or '').strip() or cols[5].text_content().strip()

            act_date = dt.datetime.strptime(act_date, '%m/%d/%Y').strftime('%Y-%m-%d')

            if actor == 'Senate':
                actor = 'upper'
            elif actor == 'House':
                actor = 'lower'
            else:
                actor = 'executive'

            for pattern, atype in self._action_classifiers.items():
                if action.startswith(pattern):
                    break
            else:
                atype = None

            bill.add_action(action, act_date, chamber=actor, classification=atype)

        yield from self.scrape_votes(bill, doc)

        yield bill

    def scrape_votes(self, bill, doc):
        vote_tr_path = (
            '//h6[@id="vote-header"]'
            '/ancestor::div[contains(@class, "gray-card")]'
            '//div[contains(@class, "card-body")]'
            '//div[@class="row"]'
        )

        for vote_row in doc.xpath(vote_tr_path):
            entries = [each.text_content() for each in vote_row.xpath('div')[1:-1:2]]
            date, subject, rcs, aye, no, nv, abs, exc, total = entries
            result = vote_row.xpath('div/a')[0]
            result_text = result.text
            result_link = result.get('href')

            if 'H' in rcs:
                chamber = 'lower'
            elif 'S' in rcs:
                chamber = 'upper'

            date = eastern.localize(
                dt.datetime.strptime(date.replace('.', ''), "%m/%d/%Y %H:%M %p"))
            date = date.isoformat()

            ve = VoteEvent(chamber=chamber,
                           start_date=date,
                           motion_text=subject,
                           result='pass' if 'PASS' in result_text else 'fail',
                           bill=bill,
                           classification='passage',    # TODO: classify votes
                           )
            ve.set_count('yes', int(aye))
            ve.set_count('no', int(no))
            ve.set_count('not voting', int(nv))
            ve.set_count('absent', int(abs))
            ve.set_count('excused', int(exc))
            ve.add_source(result_link)

            data = self.get(result_link).text
            vdoc = lxml.html.fromstring(data)

            # only one table that looks like this
            vote_table, = vdoc.xpath('//table[@cellpadding="5"]')

            # skip party row
            for row in vote_table.xpath('tr')[1:]:
                vote_type, dems, reps = row.xpath('td')

                vote_type = vote_type.text_content()
                if 'Ayes' in vote_type:
                    vote_type = 'yes'
                elif 'Noes' in vote_type:
                    vote_type = 'no'
                elif 'Not Voting' in vote_type:
                    vote_type = 'not voting'
                elif 'Exc. Absence' in vote_type:
                    vote_type = 'absent'
                elif 'Exc. Vote' in vote_type:
                    vote_type = 'excused'
                else:
                    raise ValueError('unknown vote type: ' + vote_type)

                for name in (vote_list_to_names(dems.text_content()) +
                             vote_list_to_names(reps.text_content())):
                    ve.vote(vote_type, name)

            yield ve

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber = {'lower': 'House', 'upper': 'Senate'}[chamber]
        url = ('http://www.ncleg.net/gascripts/SimpleBillInquiry/'
               'displaybills.pl?Session=%s&tab=Chamber&Chamber=%s') % (session, chamber)

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        for row in doc.xpath('//table[@cellpadding=3]/tr')[1:]:
            bill_id = row.xpath('td[1]/a/text()')[0]
            yield from self.scrape_bill(chamber, session, bill_id)


def vote_list_to_names(names):
    title, rest = names.split(': ', 1)
    if 'None' in rest:
        return []
    return rest.split('; ')
