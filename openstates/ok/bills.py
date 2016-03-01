import re
import urllib
import datetime
import collections

from billy.utils import urlescape
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html
import scrapelib

from .actions import Categorizer


class OKBillScraper(BillScraper):

    jurisdiction = 'ok'
    bill_types = ['B', 'JR', 'CR', 'R']
    subject_map = collections.defaultdict(list)

    categorizer = Categorizer()

    def scrape(self, chamber, session, only_bills=None):
        # start by building subject map
        self.scrape_subjects(chamber, session)

        url = "http://webserver1.lsb.state.ok.us/WebApplication3/WebForm1.aspx"
        form_page = lxml.html.fromstring(self.get(url).text)

        if chamber == 'upper':
            chamber_letter = 'S'
        else:
            chamber_letter = 'H'

        session_id = self.metadata['session_details'][session]['session_id']

        values = {'cbxSessionId': session_id,
                  'cbxActiveStatus': 'All',
                  'RadioButtonList1': 'On Any day',
                  'Button1': 'Retrieve'}

        lbxTypes = []
        for bill_type in self.bill_types:
            lbxTypes.append(chamber_letter + bill_type)
        values['lbxTypes'] = lbxTypes

        for hidden in form_page.xpath("//input[@type='hidden']"):
            values[hidden.attrib['name']] =  hidden.attrib['value']

        page = self.post(url, data=values).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        bill_nums = []
        for link in page.xpath("//a[contains(@href, 'BillInfo')]"):
            bill_id = link.text.strip()
            bill_num = int(re.findall('\d+', bill_id)[0])
            if bill_num >= 9900:
                self.log('skipping likely bad bill %s' % bill_id)
                continue
            if only_bills is not None and bill_id not in only_bills:
                self.log('skipping bill we are not interested in %s' % bill_id)
                continue
            bill_nums.append(bill_num)
            self.scrape_bill(chamber, session, bill_id, link.attrib['href'])
        return bill_nums

    def scrape_bill(self, chamber, session, bill_id, url):
        try:
            page = lxml.html.fromstring(self.get(url).text)
        except scrapelib.HTTPError as e:
            self.warning('error (%s) fetching %s, skipping' % (e, url))
            return

        title = page.xpath(
            "string(//span[contains(@id, 'PlaceHolder1_txtST')])").strip()

        if 'JR' in bill_id:
            bill_type = ['joint resolution']
        elif 'CR' in bill_id:
            bill_type = ['concurrent resolution']
        elif 'R' in bill_id:
            bill_type = ['resolution']
        else:
            bill_type = ['bill']

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_source(url)
        bill['subjects'] = self.subject_map[bill_id]

        for link in page.xpath("//a[contains(@id, 'Auth')]"):
            name = link.xpath("string()").strip()

            if ':' in name:
                raise Exception(name)
            if 'otherAuth' in link.attrib['id']:
                bill.add_sponsor('cosponsor', name)
            else:
                bill.add_sponsor('primary', name)

        act_table = page.xpath("//table[contains(@id, 'Actions')]")[0]
        for tr in act_table.xpath("tr")[2:]:
            action = tr.xpath("string(td[1])").strip()
            if not action or action == 'None':
                continue

            date = tr.xpath("string(td[3])").strip()
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            actor = tr.xpath("string(td[4])").strip()
            if actor == 'H':
                actor = 'lower'
            elif actor == 'S':
                actor = 'upper'

            attrs = dict(actor=actor, action=action, date=date)
            attrs.update(**self.categorizer.categorize(action))
            bill.add_action(**attrs)

        version_table = page.xpath("//table[contains(@id, 'Versions')]")[0]
        # Keep track of already seen versions to prevent processing duplicates.
        version_urls = []
        for link in version_table.xpath(".//a[contains(@href, '.PDF')]"):
            version_url = link.attrib['href']
            if version_url in version_urls:
                self.logger.warning('Skipping duplicate version URL.')
                continue
            else:
                version_urls.append(version_url)
            name = link.text.strip()

            if re.search('COMMITTEE REPORTS|SCHEDULED CCR', version_url, re.IGNORECASE):
                bill.add_document(name, version_url, mimetype='application/pdf')
                continue

            bill.add_version(name, version_url, mimetype='application/pdf')

        for link in page.xpath(".//a[contains(@href, '_VOTES')]"):
            if 'HT_' not in link.attrib['href']:
                self.scrape_votes(bill, urlescape(link.attrib['href']))

        # # If the bill has no actions and no versions, it's a bogus bill on
        # # their website, which appears to happen occasionally. Skip.
        has_no_title = (bill['title'] == "Short Title Not Found.")
        if has_no_title:
            # If there's no title, this is an empty page. Skip!
            return

        else:
            # Otherwise, save the bills.
            self.save_bill(bill)

    def scrape_votes(self, bill, url):
        page = lxml.html.fromstring(self.get(url).text.replace(u'\xa0', ' '))

        re_ns = "http://exslt.org/regular-expressions"
        path = "//p[re:test(text(), 'OKLAHOMA\s+(HOUSE|STATE\s+SENATE)')]"
        for header in page.xpath(path, namespaces={'re': re_ns}):
            bad_vote = False
            # Each chamber has the motion name on a different line of the file
            if 'HOUSE' in header.xpath("string()"):
                chamber = 'lower'
                motion_index = 8
            else:
                chamber = 'upper'
                motion_index = 13

            motion = header.xpath(
                "string(following-sibling::p[%d])" % motion_index).strip()
            motion = re.sub(r'\s+', ' ', motion)
            assert motion.strip(), "Motion text not found"
            match = re.match(r'^(.*) (PASSED|FAILED)$', motion)
            if match:
                motion = match.group(1)
                passed = match.group(2) == 'PASSED'
            else:
                passed = None

            rcs_p = header.xpath(
                "following-sibling::p[contains(., 'RCS#')]")[0]
            rcs_line = rcs_p.xpath("string()").replace(u'\xa0', ' ')
            rcs = re.search(r'RCS#\s+(\d+)', rcs_line).group(1)

            date_line = rcs_p.getnext().xpath("string()")
            date = re.search(r'\d+/\d+/\d+', date_line).group(0)
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            vtype = None
            counts = collections.defaultdict(int)
            votes = collections.defaultdict(list)

            seen_yes = False

            for sib in header.xpath("following-sibling::p")[13:]:
                line = sib.xpath("string()").replace('\r\n', ' ').strip()
                if "*****" in line:
                    break

                match = re.match(
                    r'(YEAS|NAYS|EXCUSED|VACANT|CONSTITUTIONAL PRIVILEGE|NOT VOTING|N/V)\s*:\s*(\d+)(.*)',
                    line)
                if match:
                    if match.group(1) == 'YEAS' and 'RCS#' not in line:
                        vtype = 'yes'
                        seen_yes = True
                    elif match.group(1) == 'NAYS' and seen_yes:
                        vtype = 'no'
                    elif match.group(1) == 'VACANT':
                        continue  # skip these
                    elif seen_yes:
                        vtype = 'other'
                    if seen_yes and match.group(3).strip():
                        self.logger.warning("Bad vote format, skipping.")
                        bad_vote = True
                    counts[vtype] += int(match.group(2))
                elif seen_yes:
                    for name in line.split('   '):
                        if not name:
                            continue
                        if 'HOUSE' in name or 'SENATE ' in name:
                            continue
                        votes[vtype].append(name.strip())

            if bad_vote:
                continue

            if passed is None:
                passed = counts['yes'] > (counts['no'] + counts['other'])

            vote = Vote(chamber, date, motion, passed,
                        counts['yes'], counts['no'], counts['other'],
                        rcs_num=rcs)
            vote.validate()

            vote.add_source(url)

            for name in votes['yes']:
                vote.yes(name)
            for name in votes['no']:
                if ':' in name:
                    raise Exception(name)
                vote.no(name)
            for name in votes['other']:
                vote.other(name)

            vote.validate()
            bill.add_vote(vote)

    def scrape_subjects(self, chamber, session):
        form_url = 'http://webserver1.lsb.state.ok.us/WebApplication19/WebForm1.aspx'
        form_html = self.get(form_url).text
        fdoc = lxml.html.fromstring(form_html)

        # bill types
        letter = 'H' if chamber == 'lower' else 'S'
        types = [letter + t for t in self.bill_types]

        session_id = self.metadata['session_details'][session]['session_id']

        # do a request per subject
        for subj in fdoc.xpath('//select[@name="lbxSubjects"]/option/@value'):
            # these forms require us to get hidden session keys
            values = {'cbxInclude': 'All', 'Button1': 'Retrieve',
                      'RadioButtonList1': 'On Any Day',
                      'cbxSessionID': session_id,
                      'lbxSubjects': subj, 'lbxTypes': types}
            for hidden in fdoc.xpath("//input[@type='hidden']"):
                values[hidden.attrib['name']] = hidden.attrib['value']
            #values = urllib.urlencode(values, doseq=True)
            page_data = self.post(form_url, data=values).text
            page_doc = lxml.html.fromstring(page_data)

            # all links after first are bill_ids
            for bill_id in page_doc.xpath('//a/text()')[1:]:
                self.subject_map[bill_id].append(subj)
