import re
import datetime
import collections
import lxml.html
import scrapelib
from urllib import parse
from pupa.scrape import Scraper, Bill, VoteEvent as Vote
from .actions import Categorizer


class OKBillScraper(Scraper):
    bill_types = ['B', 'JR', 'CR', 'R']
    subject_map = collections.defaultdict(list)

    categorizer = Categorizer()

    meta_session_id = {
        '2011-2012': '1200',
        '2012SS1': '121X',
        '2013SS1': '131X',
        '2013-2014': '1400',
        '2015-2016': '1600',
        '2017SS1': '171X',
        '2017SS2': '172X',
        '2017-2018': '1800',
    }

    def scrape(self, chamber=None, session=None, only_bills=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)
        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session, only_bills)

    def scrape_chamber(self, chamber, session, only_bills):
        # start by building subject map
        self.scrape_subjects(chamber, session)

        url = "http://webserver1.lsb.state.ok.us/WebApplication3/WebForm1.aspx"
        form_page = lxml.html.fromstring(self.get(url).text)

        if chamber == 'upper':
            chamber_letter = 'S'
        else:
            chamber_letter = 'H'

        session_id = self.meta_session_id[session]
        self.debug("Using session slug `{}`".format(session_id))
        values = {'cbxSessionId': session_id,
                  'cbxActiveStatus': 'All',
                  'RadioButtonList1': 'On Any day',
                  'Button1': 'Retrieve'}

        lbxTypes = []
        for bill_type in self.bill_types:
            lbxTypes.append(chamber_letter + bill_type)
        values['lbxTypes'] = lbxTypes

        for hidden in form_page.xpath("//input[@type='hidden']"):
            values[hidden.attrib['name']] = hidden.attrib['value']

        page = self.post(url, data=values).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        bill_nums = []
        for link in page.xpath("//a[contains(@href, 'BillInfo')]"):
            bill_id = link.text.strip()
            bill_num = int(re.findall(r'\d+', bill_id)[0])
            if bill_num >= 9900:
                self.warning('skipping likely bad bill %s' % bill_id)
                continue
            if only_bills is not None and bill_id not in only_bills:
                self.warning('skipping bill we are not interested in %s' % bill_id)
                continue
            bill_nums.append(bill_num)
            yield from self.scrape_bill(chamber, session, bill_id, link.attrib['href'])

    def scrape_bill(self, chamber, session, bill_id, url):
        try:
            page = lxml.html.fromstring(self.get(url).text)
        except scrapelib.HTTPError as e:
            self.warning('error (%s) fetching %s, skipping' % (e, url))
            return

        title = page.xpath(
            "string(//span[contains(@id, 'PlaceHolder1_txtST')])").strip()
        if not title:
            self.warning('blank bill on %s - skipping', url)
            return

        if 'JR' in bill_id:
            bill_type = ['joint resolution']
        elif 'CR' in bill_id:
            bill_type = ['concurrent resolution']
        elif 'R' in bill_id:
            bill_type = ['resolution']
        else:
            bill_type = ['bill']

        bill = Bill(bill_id,
                    legislative_session=session,
                    chamber=chamber,
                    title=title,
                    classification=bill_type)
        bill.add_source(url)
        bill.subject = self.subject_map[bill_id]

        for link in page.xpath("//a[contains(@id, 'Auth')]"):
            name = link.xpath("string()").strip()

            if ':' in name:
                raise Exception(name)
            if 'otherAuth' in link.attrib['id']:
                bill.add_sponsorship(name, classification='cosponsor',
                                     entity_type='person', primary=False)
            else:
                bill.add_sponsorship(name, classification='primary',
                                     entity_type='person', primary=True)

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

            attrs = self.categorizer.categorize(action)
            related_entities = []
            for item in attrs['committees']:
                related_entities.append({
                    'type': 'committee',
                    'name': item
                })
            for item in attrs['legislators']:
                related_entities.append({
                    'type': 'legislator',
                    'name': item
                })
            bill.add_action(description=action,
                            date=date.strftime('%Y-%m-%d'),
                            chamber=actor,
                            classification=attrs['classification'],
                            related_entities=related_entities)

        version_table = page.xpath("//table[contains(@id, 'Versions')]")[0]
        # Keep track of already seen versions to prevent processing duplicates.
        version_urls = []
        for link in version_table.xpath(".//a[contains(@href, '.PDF')]"):
            version_url = link.attrib['href']
            if version_url in version_urls:
                self.warning('Skipping duplicate version URL.')
                continue
            else:
                version_urls.append(version_url)
            name = link.text.strip()

            if re.search('COMMITTEE REPORTS|SCHEDULED CCR', version_url, re.IGNORECASE):
                bill.add_document_link(note=name, url=version_url,
                                       media_type='application/pdf')
                continue

            bill.add_version_link(note=name, url=version_url,
                                  media_type='application/pdf')

        for link in page.xpath(".//a[contains(@href, '_VOTES')]"):
            if 'HT_' not in link.attrib['href']:
                yield from self.scrape_votes(bill, self.urlescape(link.attrib['href']))

        # # If the bill has no actions and no versions, it's a bogus bill on
        # # their website, which appears to happen occasionally. Skip.
        has_no_title = (bill.title == "Short Title Not Found.")
        if has_no_title:
            # If there's no title, this is an empty page. Skip!
            return

        else:
            # Otherwise, save the bills.
            yield bill

    def scrape_votes(self, bill, url):
        page = lxml.html.fromstring(self.get(url).text.replace(u'\xa0', ' '))

        seen_rcs = set()

        re_ns = "http://exslt.org/regular-expressions"
        path = r"//p[re:test(text(), 'OKLAHOMA\s+(HOUSE|STATE\s+SENATE)')]"
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
            if not motion.strip():
                self.warning("Motion text not found")
                return
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

            if rcs in seen_rcs:
                continue
            else:
                seen_rcs.add(rcs)

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
                regex = (r'(YEAS|NAYS|EXCUSED|VACANT|CONSTITUTIONAL '
                         r'PRIVILEGE|NOT VOTING|N/V)\s*:\s*(\d+)(.*)')
                match = re.match(regex, line)
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
                        self.warning("Bad vote format, skipping.")
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

            vote = Vote(chamber=chamber,
                        start_date=date.strftime('%Y-%m-%d'),
                        motion_text=motion,
                        result='pass' if passed else 'fail',
                        bill=bill,
                        classification='passage')
            vote.set_count('yes', counts['yes'])
            vote.set_count('no', counts['no'])
            vote.set_count('other', counts['other'])
            vote.pupa_id = url + '#' + rcs

            vote.add_source(url)

            for name in votes['yes']:
                vote.yes(name)
            for name in votes['no']:
                if ':' in name:
                    raise Exception(name)
                vote.no(name)
            for name in votes['other']:
                vote.vote('other', name)

            yield vote

    def scrape_subjects(self, chamber, session):
        form_url = 'http://webserver1.lsb.state.ok.us/WebApplication19/WebForm1.aspx'
        form_html = self.get(form_url).text
        fdoc = lxml.html.fromstring(form_html)

        # bill types
        letter = 'H' if chamber == 'lower' else 'S'
        types = [letter + t for t in self.bill_types]

        session_id = self.meta_session_id[session]

        # do a request per subject
        for subj in fdoc.xpath('//select[@name="lbxSubjects"]/option/@value'):
            # these forms require us to get hidden session keys
            values = {'cbxInclude': 'All', 'Button1': 'Retrieve',
                      'RadioButtonList1': 'On Any Day',
                      'cbxSessionID': session_id,
                      'lbxSubjects': subj, 'lbxTypes': types}
            for hidden in fdoc.xpath("//input[@type='hidden']"):
                values[hidden.attrib['name']] = hidden.attrib['value']
            # values = urllib.urlencode(values, doseq=True)
            page_data = self.post(form_url, data=values).text
            page_doc = lxml.html.fromstring(page_data)

            # all links after first are bill_ids
            for bill_id in page_doc.xpath('//a/text()')[1:]:
                self.subject_map[bill_id].append(subj)

    def urlescape(self, url):
        scheme, netloc, path, qs, anchor = parse.urlsplit(url)
        path = parse.quote(path, '/%')
        qs = parse.quote_plus(qs, ':&=')
        return parse.urlunsplit((scheme, netloc, path, qs, anchor))
