import re
import pytz
import datetime

from billy.scrape.events import EventScraper, Event
from openstates.utils import LXMLMixin

class WYEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'wy'
    _tz = pytz.timezone('US/Mountain')

    def normalize_time(self, time_string):

        time_string = time_string.lower()

        if re.search(r'(upon|after)(\?)? adjournment', time_string):
            time_string = '12:00 am'
        elif re.search(r'(noon (adjournment|recess)|afternoon)', time_string):
            time_string = '12:00 pm'

        if re.search(r'[ap]\.m\.', time_string):
            ap = re.search(r'([ap])\.m\.', time_string).group(1)
            time_string = time_string.replace(ap + '.m.', ap + 'm')

        if re.search(r'[0-9]{1,2}:[0-9]{1,2}[ap]m', time_string):
            hour_minutes, meridiem = re.search(
                r'([0-9]{1,2}:[0-9]{1,2})([ap]m)', time_string).groups()
            time_string = hour_minutes + ' ' + meridiem

        if re.search(
            r'^[0-9]{1,2}:[0-9]{1,2} [ap]m', time_string
        ) and not re.search(r'^[0-9]{1,2}:[0-9]{1,2} [ap]m$', time_string):
            time_string = re.search(
                r'^([0-9]{1,2}:[0-9]{1,2} [ap]m)', time_string).group(1)

        if not re.search(r'^[0-9]{1,2}:[0-9]{1,2} [ap]m$', time_string):
            # if at this point it doesn't match our format return 12:00 am
            time_string = '12:00 am'
        return time_string

    def get_meeting_time(self, meeting_data):
        meeting_time = meeting_data[0].xpath(
            './/p[@class="MsoNormal"]')[0].text_content().strip()
        meeting_time = self.normalize_time(meeting_time)
        return meeting_time

    def get_committee(self, meeting_data):
        committee = meeting_data[0].xpath(
            './/p[@class="MsoNormal"]')[1].text_content().strip()
        if committee == '':
            committee = None
        else:
            committee = re.sub(r'^[0-9]+-','',committee)
            committee = self.clean_string(committee)

        return committee

    def get_location(self, meeting_data):
        tr = meeting_data[0].xpath('.//p[@class="MsoNormal"]')
        room = tr[len(tr)-1].text_content().strip()

        room = self.clean_string(room)
        if room == '':
            room = None

        return room

    def get_meeting_description(self, meeting_data):
        descriptions = ''
        if len(meeting_data) > 1:
            start_at = 1
        else:
            start_at = 0

        for tr in meeting_data[start_at:]:
            description = tr[len(tr)-2].text_content().strip()
            descriptions += ' ' + description

        descriptions = self.clean_string(descriptions).strip()

        return descriptions

    def get_bills(self, meeting_data):

        bill_data = []

        for tr in meeting_data:
            bills = tr.xpath('.//a[contains(@href, "/Bills/")]')
            if bills:
                for bill in bills:
                    bill_id = bill.text_content().strip()
                    bill_description = self.clean_string(
                        tr.xpath('.//td[3]/p')[0].text_content().strip())
                    bill_url = bill.attrib['href'].strip()  #pdf file

                    # dont include bad HTML links for bills. thankfully
                    # they're duplicates and already listed properly
                    if 'href' not in bill_url and '</a>' not in bill_url:
                        bill_data.append({
                            'bill_id': bill_id,
                            'bill_description' : bill_description,
                            'bill_url' : bill_url
                        })
        return bill_data

    def clean_string(self, my_string):
        my_string = my_string.encode('ascii','ignore')
        my_string = re.sub(r'(\n|\r\n)',' ', my_string)
        my_string = re.sub(r'\s{2,}',' ', my_string)
        my_string = my_string.strip()

        return my_string

    def is_row_a_new_meeting(self, row):
        if len(row) == 3:
            td1 = row.xpath('.//td[1]/p[@class="MsoNormal"]')
            td2 = row.xpath('.//td[2]/p[@class="MsoNormal"]')
            td3 = row.xpath('.//td[3]/p[@class="MsoNormal"]')

            if len(td2) == 0:
                td2 = row.xpath('.//td[2]/h1')

            if len(td1) == 0 or len(td2) == 0:
                return False

            if (self.clean_string(td1[0].text_content()) == ''
                    or self.clean_string(td2[0].text_content()) == ''
                    or self.clean_string(td3[0].text_content()) == ''):
                return False
        else:
            return False
        return True

    def scrape(self, chamber, session):
        if chamber == 'other':
            return

        calendar_url = ("http://legisweb.state.wy.us/%s/Calendar/"
            "CalendarMenu/CommitteeMenu.aspx" % str(session))

        page = self.lxmlize(calendar_url)

        rows = page.xpath('//table[@id="ctl00_cphContent_gvCalendars"]/tr')

        for i,row in enumerate(rows):

            row_ident = '%02d' % (i + 2)

            date_xpath = ('.//span[@id="ctl00_cphContent_gv'
                'Calendars_ctl%s_lblDate"]' % str(row_ident))
            date_string = row.xpath(date_xpath)[0].text_content()

            chamber_char = self.metadata['chambers'][chamber]['name'][0].upper()
            meeting_xpath = ('.//a[@id="ctl00_cphContent_gv'
                'Calendars_ctl%s_hl%scallink"]' % (
                    str(row_ident), chamber_char
                ))
            meeting_url = row.xpath(meeting_xpath)

            if (len(meeting_url) == 1 and
                    meeting_url[0].text_content().strip() != ''):
                try:
                    meeting_url = meeting_url[0].attrib['href']
                except KeyError:
                    self.warning(
                            "Alleged meeting date has no URL: " +
                            meeting_url[0].text_content().strip()
                            )
                    continue

                meeting_page = self.lxmlize(meeting_url)
                meetings = meeting_page.xpath(
                    './/table[@class="MsoNormalTable"]/tr')
                meeting_idents = []
                meeting_ident = 0

                # breaking the meetings into arrays (meeting_data) for
                # processing. meeting_ident is the first row of the meeting
                # (time, committee, location)
                for meeting in meetings:
                    if self.is_row_a_new_meeting(meeting):
                        meeting_idents.append(meeting_ident)
                    meeting_ident += 1

                for i,meeting_ident in enumerate(meeting_idents):

                    if len(meeting_idents) == 1 or i + 1 == len(meeting_idents):
                        ident_start, ident_end = [meeting_ident, 0]
                        meeting_data = meetings[ident_start:]
                    else:
                        ident_start, ident_end = [
                            meeting_ident, meeting_idents[i+1] - 1
                        ]

                        if ident_end - ident_start == 1:
                            ident_end = ident_start + 2

                        meeting_data = meetings[ident_start:ident_end]
                    committee = self.get_committee(meeting_data)
                    meeting_time = self.get_meeting_time(meeting_data)
                    meeting_date_time = datetime.datetime.strptime(
                        date_string + ' ' + meeting_time, '%m/%d/%Y %I:%M %p')
                    meeting_date_time = self._tz.localize(meeting_date_time)

                    location = self.get_location(meeting_data)
                    description = self.get_meeting_description(meeting_data)
                    bills = self.get_bills(meeting_data)

                    if description == '':
                        description = committee

                    event = Event(
                        session,
                        meeting_date_time,
                        'committee:meeting',
                        description,
                        location
                    )

                    event.add_source(meeting_url)

                    for bill in bills:

                        if bill['bill_description'] == '':
                            bill['bill_description'] = committee

                        event.add_related_bill(
                            bill_id=bill['bill_id'],
                            description=bill['bill_description'],
                            type='consideration'
                        )
                        event.add_document(
                            name=bill['bill_id'],
                            url=bill['bill_url'],
                            type='bill',
                            mimetype='application/pdf'
                        )

                    event.add_participant(
                        type='host',
                        participant=committee,
                        participant_type='committee',
                        chamber=chamber
                    )

                    self.save_event(event)
