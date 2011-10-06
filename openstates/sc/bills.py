import datetime
import os
import re
import sys
import tempfile
import traceback

from .utils import action_type, bill_type, sponsorsToList

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf


import lxml.html

class SCBillScraper(BillScraper):
    state = 'sc'
    urls = {
        'bill-detail' : "http://scstatehouse.gov/cgi-bin/web_bh10.exe?bill1=%s&session=%s" ,
        'vote-url' : "http://www.scstatehouse.gov/php/votehistory.php?type=BILL&session=%s&bill_number=%s",
        'vote-url-base' : "http://www.scstatehouse.gov",

        'lower' : {
          'daily-bill-index': "http://www.scstatehouse.gov/hintro/hintros.htm",
        },

        'upper' : {
          'daily-bill-index': "http://www.scstatehouse.gov/sintro/sintros.htm",
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


    def extract_vote_rows(self, bill_id,fb ):
        vote_data = []

        tables = fb.xpath("//div/div/table")
        if len(tables) > 1:
            fb = tables[1]
            rows = fb.xpath("tr")
        else:
            self.warning("problem handling vote history div")
            return vote_data

        if len(rows) >= 3:
            header_row = rows[0]
            data_row = rows[2]

            rowtd = data_row.xpath("td")
            rowth = header_row.xpath("th")

            for rr in range(2,len(rows)):
                data_row = rows[rr]
                rowtd = data_row.xpath("td")
                item = dict()
                for ii in range(0,len(rowtd)):
                    links = rowtd[ii].xpath("a/@href")
                    if len(links) == 1:
                        #self.debug("item %d LINKS %s s" % (ii, links ) )
                        item['vote_link'] = links[0]

                    key = rowth[ii].text_content()
                    value = rowtd[ii].text_content()
                    item[key] = value

                vote_data.append(item)

        else:
            self.warning("Failed to parse vote hisstory div, expecting 3 rows")
            return []

        self.debug("VOTE_DATA %s returning %d items, %s" %
                   (bill_id, len(vote_data), vote_data))
        return vote_data

    def scrape_vote_history(self, vurl, chamber, bill, bill_id ):
        """Get information from the vote history page.

        The bill title will appear. If this is shorter than the bill title we
        have, add it to the bill.

        Collect data for each vote row, which will have a link to the pdf file
        containing the votes, the motion, the counts (yeas,nays,etc).

        For each vote row, fetch the pdf and extract the votes.  Add this vote
        information to the bill.
        """
        with self.urlopen(vurl) as votepage:
            if votepage.find("No Votes Returned") != -1:
                return

            bill_title_xpath = "//div[@id='votecontent']/div[1]"
            fb_vxpath = '/html/body/table/tbody/tr/td/div[@id="tablecontent"]/table/tbody/tr/td[@class="content"]/div[@id="votecontent"]/div'
            doc = lxml.html.fromstring(votepage)
            doc.make_links_absolute(vurl)

            fb_vote_row = doc.xpath(fb_vxpath)

            if len(fb_vote_row) != 3:
                self.warning("vote history page, expected 3 rows, returning")
                return

            bname = fb_vote_row[0].text_content().strip()
            btitle = fb_vote_row[1].text_content().strip()

            l1 = len(bill['title'])
            l2 = len(btitle)
            if l1 - l2 > 20 and l2 > 4 and l2 < l1:
                self.debug("Bill[%s] Setting title: %s" % (bill_id,btitle))
                #bill['alternate_title'] = btitle
                #bill['short_title'] = btitle
                bill.add_title(btitle)

            vote_details = self.extract_vote_rows(bill_id,fb_vote_row[2])

        #now everyting ins in vote_details
        for d in vote_details:
            try:
                vote_date_time = d['Date/Time']
                motion = d['Motion']
                try:
                    result = d['Result']
                except KeyError:
                    self.warning("Bill[%s] Roll call data has no result %s %s"
                                 % (bill_id, vurl, d))
                    continue

                # Get link to PDF containing roll call votes
                link_to_votes_href = d['vote_link']

                y, no, total_count = int(d['Yeas']), int(d['Nays']), int(d['Total'])

                other_count = total_count - (y + no)
                self.debug("VOTE %s[%s] %s Y/N/Other %d/%d/%d %s %s" %
                           (bill_id, motion, result, y, no, other_count,
                            vote_date_time, link_to_votes_href ) )

                vote_date_1 = vote_date_time.split()
                vote_date = " ".join(vote_date_1)

                vvote_date = datetime.datetime.strptime(vote_date, "%m/%d/%Y %I:%M %p")
                vvote_date = vvote_date.date()

                passed = result.find("Passed") != -1
                vote = Vote(chamber, vvote_date, motion, passed, y, no,
                            other_count)

                if link_to_votes_href:
                    bill.add_source(link_to_votes_href)
                    vote['pdf-source'] = link_to_votes_href
                    vote['source'] = link_to_votes_href
                    self.extract_rollcall_from_pdf(chamber, vote, bill,
                                                   link_to_votes_href, bill_id)
                bill.add_vote(vote)
            except Exception as error:
                self.warning("scrape_vote_history: Failed bill=%s %s %s" %
                             (bill_id, d, traceback.format_exc()))


    def split_page_into_parts(self, data, session, bill_number):
        """
        Data contains the content of a bill detail page.
        Return a tuple containing:
            similar list, summary, after_summary, vote_url
        """

        similar_to_list, after_summary, summary, vurl = [], None, None, None

        sim = re.match("Similar (.+)\n",data)
        if sim:
            for part in sim.group(1).split(","):
                simparts_pat = re.compile('\(<A HREF=".+">(.+)</A>\)')
                #self.debug("VVV CCC Part==[%s]\n========" % part)
                sr = simparts_pat.match(part.strip())
                if sr:
                    similar_to_list.append(sr.group(1))
            data = data[sim.end():]

        bb = data.find("<A HREF")
        if bb != -1:
            summary = re.sub(r'\s+', ' ', data[1:bb])
            after_summary = data[bb:]

            vh = after_summary.find("View Vote History")
            vh1 = after_summary.find("\n")
            #self.debug("VOTE (eol vh1: %d) (votehistory %d)" % (vh1, vh))
            if vh != -1:
                vurl = self.urls['vote-url'] % (session,bill_number)
            if vh1 != -1:
                # skip to end of line
                after_summary = after_summary[vh1:]
        else:
            summary = re.sub(r'\s+', ' ', data)

        return (similar_to_list, summary, after_summary, vurl)


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


    def scrape_details(self, bill_detail_url, session, chamber, bill_id, page):

        data = page

        pat1 = re.compile(r'</FORM>')
        results = pat1.search(data)
        if not results:
            raise ScrapeError("scrape_details(1) - unable to parse |%s|" % 
                              bill_detail_url)

        pre_start = page.find("<pre>",results.start())
        if pre_start == -1:
            self.warning("scrape_details(2) - unable to parse (no <pre>) |%s|\n|%s|"  % (bill_detail_url,page))
            return

        pre_stop = page.find("</pre>",pre_start)
        if pre_stop == -1:
            raise ScrapeError("scrape_details(3) - unable to parse (no </pre>) %s"  % bill_detail_url)

        pre_section = page[pre_start:pre_stop]

        data = pre_section
        vurl = None

        action_line_re = re.compile(r'(\d\d/\d\d/\d\d)\s+(\w+)\s+(.+)')

        pat2 = re.compile(r' By ')
        results = pat2.search(data)
        if results != None:
            bystuff = data[results.start():results.end()]
            data = data[results.end():]

        pat3 = re.compile(r'</b>')
        results1 = pat3.search(data)

        newspon = []
        if results != None and results1 != None:
            spondata = data[:results1.start()]
            mysponsors = sponsorsToList(spondata)
            for s in mysponsors:
                newspon.append(s)
            data = data[results1.end():]

        apat = re.compile(">(H|S) (\d*)<")
        billpat = re.compile("(\d+)")
        bill_number = billpat.search(bill_id).group(0)

        (similar_bills, summary, after_summary,vurl) = self.split_page_into_parts(data,session, bill_number)

        bill_summary = summary.strip().decode('utf8', 'ignore')

        bill = Bill(session, chamber, bill_id, bill_summary,
                    type=bill_type(bill_summary))

        # find versions
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute(bill_detail_url)
        version_url = doc.xpath('//a[text()="View full text"]/@href')[0]
        version_html = self.urlopen(version_url)
        version_doc = lxml.html.fromstring(version_html)
        version_doc.make_links_absolute(bill_detail_url)
        for version in doc.xpath('//a[contains(@href, "/prever/")]'):
            bill.add_version(version.text, version.get('href'))

        # actions
        linenum = 0
        for line in after_summary.splitlines():
            #get rid of the parenthesis
            action_line = line.partition("(")[0].strip()
            #r1 = action_line_re.search(action_line)
            r = action_line_re.search(action_line)

            if r:
                the_date = r.group(1)
                action_chamber = r.group(2)
                action = r.group(3)

                date = datetime.datetime.strptime(the_date, "%m/%d/%y")
                date = date.date()

                t = action_type(action)
                if t == ['other']:
                    self.debug("OTHERACTION: bill %s %d Text[%s] line[%s]" %
                               (bill_id,linenum,action,line))
                else:
                    self.debug("ACTION: %s %d dt|ch|action [%s|%s|%s] [%s]" %
                               (bill_id, linenum, the_date, action_chamber,
                                action, str(t)))

                bill.add_action(chamber, action, date, t)
            elif len(line) > 0:
                self.debug("Skipping line %d [%s] line:[%s]" % (linenum, bill_id, line))

            linenum += 1

        if similar_bills:
            bill['similar'] = similar_bills

        bill.add_source(bill_detail_url)

        for sponsor in newspon:
            bill.add_sponsor("sponsor", sponsor)

        if vurl:
            try:
                self.scrape_vote_history(vurl, chamber, bill, bill_id)
                bill.add_source(vurl)
                self.debug("Scraped votes: (chamber=%s,bill=%s,url=%s)" %
                           (chamber,bill_id,vurl) )
            except Exception as error:
                self.warning("Failed to scrape votes: chamber=%s bill=%s vurl=%s %s" %
                             (chamber,bill_id, vurl, traceback.format_exc()))

        self.save_bill(bill)


    def recap(self, data):
        """Extract bill ids from daily recap page.
        Splits page into sections, and returns list containing bill ids
        """
        # throw away everything before <body>
        start = data.index("<body>")
        stop = data.index("</body>",start)

        bill_id_exp = re.compile(">(?P<id>\w\. \d{1,4}?)</a> \(<a href=")
        billids = set()
        if stop >= 0 and stop > start:
          all = re.compile("/cgi-bin/web_bh10.exe" ).split(data[start:stop])
          for part in all[1:]:
            result = bill_id_exp.search(part)
            if result:
                bill_id = result.group('id')
                billids.add(bill_id)

          return billids

        raise ScrapeError("recap: bad format %s" % data )


    def scrape(self, chamber, session):
        # 1. Get list of days with information by parsing daily url
        #    which will have one link for each day in the session.
        # 2. Scan each of the days and collect a list of bill numbers.
        # 3. Get Bill info.

        index_url = self.urls[chamber]['daily-bill-index']

        days = []
        with self.urlopen(index_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(index_url)
            days = [str(link.attrib['href']) for link in
                    page.find_class('contentlink')]

        self.log("Session days: %d" % len(days))

        # visit each day and extract bill ids
        all_bills = set()

        for dayurl in days:
            self.debug("processing day %s %s" % (dayurl,chamber))
            with self.urlopen(dayurl) as data:
                billids = self.recap(data)
                all_bills |= billids;
                self.debug("  Day count: #bills %d all %d on %s" %
                           (len(billids), len(all_bills), dayurl))

        regexp = re.compile("\d+")
        for bill_id in all_bills:
            pat = regexp.search(bill_id)
            if not pat:
                self.warning("Missing billid [%s]" % bill_id)
                continue

            bn = pat.group(0)
            dtl_url = self.urls['bill-detail'] % (bn,session)

            with self.urlopen(dtl_url) as page:
                self.scrape_details(dtl_url, session, chamber, bill_id, page)

        self.log("Total bills processed: %d : " % len(all_bills))
