import re
import pytz
import hashlib
import datetime
import lxml.html

from billy.scrape.events import EventScraper, Event

# the committee abbreviations are in the urls. this is for 
# looking up committees if the name isn't in the meeting page.
cmte_lookup = {
    'lower' : (
        {'cmte_abbv' : 'AGR', 'cmte_name' : 'Agriculture'},                                                                                                                                                                      
        {'cmte_abbv' : 'CPC', 'cmte_name' : 'Consumer Protection & Commerce'},
        {'cmte_abbv' : 'COHDWS', 'cmte_name' : 'County of Hawaii Department of Water Supply' },
        {'cmte_abbv' : 'CUA', 'cmte_name' : 'Culture & the Arts'},
        {'cmte_abbv' : 'EBM', 'cmte_name' : 'Economic Revitalization, Business and Military Affairs'},
        {'cmte_abbv' : 'EDN', 'cmte_name' : 'Education'},
        {'cmte_abbv' : 'EEP', 'cmte_name' : 'Energy & Environmental Protection'},
        {'cmte_abbv' : 'ERB', 'cmte_name' : 'Economic Revitalization & Business'},
        {'cmte_abbv' : 'FIN', 'cmte_name' : 'Finance'},
        {'cmte_abbv' : 'HAW', 'cmte_name' : 'Hawaiian Affairs'},
        {'cmte_abbv' : 'HED', 'cmte_name' : 'Higher Education'},
        {'cmte_abbv' : 'HLT', 'cmte_name' : 'Health'},
        {'cmte_abbv' : 'HSG', 'cmte_name' : 'Housing'},
        {'cmte_abbv' : 'HUS', 'cmte_name' : 'Human Services'},
        {'cmte_abbv' : 'INT', 'cmte_name' : 'International Affairs'},
        {'cmte_abbv' : 'JUD', 'cmte_name' : 'Judiciary'},
        {'cmte_abbv' : 'LAB', 'cmte_name' : 'Labor & Public Employment'},
        {'cmte_abbv' : 'LMG', 'cmte_name' : 'Legislative Management'},
        {'cmte_abbv' : 'PBM', 'cmte_name' : 'Public Safety & Military Affairs'},
        {'cmte_abbv' : 'TOU', 'cmte_name' : 'Tourism'},
        {'cmte_abbv' : 'TRN', 'cmte_name' : 'Transportation'},
        {'cmte_abbv' : 'WLO', 'cmte_name' : 'Water, Land, & Ocean Resources'}
    ),
    'upper' : (
        {'cmte_abbv' : 'AGL', 'cmte_name' : 'Agriculture'},
        {'cmte_abbv' : 'CPN', 'cmte_name' : 'Commerce and Consumer Protection'},
        {'cmte_abbv' : 'CSGTF', 'cmte_name' : 'Charter School Governance, Accountability, and Authority Task Force'},
        {'cmte_abbv' : 'EDU', 'cmte_name' : 'Education'},
        {'cmte_abbv' : 'EGH', 'cmte_name' : 'Economic Development, Government Operations and Housing'},
        {'cmte_abbv' : 'EDT', 'cmte_name' : 'Economic Development and Technology'},
        {'cmte_abbv' : 'ENE', 'cmte_name' : 'Energy and Environment'},
        {'cmte_abbv' : 'HMS', 'cmte_name' : 'Human Services'},
        {'cmte_abbv' : 'HRE', 'cmte_name' : 'Higher Education'},
        {'cmte_abbv' : 'HTH', 'cmte_name' : 'Health'},
        {'cmte_abbv' : 'HWN', 'cmte_name' : 'Hawaiian Affairs'},
        {'cmte_abbv' : 'JDL', 'cmte_name' : 'Judiciary and Labor'},
        {'cmte_abbv' : 'PGM', 'cmte_name' : 'Public Safety, Government Operations, and Military Affairs'},
        {'cmte_abbv' : 'PSM', 'cmte_name' : 'Public Safety, Intergovernmental and Military Affairs'},
        {'cmte_abbv' : 'TEC', 'cmte_name' : 'Technology and the Arts'},
        {'cmte_abbv' : 'THA', 'cmte_name' : 'Tourism and Hawaiian Affairs'},
        {'cmte_abbv' : 'TIA', 'cmte_name' : 'Transportation and International Affairs'},
        {'cmte_abbv' : 'TSM', 'cmte_name' : 'Tourism'},
        {'cmte_abbv' : 'SCA01', 'cmte_name' : 'Special Committee On Accountability - 1'},
        {'cmte_abbv' : 'SCA02', 'cmte_name' : 'Special Committee On Accountability - 2'},
        {'cmte_abbv' : 'WAM', 'cmte_name' : 'Ways and Means'},
        {'cmte_abbv' : 'WTL', 'cmte_name' : 'Water and Land'},
        {'cmte_abbv' : 'WLH', 'cmte_name' : 'Water, Land, and Housing'}
    ),
    'joint' : (
        {'cmte_abbv' : 'ESPO', 'cmte_name' : 'Economic Stimulus Program Oversight'},
        {'cmte_abbv' : 'IFTF', 'cmte_name' : 'Illegal Fireworks Task Force'},
        {'cmte_abbv' : 'MBTF', 'cmte_name' : 'Medicaid Buy-In Task Force'},
        {'cmte_abbv' : 'SLARS', 'cmte_name' : 'Student Loan Auction Rate Securities'}
    )
}

class HIEventScraper(EventScraper):
    jurisdiction = 'hi'

    _tz = pytz.timezone('US/Hawaii')

    def get_page_from_url(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def get_meetings(self, year):

        base_url = "http://www.capitol.hawaii.gov/session%s/hearingnotices/" % str(year)
        files_page = self.get_page_from_url(base_url)

        meetings = []

        for file in files_page.xpath('//a[contains(@href,".htm")]'):

            meeting_url = file.attrib['href']
            
            if self.is_summary_page(meeting_url=meeting_url):
                continue

            if re.search('/CONF_', meeting_url, re.I):
                continue

            meeting_page = self.get_page_from_url(meeting_url)

            if self.is_summary_page(meeting_page=meeting_page):
                continue

            # occasionally, pages have different filenames yet contain the exact same data, skip these
            # example:
            # http://www.capitol.hawaii.gov/session2013/hearingnotices/HEARING_WAM_01-03-13_PM_INFO_.htm
            # http://www.capitol.hawaii.gov/session2013/hearingnotices/HEARING_WAM_01-03-13_INFO_PM_.htm
            meeting_page_md5 = self.get_md5_for_page(meeting_page)

            already_processed = [meeting['md5'] for meeting in meetings]

            if meeting_page_md5 in already_processed:
                continue
            else:
                meetings.append({
                    'meeting_url' : meeting_url,
                    'md5' : meeting_page_md5,
                    'meeting_page' : meeting_page
                })

        return meetings

    def get_cmte_abbvs(self, url):
        
        committees = []

        # replace hyphen before date with underscore
        if re.search(r'-[0-9]{1,2}-[0-9]{1,2}-[0-9]+_',url):
            date = re.search(r'-([0-9]{1,2}-[0-9]{1,2}-[0-9]+)_', url).group(1)
            url = re.sub(r'-[0-9]{1,2}-[0-9]{1,2}-[0-9]+_', '_' + date + '_', url)

        if re.search(r'_SEN-HSE_', url):
            url = url.replace('_SEN-HSE_','_')

        if re.search(r'hearingnotices/[^_]+_[^_]+_', url):
            committee_string = re.search(r'hearingnotices/[^_]+_([^_]+)_', url).group(1)
            committees = committee_string.split('-')
        return committees

    def get_bills(self, page):

        bills = []

        bills_xpath = '//table[@class="MsoNormalTable"]/tr[td[p[a[' \
            'contains(@href, "/Bills/") or ' \
            'contains(@href, "/bills/")]]]]'
        
        for tr in page.xpath(bills_xpath):
            bill_description = tr.xpath('.//td[2]')[0]
            bill_description = self.clean_string(bill_description.text_content())
            for bill in tr.xpath('.//a[contains(@href,"/Bills/") or contains(@href,"/bills/")]'):
                bill_url = bill.attrib['href']
                bill_id = self.clean_string(bill.text_content())
                bills.append({
                    'bill_id' : bill_id,
                    'bill_url' : bill_url,
                    'bill_description' : bill_description
                })

        return bills


    def get_meeting_info(self, page):

        meeting_info = {
            'DATE' : None,
            'TIME' : None,
            'PLACE' : None
        }

        info_xpath = '//div[@align="center"]/table[@class="MsoNormalTable"]/tr[td//text()[contains(., "%s:")]]/td[2]' \
            '|' \
            '//div[@align="center"]/table[@class="MsoNormalTable"]/tbody/tr[td//text()[contains(., "%s:")]]/td[2]'

        for item in meeting_info.keys():
            item_xpath =  info_xpath % (item,item)

            item_value = page.xpath(item_xpath)[0]
            item_value = self.clean_string(item_value.text_content())

            if item == 'TIME':
                item_value = self.normalize_time(item_value)
            elif item == 'DATE':
                item_value = self.normalize_date(item_value)

            meeting_info[item] = item_value

        return meeting_info	

    def get_md5_for_page(self, page):

        text = ''

        for el in page.findall("*"):
            text += el.text_content().strip().encode('ascii','ignore')
        h = hashlib.md5(text)

        return h.hexdigest()

    def is_summary_page(self, **kwargs):

        if 'meeting_url' in kwargs.keys():
            if 'SUMMARY_INFO' in kwargs['meeting_url']:
                return True
        elif 'meeting_page' in kwargs.keys():
            td = kwargs['meeting_page'].xpath('//div[@class="Section1"]/table['
                '@class="MsoNormalTable" and @border="1"][1]/tr[1]/td'
            )
            if td:	
                summary_header = " ".join([i.text_content().strip().upper() for i in td])
                if 'DATE TIME LOCATION SUBJECT' == summary_header:
                    return True

        return False
        
    def clean_string(self, my_string):

        my_string = my_string.encode('ascii','ignore')
        my_string = re.sub(r'(\n|\r\n)',' ', my_string)
        my_string = re.sub(r'\s{2,}',' ', my_string)
        my_string = my_string.strip()

        return my_string

    def normalize_time(self, time_string):

        time_string = time_string.lower()
        time_string = time_string.replace(' to completion','')
        time_string = time_string.replace(' completion','')
        time_string = time_string.replace(' please note time change','')
        time_string = time_string.replace('-',' ')
        time_string = time_string.replace('.', '')
        time_string = time_string.replace('12:00 noon', '12:00 pm')
        time_string = time_string.replace(';',':')
        time_string = time_string.replace(' ','')
        
        no_space_pattern = "([0-9])([ap]m)"

        if re.search(no_space_pattern, time_string):
            time_string = re.sub(no_space_pattern, lambda m: ' '.join('%s' % s for s in m.groups()), time_string)

        time_string = self.clean_string(time_string)

        if re.search(r'^[0-9]{1,2}:[0-9]{2} [ap]m', time_string):
            hour_minutes, meridiem = re.search(r'^([0-9]{1,2}:[0-9]{2}) ([ap]m)', time_string).groups()
            new_time = hour_minutes + ' ' + meridiem
        else:
            # a few edge cases which tend to occur about dozen times per term
            #10 am,2:3pm,2:45,11:15:am
            new_time = '12:00 am'
 
        return new_time

    def normalize_date(self, date_string):

        date_string = date_string.replace(',', '')
        date_string = date_string.replace('.', '')

        if re.search(r'[0-9]{5,}$', date_string):
            day, year = re.search(r'([0-9]{1,2})([0-9]{4})$', date_string).groups()
            date_string = re.sub(r'[0-9]{5,}$', day + ' ' + year, date_string)

        # a couple of edges cases. safe to remove after scraping historical data.
        if re.search(r'\[1011\] ', date_string):
            date_string = date_string.replace('[1011] ', '')

        if date_string == 'Friday February 28 25 2011':
            date_string = 'Friday February 25 2011'
        if date_string == 'March 18 2011':
            date_string = 'Friday March 18 2011'
        if date_string == 'Thursday April 7':
            date_string = 'Thursday April 7 2011'
        if date_string == 'Saturday February12 2011':
            date_string = 'Saturday February 12 2011'
        if date_string == 'Wednesday 14 March 2012':
            date_string = 'Wednesday March 14 2012'
    
        # meeting rescheduled. pick the last day.
        # examples
        # Friday February 10 2012 Monday February 13 2012
        # Tuesday February 21 2012 Wednesday February 22 2012
        # Tuesday February 28 2012 Wednesday February 29 2012
        dates_regex = re.compile('((Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) '
            '(January|February|March|April|May|June|July|August|September|October|November|December) '
            '[0-9]{1,2} '
            '[0-9]{4})')
        date_matches = dates_regex.findall(date_string)
        if len(date_matches) == 2:
            date_string = date_matches[len(date_matches)-1][0]

        return date_string

    def get_chamber_cmte_type(self, committees):
    
        chambers = []

        for committee in committees:
            if committee in [c['cmte_abbv'] for c in cmte_lookup['lower']]:
                chambers.append('House')
            if committee in [c['cmte_abbv'] for c in cmte_lookup['upper']]:
                chambers.append('Senate')
            if committee in [c['cmte_abbv'] for c in cmte_lookup['joint']]:
                chambers.append('Joint')

        chambers = set(chambers)

        if len(chambers) == 1:
            return chambers.pop()
        elif len(chambers) > 1:
            return 'Joint'
        else:
            return ''

    def get_chamber_from_cmte_abbv(self,cmte_abbv):

        for chamber in cmte_lookup.keys():
            for cmte_abbvs in cmte_lookup[chamber]:
                if cmte_abbv == cmte_abbvs['cmte_abbv']:
                    return chamber

        return None		

    def get_description(self, committees):

        committee_string = ''

        committees = set(committees)
        for committee in committees:
            committee_string += ', ' + committee 
        committee_string = self.clean_string(committee_string).lstrip(', ')

        return committee_string

    def get_committee_name_from_cmte_abbv(self, cmte_abbv):

        committee_name = ''

        for cmte in cmte_lookup['lower'] + cmte_lookup['upper'] + cmte_lookup['joint']:
            if cmte_abbv == cmte['cmte_abbv']:
                committee_name = cmte['cmte_name']
                break

        return committee_name

    def get_committees(self, meeting_page):

        committees = []

        for committee in meeting_page.xpath(
            './/a[contains(normalize-space(text()),"COMMITTEE ON")]' 
            '|'
            ' .//u[contains(normalize-space(text()),"COMMITTEE ON")]'
        ):
            committee = self.clean_string(committee.text_content())
            if committee == '':
                continue
            committee = committee.replace('COMMITTEE ON ','')
            committees.append(committee)
        return committees		

    def scrape(self, term, chambers):

        years = []

        if term == 'other':
            return
        for meta_term in self.metadata['terms']:
            if term in meta_term['sessions']:
                if int(meta_term['start_year']) <= int(datetime.date.today().year):
                    years.append(meta_term['start_year'])
                if int(meta_term['end_year']) <= int(datetime.date.today().year):
                    years.append(meta_term['end_year'])

        for year in years:
            meetings = self.get_meetings(year)

            for meeting in meetings:
                meeting_page = meeting['meeting_page']
                meeting_url = meeting['meeting_url']

                committees = self.get_committees(meeting_page)

                if len(committees) == 0:
                    for committee_abbv in self.get_cmte_abbvs(meeting_url):
                        committee = self.get_committee_name_from_cmte_abbv(committee_abbv)
                        committees.append(committee)

                description = self.get_description(committees)

                meeting_info = self.get_meeting_info(meeting_page)
                bills = self.get_bills(meeting_page)

                meeting_date_time = datetime.datetime.strptime(
                    meeting_info['DATE'] + ' ' + meeting_info['TIME'],
                    '%A %B %d %Y %I:%M %p'
                )
                meeting_date_time = self._tz.localize(meeting_date_time)
                
                location = meeting_info['PLACE']

                event = Event(
                    term,
                    meeting_date_time,
                    'committee:meeting',
                    description,
                    location
                )

                event.add_source(meeting_url)

                for committee in committees:
                    event.add_participant(
                        type='host',
                        participant=committee,
                        participant_type='committee',
                    )

                for bill in bills:
                    event.add_related_bill(
                        bill_id=bill['bill_id'],
                        description=bill['bill_description'],
                        type='consideration'
                    )
                    event.add_document(
                        name=bill['bill_id'],
                        url=bill['bill_url'],
                        type='bill',
                    )

                self.save_event(event)

