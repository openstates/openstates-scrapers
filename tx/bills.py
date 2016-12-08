import datetime
import ftplib
import re
import time
import xml.etree.cElementTree as etree

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill


class TXBillScraper(BillScraper):
    jurisdiction = 'tx'
    _FTP_ROOT = 'ftp.legis.state.tx.us'
    CHAMBERS = {'H': 'lower', 'S': 'upper'}
    NAME_SLUGS = {
        'I': 'Introduced',
        'E': 'Engrossed',
        'S': 'Senate Committee Report',
        'H': 'House Committee Report',
        'F': 'Enrolled'
    }

    def _get_ftp_files(self, root, dir_):
        ''' Recursively traverse an FTP directory, returning all files '''

        for i in range(3):
            try:
                ftp = ftplib.FTP(root)
                break
            except (EOFError, ftplib.error_temp):
                time.sleep(2 ** i)
        else:
            raise
        ftp.login()
        ftp.cwd('/' + dir_)
        self.log('Searching an FTP folder for files ({})'.format(dir_))

        lines = []
        ftp.retrlines('LIST', lines.append)
        for line in lines:
            (_date, _time, is_dir, _file_size, name) = re.search(r'''(?x)
                    ^(\d{2}-\d{2}-\d{2})\s+  # Date in mm-dd-yy
                    (\d{2}:\d{2}[AP]M)\s+  # Time in hh:mmAM/PM
                    (<DIR>)?\s+  # Directories will have an indicating flag
                    (\d+)?\s+  # Files will have their size in bytes
                    (.+?)\s*$  # Directory or file name is the remaining text
                    ''', line).groups()
            if is_dir:
                for item in self._get_ftp_files(root, '/'.join([dir_, name])):
                    yield item
            else:
                yield '/'.join(['ftp://' + root, dir_, name])

    def scrape(self, session, chambers):
        self.validate_session(session)

        session_code = session
        if len(session_code) == 2:
            session_code = session_code + 'R'
        assert len(session_code) == 3, "Unable to handle the session name"

        self.versions = []
        version_files = self._get_ftp_files(self._FTP_ROOT,
                                            'bills/{}/billtext/html'.
                                            format(session_code))
        for item in version_files:
            bill_id = item.split('/')[-1].split('.')[0]
            bill_id = ' '.join(re.search(r'([A-Z]{2})R?0+(\d+)',
                               bill_id).groups())
            self.versions.append((bill_id, item))

        self.analyses = []
        analysis_files = self._get_ftp_files(self._FTP_ROOT,
                                             'bills/{}/analysis/html'.
                                             format(session_code))
        for item in analysis_files:
            bill_id = item.split('/')[-1].split('.')[0]
            bill_id = ' '.join(re.search(r'([A-Z]{2})R?0+(\d+)',
                               bill_id).groups())
            self.analyses.append((bill_id, item))

        self.fiscal_notes = []
        fiscal_note_files = self._get_ftp_files(self._FTP_ROOT,
                                                'bills/{}/fiscalnotes/html'.
                                                format(session_code))
        for item in fiscal_note_files:
            bill_id = item.split('/')[-1].split('.')[0]
            bill_id = ' '.join(re.search(r'([A-Z]{2})R?0+(\d+)',
                               bill_id).groups())
            self.fiscal_notes.append((bill_id, item))

        self.witnesses = []
        witness_files = self._get_ftp_files(self._FTP_ROOT,
                                            'bills/{}/witlistbill/html'.
                                            format(session_code))
        for item in witness_files:
            bill_id = item.split('/')[-1].split('.')[0]
            bill_id = ' '.join(re.search(r'([A-Z]{2})R?0+(\d+)',
                               bill_id).groups())
            self.witnesses.append((bill_id, item))

        history_files = self._get_ftp_files(self._FTP_ROOT,
                                            'bills/{}/billhistory'.
                                            format(session_code))
        for bill_url in history_files:
            self.scrape_bill(session, bill_url)

    def scrape_bill(self, session, history_url):
        history_xml = self.get(history_url).text.encode('ascii', 'ignore')
        root = etree.fromstring(history_xml)

        bill_title = root.findtext("caption")
        if (bill_title is None or
                "Bill does not exist" in history_xml):
            self.warning("Bill does not appear to exist")
            return
        bill_id = ' '.join(root.attrib['bill'].split(' ')[1:])

        chamber = self.CHAMBERS[bill_id[0]]

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

        bill.add_source(history_url)

        bill['subjects'] = []
        for subject in root.iterfind('subjects/subject'):
            bill['subjects'].append(subject.text.strip())

        versions = [x for x in self.versions if x[0] == bill_id]
        for version in versions:
            bill.add_version(
                name=self.NAME_SLUGS[version[1][-5]],
                url=version[1],
                mimetype='text/html'
            )

        analyses = [x for x in self.analyses if x[0] == bill_id]
        for analysis in analyses:
            bill.add_document(
                name="Analysis ({})".format(self.NAME_SLUGS[analysis[1][-5]]),
                url=analysis[1],
                mimetype='text/html'
            )

        fiscal_notes = [x for x in self.fiscal_notes if x[0] == bill_id]
        for fiscal_note in fiscal_notes:
            bill.add_document(
                name="Fiscal Note ({})".format(self.NAME_SLUGS
                                               [fiscal_note[1][-5]]),
                url=fiscal_note[1],
                mimetype='text/html'
            )

        witnesses = [x for x in self.witnesses if x[0] == bill_id]
        for witness in witnesses:
            bill.add_document(
                name="Witness List ({})".format(self.NAME_SLUGS
                                                [witness[1][-5]]),
                url=witness[1],
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
                self.warning("Skipping public hearing action with no date")
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
            elif (desc.startswith('Referred to') or
                    desc.startswith("Recommended to be sent to ")):
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
                bill.add_sponsor('cosponsor',
                                 coauthor,
                                 official_type='coauthor')
        for sponsor in root.findtext('sponsors').split(' | '):
            if sponsor != "":
                bill.add_sponsor('primary', sponsor, official_type='sponsor')
        for cosponsor in root.findtext('cosponsors').split(' | '):
            if cosponsor != "":
                bill.add_sponsor('cosponsor',
                                 cosponsor,
                                 official_type='cosponsor')

        self.save_bill(bill)
