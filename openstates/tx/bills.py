import re
from urlparse import urljoin
import datetime
import ftplib

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill

from .utils import chamber_name, parse_ftp_listing

import lxml.etree


class TXBillScraper(BillScraper):
    jurisdiction = 'tx'
    _ftp_root = 'ftp.legis.state.tx.us'

    def _get_ftp_files(self, root, dir_):
        '''
        Walk an FTP directory and its subdirectories, and yield the
        paths to all files therein
        '''

        ftp = ftplib.FTP(self._ftp_root)
        ftp.login()
        ftp.cwd(dir_)
        self.log('Searching an FTP folder for files ({})'.format(dir_))

        lines = []
        ftp.retrlines('LIST', lines.append)
        for line in lines:
            name = line.split(' ')[-1]
            if '<DIR>' in line:
                for item in self._get_ftp_files(root, '/'.join([dir_, name])):
                    yield item
            else:
                yield '/'.join(['ftp://' + root, dir_, name])

    def scrape(self, chamber, session):
        """Scrapes information on all bills for a given chamber and session."""
        self.validate_session(session)

        if len(session) == 2:
            session = '%sR' % session

        self.versions = []
        version_files = self._get_ftp_files(self._ftp_root, 'bills/{}/billtext/html'.format(session))
        for item in version_files:
            bill_id = item.split('/')[-1].split('.')[0]
            bill_id = ' '.join(re.search(r'([A-Z]{2})R?0+(\d+)', bill_id).groups())
            self.versions.append((bill_id, item))

        for bill_type in ['bills', 'concurrent_resolutions',
                          'joint_resolutions', 'resolutions']:
            # This is the billhistory directory for a particular type of bill
            # (e.g. senate resolutions).  It should contain subdirectories
            # with names like "SR00001_SR00099".
            history_dir_url = 'ftp://' + self._ftp_root + '/bills/%s/billhistory/%s_%s/' % (
                    session, chamber_name(chamber), bill_type)
            history_groups_listing = self.urlopen(history_dir_url)
            # A group_dir has a name like "HJR00200_HJR00299" and contains
            # the files for a group of 100 bills.
            for group_dir in parse_ftp_listing(history_groups_listing):
                self.scrape_group(
                    chamber, session, history_dir_url, group_dir)

    def scrape_group(self, chamber, session, history_dir_url, group_dir):
        """Scrapes information on all bills in a given group of 100 bills."""
        # Under billhistory, each group dir has a name like HBnnnnn_HBnnnnn,
        # HCRnnnnn_HCRnnnnn, HJRnnnnn_HJRnnnnn, HRnnnnn_HRnnnnn.
        history_group_url = urljoin(history_dir_url, group_dir) + '/'
        # For each group_dir under billhistory, there is a corresponding dir in
        # billtext/html containing the bill versions (texts).  These dirs have
        # similar names, except the prefix is "HC", "HJ", "SC", "SJ" for
        # concurrent/joint resolutions instead of "HCR", "HJR", "SCR", "SJR".

        # Now get the history and version data for each bill.
        histories_list = self.urlopen(history_group_url)
        for history_file in parse_ftp_listing(histories_list):
            url = urljoin(history_group_url, history_file)
            bill_num = int(re.search(r'\d+', history_file).group(0))
            self.scrape_bill(chamber, session, url, history_group_url,
                             bill_num)

    def scrape_bill(self, chamber, session, history_url, history_group_url,
                   billno):
        """Scrapes the information for a single bill."""
        history_xml = self.urlopen(history_url)
        if "Bill does not exist." in history_xml:
            return

        bill = self.parse_bill_xml(chamber, session, history_xml)
        if bill is None:
            return

        bill.add_source(history_url)

        text_group_url = history_group_url.replace(
            '/billhistory/', '/billtext/html/')
        text_group_url = re.sub('([HS][CJ])R', '\\1', text_group_url)

        self.save_bill(bill)

    def parse_bill_xml(self, chamber, session, txt):
        root = lxml.etree.fromstring(txt.bytes)
        bill_id = ' '.join(root.attrib['bill'].split(' ')[1:])
        bill_title = root.findtext("caption")
        if bill_title is None:
            return None

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

        versions = [x for x in self.versions if x[0] == bill_id]
        for version in versions:
            version_names = {
                    'I': 'Introduced',
                    'E': 'Engrossed',
                    'S': 'Senate Committee Report',
                    'H': 'House Committee Report',
                    'F': 'Enrolled'
            }
            bill.add_version(
                    name=version_names[version[1][-5]],
                    url=version[1],
                    mimetype='text/html'
            )

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

            introduced = False

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
                    atype = 'bill:filed'
            elif desc.startswith('Sent to the Governor'):
                # But what if it gets lost in the mail?
                atype = 'governor:received'
            elif desc.startswith('Signed by the Governor'):
                atype = 'governor:signed'
            elif desc == 'Vetoed by the Governor':
                atype = 'governor:vetoed'
            elif desc == 'Read first time':
                atype = ['bill:introduced', 'bill:reading:1']
                introduced = True
            elif desc == 'Read & adopted':
                atype = ['bill:passed']
                if not introduced:
                    introduced = True
                    atype.append('bill:introduced')
            elif desc == "Passed as amended":
                atype = 'bill:passed'
            elif desc.startswith('Referred to') or desc.startswith("Recommended to be sent to "):
                atype = 'committee:referred'
            elif desc == "Reported favorably w/o amendment(s)":
                atype = 'committee:passed'
            elif desc == "Filed":
                atype = 'bill:filed'
            elif desc == 'Read 3rd time':
                atype = 'bill:reading:3'
            elif desc == 'Read 2nd time':
                atype = 'bill:reading:2'
            elif desc.startswith('Reported favorably'):
                atype = 'committee:passed:favorable'
            else:
                atype = 'other'

            if 'committee:referred' in atype:
                repls = [
                    'Referred to',
                    "Recommended to be sent to "
                ]
                ctty = desc
                for r in repls:
                    ctty = ctty.replace(r, "").strip()
                extra['committees'] = ctty

            bill.add_action(actor, action.findtext('description'),
                            act_date, type=atype, **extra)

        for author in root.findtext('authors').split(' | '):
            if author != "":
                bill.add_sponsor('primary', author, official_type='author')
        for coauthor in root.findtext('coauthors').split(' | '):
            if coauthor != "":
                bill.add_sponsor('cosponsor', coauthor, official_type='coauthor')
        for sponsor in root.findtext('sponsors').split(' | '):
            if sponsor != "":
                bill.add_sponsor('primary', sponsor, official_type='sponsor')
        for cosponsor in root.findtext('cosponsors').split(' | '):
            if cosponsor != "":
                bill.add_sponsor('cosponsor', cosponsor, official_type='cosponsor')

        bill['subjects'] = []
        for subject in root.iterfind('subjects/subject'):
            bill['subjects'].append(subject.text.strip())

        return bill
