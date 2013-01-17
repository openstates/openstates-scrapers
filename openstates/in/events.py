import re
import pytz
import datetime
import lxml.html

from billy.scrape.utils import convert_pdf
from billy.scrape.events import EventScraper, Event

class INEventScraper(EventScraper):
    jurisdiction = 'in'

    _tz = pytz.timezone('America/Indiana/Indianapolis')

    # scrape pdf or txt (lowercase). pdf is preferred since data from txt files, from IN, appear to be getting truncated
    # it isn't clear yet which may be the better route, if not a completely different solution
    #http://www.in.gov/legislative/reports/2013/BSCHDS.TXT
    #http://www.in.gov/legislative/reports/2013/BSCHDS.PDF
    scrape_mode = 'pdf' 

    def get_page_from_url(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def get_committee(self, meeting_data):

        committee = ''
        committee_data = meeting_data[0]

        committee_regex = re.compile('^(\s+)?AGENDA FOR\s+:\s+(.*)', re.I)
    
        if re.search(committee_regex, committee_data):
            if self.scrape_mode == 'txt':
                committee = re.search(committee_regex,committee_data).group(2)
            elif self.scrape_mode == 'pdf':
                committee = re.search(r': (.*?) (January|February|March|April|May|June|July|August|September|October|November|December) [0-9]+,',
                    committee_data).group(1)
            committee = committee.strip()

        return committee

    def get_meeting_info(self, meeting_data):

        meeting_info = {
            'date': '',
            'time' : '',
            'location' : ''
        }

        date_regex = re.compile('((January|February|March|April|May|June|July|August|September|October|November|December) [0-9]+)')

        for data in meeting_data:
            if (self.scrape_mode == 'txt' and re.search(r'^\s+MEETING\s+:', data)) or \
                (self.scrape_mode == 'pdf' and re.search(r'^Agenda for\s:\s+', data)):
            
                if self.scrape_mode == 'pdf':
                    orig_data = data[:]
                    data = date_regex.split(data)
                    data = orig_data.replace(data[0], '')[:]

                    # hack to insert a time if none exists
                    if not re.search(r'[0-9]{1,2}:[0-9]{2} [AP]', data, re.I):
                        if re.search(r'upon adjournment,', data, re.I):
                            adjourn_reg = re.compile(r'upon adjournment,', re.I)
                            data = adjourn_reg.sub('', data)
                        date = date_regex.search(data).group(1)
                        date_regex = re.compile(date_regex.pattern + ',')
                        data = date_regex.sub(date + ', 12:00 am,', data)
                elif self.scrape_mode == 'txt':
                    data = re.sub('^\s+MEETING\s+:\s+','', data)

                for i,item in enumerate(data.split(',')):
                    item_value = item.strip()

                    if i == 0:
                        meeting_info['date'] = item_value
                    elif i == 1:
                        item_value = self.normalize_time(item_value)
                        meeting_info['time'] = item_value
                    elif i == 2:
                        meeting_info['location'] = item_value
                break

        # if room wasn't found on the line we expected, search the entire meeting
        if not meeting_info['location']:
            for data in meeting_data:
                if re.search('ROOM [0-9A-Z ]+', data, re.I):
                    meeting_info['location'] = re.search('(ROOM [0-9A-Z ]+)', data, re.I).group(1)
                    break
        if not meeting_info['location']:
            meeting_info['location'] = 'Unavailable'

        return meeting_info

    def normalize_time(self, time_string):
        
        time_string = time_string.lower()

        if time_string == '':
            time_string = '12:00 am'
        if re.search(r'upon adjournment', time_string):
            time_string = '12:00 am'
        if re.search(r' [ap]$', time_string):
            time_string += 'm'

        return time_string

    def get_bills(self, meeting_data, session):

        bills = []

        bills_start, bills_end = [0,0]
        for i, data in enumerate(meeting_data):
            if re.search(r'HEARING\s+:', data, re.I):
                bills_start = i
            if re.search(r'SENATE COMMITTEE SCHEDULE', data, re.I) and bills_start > 0:
                bills_end = i
                break

        if bills_end > 0:				
            bills_data = meeting_data[bills_start:bills_end]
        else:
            bills_data = meeting_data[bills_start:]

        for bill_data in bills_data:
            bill_data = bill_data.strip()

            if bill_data == '':
                continue

            # clean up
            hearing_reg = re.compile(r'(\s+)?Hearing\s+:\s+', re.I)
            if re.search(hearing_reg, bill_data):
                bill_data = hearing_reg.sub('', bill_data)
            
            if re.search(r'^([A-Z]{2,4}\s+[0-9]+)', bill_data):

                bill_id = re.search(r'^([A-Z]{2,4}\s+[0-9]+)', bill_data).group(1).strip()
                bill_id = re.sub(r'\s{2,}', ' ', bill_id)
    
                bill_meta = self.get_bill_intro_meta(session, bill_id)

                bills.append({
                    'bill_id' : bill_id,
                    'bill_url' : bill_meta['bill_url'],
                    'bill_description' : bill_meta['bill_description']	
                })
                
        return bills

    def get_bill_intro_meta(self, session, bill_id):

        intro_meta = {
            'bill_url': '',
            'bill_description' : ''
        }

        bill_num = bill_id.split(' ')[1]
        bill_intro_url = 'http://www.in.gov/legislative/bills/%s/IN/IN%s.1.html' % (session, bill_num)

        bill_intro_page = self.get_page_from_url(bill_intro_url)

        # b synopsis elements are missing sometimes so get it with regex
        intro_text = ''
        for el in bill_intro_page.findall("*"):				
            intro_text += ' ' + el.text_content().replace('\n', ' ')

        # only the first sentence
        bill_description = re.search(r'Synopsis:\s+(.*?)\.\s+', intro_text).group(1)
        
        intro_meta['bill_description'] = bill_description
        intro_meta['bill_url'] = bill_intro_url
        
        return intro_meta

    def get_participants(self, meeting_data):

        participants = []

        for data in meeting_data:
            if re.search('CHAIRMAN\s+:', data, re.I):
                chair_name = re.search(r'(\s+)?CHAIRMAN\s+:\s+(.*)', data, re.I).group(2).strip()
                participants.append({
                    'type' : 'chair',
                    'participant' : chair_name,
                    'participant_type' : 'legislator'
                })

        # find out what rows member start and end on
        members_start, members_end = [0,0]
        start_regex = re.compile(r'MEMBERS\s+:', re.I)
        end_regex = re.compile(r'^\s{14}[A-Z]')

        for i, data in enumerate(meeting_data):
            if start_regex.search(data):
                members_start = i
            if end_regex.search(data) and members_start > 0:
                members_end = i+1
                break

        members_string = ''
        member_names = []

        for members_data in meeting_data[members_start:members_end]:
    
            members_data = members_data.strip()
    
            if members_data == '':
                continue

            time_reg = re.compile(r'[0-9]+:[0-9]+ [AP]M', re.I)
            if re.search(time_reg, members_data):
                members_data = time_reg.sub('', members_data).strip()

            member_header_reg = re.compile(r'^(\s+)?Members\s+:\s+', re.I)

            if re.search(member_header_reg, members_data):
                members_data = member_header_reg.sub('', members_data)

            if re.search(r'\.$', members_data):
                members_data = re.sub(r'\.$', ',', members_data)

            members_string += ' ' + members_data

        members_string = members_string.replace('- ', '-').strip(',')
        member_names = [member.strip() for member in members_string.split(',')]

        for member_name in member_names:
    
            participants.append({
                'type' : 'participant',
                'participant' : member_name,
                'participant_type' : 'legislator'
            })
        
        cmte_name = self.get_committee(meeting_data)
        participants.append({
            'type' : 'host',
            'participant' : cmte_name,
            'participant_type' : 'committee'
        })

        return participants
        

    def scrape(self, chamber, session):

        if chamber == 'other':
            return 

        if str(session) != '2013':
            self.error("Events for the %s session are not implemented." % str(session))	
            
        meetings_url = "http://www.in.gov/legislative/reports/%s/BSCHD%s.%s" % (
            str(session),
            str(self.metadata['chambers'][chamber]['name'])[0].upper(),
            self.scrape_mode.upper())
        
        if self.scrape_mode.lower() == 'pdf':
            (path, response) = self.urlretrieve(meetings_url)
            meetings_data = convert_pdf(path, type='text').encode('ascii','ignore')

        elif self.scrape_mode.lower() == 'txt':
            meetings_data = self.urlopen(meetings_url).encode('ascii','ignore')

        meetings_data = meetings_data.split("\n")

        meeting_idents = []

        for i, line in enumerate(meetings_data):

            if re.search(r'^(\s+)?AGENDA FOR\s:', line, re.I):
                meeting_idents.append(i)

        for i, meeting_ident in enumerate(meeting_idents):
            
            if i == len(meeting_idents) - 1: 
                start_ident, end_ident = [meeting_ident, 0]
                meeting_data = meetings_data[start_ident:]
            else:
                start_ident, end_ident = [meeting_ident, meeting_idents[i+1]-1]
                meeting_data = meetings_data[start_ident:end_ident]

            canceled = set([1 if re.search(r'MEETING HAS BEEN CANCELED', data, re.I) else 0 
                for data in meeting_data])
            if 1 in canceled:
                continue

            meeting_info = self.get_meeting_info(meeting_data)

            location = meeting_info['location']
            meeting_date_time = datetime.datetime.strptime(
                meeting_info['date'] + ' ' + str(session) + ' ' + meeting_info['time'],
                '%B %d %Y %I:%M %p')
            meeting_date_time = self._tz.localize(meeting_date_time)
            
            committee = self.get_committee(meeting_data)
            description = committee

            event = Event(
                session,
                meeting_date_time,
                'committee:meeting',
                description,
                location
            )

            event.add_source(meetings_url)

            for participant in self.get_participants(meeting_data):
                event.add_participant(**participant)
                                
            for bill in self.get_bills(meeting_data,session):

                event.add_related_bill(
                    bill_id = bill['bill_id'],
                    description = bill['bill_description'],
                    type='consideration'	
                )

                event.add_document(
                    name = bill['bill_id'],
                    url = bill['bill_url'],
                    type = 'bill'
                )
    
            self.save_event(event)

