import datetime
import os
import re
import sys
import tempfile
import traceback

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

import lxml.html


def action_type(action):
    action = action.lower()
    atypes = []
    if re.match('^read (the )?(first|1st) time', action):
        atypes.append('bill:introduced')
        atypes.append('bill:reading:1')
    elif re.match('^read second time', action):
        atypes.append('bill:reading:2')
    elif re.match('^read third time', action):
        atypes.append('bill:reading:3')

    if re.match('^referred to (the )?committee', action):
        atypes.append('committee:referred')
    elif re.match('^referred to (the )?subcommittee', action):
        atypes.append('committee:referred')

    if re.match('^introduced and adopted', action):
        atypes.append('bill:introduced')
        #not sure if adopted means passed
        atypes.append('bill:passed')
    elif re.match('^introduced and read first time', action):
        atypes.append('bill:introduced')
        atypes.append('bill:reading:1')
    elif re.match('^introduced', action):
        atypes.append('bill:introduced')

    if atypes:
        return atypes

    return ['other']


class SCBillScraper(BillScraper):
    state = 'sc'
    urls = {
        'bill-detail' : "http://scstatehouse.gov/cgi-bin/web_bh10.exe?bill1=%s&session=%s" ,
        'vote-url' : "http://www.scstatehouse.gov/php/votehistory.php?type=BILL&session=%s&bill_number=%s",
        'vote-url-base' : "http://www.scstatehouse.gov",

        'lower' : {
          'daily-bill-index': "http://www.scstatehouse.gov/hintro/hintros.php",
        },

        'upper' : {
          'daily-bill-index': "http://www.scstatehouse.gov/sintro/sintros.php",
        }
    }


    def find_part(self, alist, line, start=0):
        for ii in range(start,len(alist)):
            if line.find(alist[ii]) != -1:
                return ii
        return -1


    def count_votes(self, url,chamber,bill_id,data):
        yays,nays, other, valid_data = [],[],[], False

        house_sections =  ['FIRST', 'RESULT', 'Yeas:', 'YEAS', 'NAYS',
                           'EXCUSED ABSENCE', 'ABSTAIN', 'NOT VOTING', 'REST']
        senate_sections = ['FIRST', 'RESULT', 'Ayes:', 'AYES', 'NAYS',
                           'EXCUSED ABSENCE', 'ABSTAIN', 'NOT VOTING', 'REST']

        result_pat = re.compile("RESULT: (.+)$")

        house_yes_section, hyes = 'YEAS', 'Yeas:'
        senate_yes_section, syes = 'AYES', 'Ayes:'
        yes_section = house_yes_section

        #replace multiple lines with single lines?
        data = re.sub(r'\n+', '\n', data)

        lines = data.split("\n")
        section, linenum, expected, areas = 0, 0, dict(), dict()

        first_line = lines[0].strip()
        if re.match("Senate", first_line):
            sections = senate_sections
            yes_section = senate_yes_section
        elif re.match("House", first_line):
            sections = house_sections
            yes_section = house_yes_section
        elif re.match("Joint", first_line):
            self.warning("Bill[%s] Joint votes not handled: %s " %
                         (bill_id, first_line))
            return (False, expected, areas, yays, nays, other )
        else:
            self.warning("Bill[%s] unknown votes not handled: %s" %
                         (bill_id, first_line))
            return (valid_data, expected, areas, yays, nays, other )

        for s in sections:
            areas[s] = []
            if not s in ['REST','FIRST','RESULT','Yeas:', 'Ayes:']:
                expected[s] = 0


        # Get the result line
        nlines = len(lines)
        result_pat = re.compile("RESULT: (.+)$")
        epat = re.compile("\w - (\d+)")
        #section_header_pat = re.compile("\w - (\d+)")
        done, vresult, vtitle = False, "", ""
        #while linenum < nlines and not done:
        while linenum < nlines and not result_pat.search(lines[linenum]):
            linenum += 1

        if linenum < nlines:
            result_match = result_pat.search(lines[linenum])
            if not result_match:
                self.warning("Bill[%s] failed to get roll call votes, because failed to find RESULT (url=%s)" % (bill_id,url))
                return (valid_data, expected, areas, yays, nays, other )
        else:
            self.warning("(2) Bill[%s] failed to get roll call votes, because failed to find RESULT (url=%s)" % (bill_id,url))
            return (valid_data, expected, areas, yays, nays, other )

        vresult = result_match.group(1)

        # Get the summary line
        # Get the bill title line
        # get the YEAS line, starting adding to YEAS
        done = False
        while linenum < nlines and not done:
            line = lines[linenum]
            if line.find(sections[2]):
                self.debug ("%s %d got VOTE TOTALS section[%s] line|%s|" %
                            (bill_id, linenum, sections[2], line ))
                linenum += 1
                vtitle = lines[linenum]
                done = True
            linenum += 1

        self.debug("%s %d ==> VOTE |%s| |%s| " %
                   (bill_id, linenum, vtitle, vresult))

        current_expected = 0
        done = False
        while linenum < nlines and not done:
            line = lines[linenum]
            result_match = epat.search(lines[linenum])
            if result_match:
                current_expected = int(result_match.group(1))
                expected[ sections[3] ] = current_expected
                done = True
                section = 3
            linenum += 1

        skey = sections[section]

        done = False
        while linenum < nlines and not done:
            line = lines[linenum].strip()

            nn = self.find_part(sections, line, section )
            if nn != -1:

                # get specified value to verify we get them all
                eresult = epat.search(line)
                section_count = 0
                if eresult:
                    section_count = int(eresult.group(1))

                skey = sections[nn]
                expected[ skey ] = section_count

                section = nn

            elif len(line) > 0 and not re.search("Page \d+ of \d+", line):
                # if not page footer (Page x of Y ), add voters
                possible = line.split("  ")
                nonblank = [s.strip() for s in possible if len(s) >0]
                areas[skey].extend(nonblank)

            linenum += 1

        counts_match = True
        counts_in_error = expected_counts_in_error = 0
        area_errors = []
        self.debug ("EXPECTED %s " % expected )
        for k in expected.keys():
            v = areas[k]
            expected_len = expected[k]
            if len(v) != expected[k]:
                self.warning("%s VOTE COUNT FOR %s: Got %d expected %d (%s)" %
                             (bill_id, k, len(v) , expected[k], v ) )
                counts_match = False
                counts_in_error += len(v)
                expected_counts_in_error += expected_len
                area_errors.append(k)

        if counts_match:
            yays = areas[ yes_section ]
            nays = areas['NAYS']
            other = areas['EXCUSED ABSENCE']
            other.extend(areas['NOT VOTING'] )
            other.extend(areas['ABSTAIN'] )
            msg = "SUCCESSFUL (y/n/o) (%d/%d/%d)" % (len(yays), len(nays),
                                                     len(other))
            self.debug("%s %s ROLL_CALL %s: %s" %
                       (bill_id, chamber, msg, url))
            valid_data = True
        else:
            self.warning("%s %s ROLL_CALL FAILED: %s" %
                         (bill_id, chamber, url) )

        return (valid_data, expected, areas, yays, nays, other)


    def extract_rollcall_from_pdf(self,chamber,vote, bill, url,bill_id):
        billnum = re.search("(\d+)", bill_id).group(1)
        self.debug("Scraping rollcall %s|%s|" % (billnum, url))

        bill_prefix = "vote_%s_%s_"  % (chamber, re.sub(r'\s+', '_', bill_id ))

        bill.add_source(url)
        #billnum = re.search("(\d+)", bill_id).group(1)

        # Save roll call pdf to a local file
        temp_file = tempfile.NamedTemporaryFile(delete=False,suffix='.pdf',
                                                prefix=bill_prefix )
        pdf_temp_name = temp_file.name

        self.debug("Parsing pdf votes, saving to tempfile [%s]" %
                   temp_file.name)
        with self.urlopen(url) as pdata:
            pdf_file = file(pdf_temp_name, 'w')
            pdf_file.write(pdata)
            pdf_file.close()

        # Pdf is in pdf_temp_name
        rollcall_data  = convert_pdf(pdf_temp_name, type='text')
        (valid_data, expected, areas, yays, nays, other) = self.count_votes(url,chamber,bill_id,rollcall_data)

        os.unlink(pdf_temp_name)

        if valid_data:
            self.debug("VOTE %s %s yays %d nays %d other %d pdf=%s" %
                       (bill_id, chamber, len(yays), len(nays), len(other),
                        pdf_temp_name ))
            [vote.yes(legislator) for legislator in yays]
            [vote.no(legislator) for legislator in nays]
            [vote.other(legislator) for legislator in other]


    def scrape_vote_history(self, bill, vurl):
        html = self.urlopen(vurl)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(vurl)

        # skip first two rows
        for row in doc.xpath('//table/tr')[2:]:
            (timestamp, motion, vote, yeas, nays,
             nv, exc, abst, total, result) = row.getchildren()

            timestamp = timestamp.text.replace(u'\xa0', ' ')
            timestamp = datetime.datetime.strptime(timestamp,
                                                   '%m/%d/%Y %H:%M %p')
            yeas = int(yeas.text)
            nays = int(nays.text)
            others = int(nv.text) + int(exc.text) + int(abst.text)
            assert yeas + nays + others == int(total.text)

            passed = (result.text == 'Passed')

            vote_link = vote.xpath('a')[0]
            if '[H]' in vote_link.text:
                chamber = 'lower'
            else:
                chamber = 'upper'

            vote = Vote(chamber, timestamp, motion.text, passed, yeas, nays,
                        others)
            vote.add_source(vurl)

            # TODO: handle roll call

            bill.add_vote(vote)


    def process_rollcall(self,chamber,vvote_date,bill,bill_id,action):
        self.debug("508 Roll call: [%s]" % action )
        if re.search(action,'Ayes'):
            pat1 = re.compile('<a href="(.+)" target="_blank">Ayes-(\d+)\s+Nays-(\d+)</a>')
        else:
            pat1 = re.compile('<a href="(.+)" target="_blank">Yeas-(\d+)\s+Nays-(\d+)</a>')
        sr1 = pat1.search(action)
        if not sr1:
            self.debug("515 Roll call: NO MATCH " )
            return

        the_link = sr1.group(1)
        the_ayes = sr1.group(2)
        the_nays = sr1.group(3)

        vbase = self.urls['vote-url-base']
        vurl = "%s%s" % (self.urls['vote-url-base'], the_link)
        self.debug("VOTE 512 Roll call: link [%s] AYES [%s] NAYS[%s] vurl[%s]"
                   % (the_link, the_ayes, the_nays, vurl ))

        motion = "some rollcall action"
        yes_count = int(the_ayes)
        no_count = int(the_nays)
        other_count = 0
        passed = True
        vote = Vote(chamber, vvote_date, motion, passed, yes_count, no_count,
                    other_count)
        self.extract_rollcall_from_pdf(chamber,vote, bill,vurl,bill_id)
        self.debug("2 ADD VOTE %s" % bill_id)
        bill.add_vote(vote)


    def scrape_details(self, bill_detail_url, session, chamber, bill_id):
        page = self.urlopen(bill_detail_url)

        if 'INVALID BILL NUMBER' in page:
            self.warning('INVALID BILL %s' % bill_detail_url)
            return

        doc = lxml.html.fromstring(page)
        doc.make_links_absolute(bill_detail_url)

        bill_div = doc.xpath('//div[@style="margin:0 0 40px 0;"]')[0]

        bill_type = bill_div.xpath('span/text()')[0]

        if 'General Bill' in bill_type:
            bill_type = 'bill'
        elif 'Concurrent Resolution' in bill_type:
            bill_type = 'concurrent resolution'
        elif 'Joint Resolution' in bill_type:
            bill_type = 'joint resolution'
        elif 'Resolution' in bill_type:
            bill_type = 'resolution'
        else:
            raise ValueError('unknown bill type: %s' % bill_type)

        # this is fragile, but less fragile than it was
        b = bill_div.xpath('./b[text()="Summary:"]')[0]
        bill_summary = b.getnext().tail.strip()

        bill = Bill(session, chamber, bill_id, bill_summary, type=bill_type)

        # sponsors
        for sponsor in doc.xpath('//a[contains(@href, "member.php")]/text()'):
            bill.add_sponsor('sponsor', sponsor)

        # find versions
        version_url = doc.xpath('//a[text()="View full text"]/@href')[0]
        version_html = self.urlopen(version_url)
        version_doc = lxml.html.fromstring(version_html)
        version_doc.make_links_absolute(version_url)
        for version in version_doc.xpath('//a[contains(@href, "/prever/")]'):
            bill.add_version(version.text, version.get('href'))

        # actions
        for row in bill_div.xpath('table/tr'):
            date_td, chamber_td, action_td = row.xpath('td')

            date = datetime.datetime.strptime(date_td.text, "%m/%d/%y")
            action_chamber = {'Senate':'upper',
                              'House':'lower',
                              None: 'other'}[chamber_td.text]

            action = action_td.text_content()
            action = action.split('(House Journal')[0]
            action = action.split('(Senate Journal')[0]

            atype = action_type(action)
            bill.add_action(action_chamber, action, date, atype)


        # votes
        vurl = doc.xpath('//a[text()="View Vote History"]/@href')
        if vurl:
            vurl = vurl[0]
            self.scrape_vote_history(bill, vurl)

        bill.add_source(bill_detail_url)
        self.save_bill(bill)


    def scrape(self, chamber, session):
        index_url = self.urls[chamber]['daily-bill-index']
        chamber_letter = 'S' if chamber == 'upper' else 'H'

        page = self.urlopen(index_url)
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute(index_url)

        # visit each day and extract bill ids
        days = doc.xpath('//div/b/a/@href')
        for day_url in days:
            data = self.urlopen(day_url)
            doc = lxml.html.fromstring(data)
            doc.make_links_absolute(day_url)

            for bill_a in doc.xpath('//p/a[1]'):
                bill_id = bill_a.text
                if bill_id.startswith(chamber_letter):
                    self.scrape_details(bill_a.get('href'), session, chamber,
                                        bill_id)
