import re
import pytz
import datetime
import lxml.html

from billy.scrape.events import EventScraper, Event

class INEventScraper(EventScraper):
    jurisdiction = 'in'

    _tz = pytz.timezone('US/Central')

    def get_page_from_url(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def get_committee(self, meeting_data):

        committee = ''
        committee_data = meeting_data[0]

        committee_regex = re.compile('^   AGENDA FOR :  (.*)')
    
        if re.search(committee_regex, committee_data):
            committee = re.search(committee_regex,committee_data).group(1)

        return committee.strip()

    def get_meeting_info(self, meeting_data):

        meeting_info = {
            'date': '',
            'time' : '',
            'location' : ''
        }

        for data in meeting_data:

            if re.search(r'^\s+MEETING\s+:', data):
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

        bills_ident = 0
        for i, data in enumerate(meeting_data):
            if re.search(r'HEARING\s+:', data):
                bills_ident = i
                break

        bills_data = meeting_data[bills_ident:]

        bill_regex = re.compile(r'^(\s+HEARING\s+:\s+|\s{18})([A-Z]{2,4}\s+[0-9]+)\s+')

        for bill_data in bills_data:
            if re.search(bill_regex, bill_data):
                
                bill_id = re.search(bill_regex, bill_data).group(2).replace('  ', ' ')
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
            if re.search(r'^\s+(CHAIRMAN|MEMBERS|AGENDA FOR)\s+:', data):
                if 'CHAIRMAN' in data:
                    chair_name = re.search(r'\s+CHAIRMAN\s+:\s+([^\s]+)', data).group(1)
                    participants.append({
                        'type' : 'chair',
                        'participant' : chair_name,
                        'participant_type' : 'legislator'
                    })
                elif 'MEMBERS' in data:
                    leg_names = re.search(r'^\s+MEMBERS\s+:\s+(.*)', data).group(1).encode('ascii','ignore').strip().strip(',')
                    leg_names = [leg_name.strip() for leg_name in leg_names.split(',')]
                    for leg_name in leg_names:
                        participants.append({
                            'type' : 'participant',
                            'participant' : leg_name,
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

        # the pages for older sessions exist but don't have any data - odd. perhaps it still exists in that format, somewhere.
        # http://www.in.gov/legislative/reports/2012/BSCHDH.TXT
        # http://www.in.gov/legislative/reports/2011/BSCHDS.TXT
        # http://www.in.gov/legislative/reports/2011/BSCHDH.PDF

        # some older years do have data.
        # google search inurl:in.gov "BSCHDS.TXT" OR "BSCHDH.TXT" and you will see

        # although heavier to consumer, the PDF's might be a better route as they also contain more data.
        # probably wise to not enable, see if the 2013 files are updated in the coming weeks, and/or use another method 
        # http://www.in.gov/legislative/reports/2013/BSCHDS.PDF

        if str(session) != '2013':
            self.error("Events for the %s session are not implemented." % str(session))	
            
        meetings_url = "http://www.in.gov/legislative/reports/%s/BSCHD%s.TXT" % (str(session), str(self.metadata['chambers'][chamber]['name'])[0].upper())
        
        meetings_data = self.urlopen(meetings_url)
        meetings_data = meetings_data.split("\n")

        meeting_idents = []

        for i, line in enumerate(meetings_data):
            if re.search(r'AGENDA FOR :', line):
                meeting_idents.append(i)

        for i, meeting_ident in enumerate(meeting_idents):
            
            if i == len(meeting_idents) - 1: 
                start_ident, end_ident = [meeting_ident, 0]
                meeting_data = meetings_data[start_ident:]
            else:
                start_ident, end_ident = [meeting_ident, meeting_idents[i+1]-1]
                meeting_data = meetings_data[start_ident:end_ident]

            meeting_info = self.get_meeting_info(meeting_data)
            location = meeting_info['location']
            meeting_date_time = datetime.datetime.strptime(meeting_info['date'] + ' ' + str(session) + ' ' + meeting_info['time'], '%B %d %Y %I:%M %p')
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
    
            #pp.pprint(event)

            self.save_event(event)

