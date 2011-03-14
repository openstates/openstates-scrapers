import re
import urllib2
import urlparse
import datetime

from billy.utils import urlescape
from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill

from openstates.tx.utils import chamber_name, parse_ftp_listing

import lxml.etree


class TXBillScraper(BillScraper):
    state = 'tx'
    _ftp_root = 'ftp://ftp.legis.state.tx.us/'

    def scrape(self, chamber, session):
        self.validate_session(session)

        if len(session) == 2:
            session = "%sR" % session

        for btype in ['bills', 'concurrent_resolutions',
                      'joint_resolutions', 'resolutions']:
            billdirs_path = '/bills/%s/billhistory/%s_%s/' % (
                session, chamber_name(chamber), btype)
            billdirs_url = urlparse.urljoin(self._ftp_root, billdirs_path)

            with self.urlopen(billdirs_url) as bill_dirs:
                for dir in parse_ftp_listing(bill_dirs):
                    bill_url = urlparse.urljoin(billdirs_url, dir) + '/'
                    with self.urlopen(bill_url) as bills:
                        for history in parse_ftp_listing(bills):
                            self.scrape_bill(chamber, session,
                                             urlparse.urljoin(bill_url,
                                                              history))

    def scrape_bill(self, chamber, session, url):
        with self.urlopen(url) as data:
            if "Bill does not exist." in data:
                return

            bill = self.parse_bill_xml(chamber, session, data)
            bill.add_source(urlescape(url))

            versions_url = url.replace('billhistory', 'billtext/html')
            # URLs for versions inexplicably (H|S)(J|C) instead of (H|J)(CR|JR)
            versions_url = versions_url.replace('JR', 'J').replace('CR', 'C')
            versions_url = '/'.join(versions_url.split('/')[0:-1])

            bill_prefix = bill['bill_id'].split()[0]
            bill_num = int(bill['bill_id'].split()[1])
            long_bill_id = "%s%05d" % (bill_prefix, bill_num)

            try:
                with self.urlopen(versions_url) as versions_list:
                    bill.add_source(urlescape(versions_url))
                    for version in parse_ftp_listing(versions_list):
                        if version.startswith(long_bill_id):
                            version_name = version.split('.')[0]
                            version_url = urlparse.urljoin(
                                versions_url + '/',
                                version)
                            bill.add_version(version_name,
                                             urlescape(version_url))
            except urllib2.URLError:
                # Sometimes the text is missing
                pass

            self.save_bill(bill)

    def parse_bill_xml(self, chamber, session, txt):
        root = lxml.etree.fromstring(txt)
        bill_id = ' '.join(root.attrib['bill'].split(' ')[1:])
        bill_title = root.findtext("caption")

        if session[2] == 'R':
            session = session[0:2]

        if bill_id[1] == 'B':
            bill_type = ['bill']
        elif bill_id[1] == 'R':
            bill_type = ['resolution']
        elif bill_id[1:3] == 'CR':
            bill_type = ['concurrent resolution']
        elif bill_id[1:3] == 'JR':
            bill_type = ['joint resolution']
        else:
            raise ScrapeError("Invalid bill_id: %s" % bill_id)

        bill = Bill(session, chamber, bill_id, bill_title, type=bill_type)

        for action in root.findall('actions/action'):
            act_date = datetime.datetime.strptime(action.findtext('date'),
                                            "%m/%d/%Y").date()

            extra = {}
            extra['action_number'] = action.find('actionNumber').text
            comment = action.find('comment')
            if comment is not None and comment.text:
                extra['comment'] = comment.text.strip()

            actor = {'H': 'lower',
                     'S': 'upper',
                     'E': 'executive'}[extra['action_number'][0]]

            desc = action.findtext('description').strip()

            if desc == 'Scheduled for public hearing on . . .':
                continue

            if desc == 'Amended':
                atype = 'amendment:passed'
            elif desc == 'Amendment(s) offered':
                atype = 'amendment:introduced'
            elif desc == 'Amendment amended':
                atype = 'amendment:amended'
            elif desc == 'Amendment withdrawn':
                atype = 'amendment:withdrawn'
            elif desc == 'Passed' or desc == 'Adopted':
                atype = 'bill:passed'
            elif re.match(r'^Received (by|from) the', desc):
                if 'Secretary of the Senate' not in desc:
                    atype = 'bill:introduced'
                else:
                    atype = 'other'
            elif desc.startswith('Sent to the Governor'):
                # But what if it gets lost in the mail?
                atype = 'governor:received'
            elif desc.startswith('Signed by the Governor'):
                atype = 'governor:signed'
            elif desc == 'Read first time':
                atype = ['bill:introduced', 'bill:reading:1']
                introduced = True
            elif desc == 'Read & adopted':
                atype = 'bill:passed'
            elif desc.startswith('Referred to'):
                atype = 'committee:referred'
            elif desc == "Filed":
                atype = 'bill:filed'
            else:
                atype = 'other'

            bill.add_action(actor, action.findtext('description'),
                            act_date, type=atype, **extra)

        for author in root.findtext('authors').split(' | '):
            if author != "":
                bill.add_sponsor('author', author)
        for coauthor in root.findtext('coauthors').split(' | '):
            if coauthor != "":
                bill.add_sponsor('coauthor', coauthor)
        for sponsor in root.findtext('sponsors').split(' | '):
            if sponsor != "":
                bill.add_sponsor('sponsor', sponsor)
        for cosponsor in root.findtext('cosponsors').split(' | '):
            if cosponsor != "":
                bill.add_sponsor('cosponsor', cosponsor)

        bill['subjects'] = []
        for subject in root.iterfind('subjects/subject'):
            bill['subjects'].append(subject.text.strip())

        return bill
