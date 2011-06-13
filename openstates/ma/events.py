
from billy.scrape.events import EventScraper, Event

from BeautifulSoup import BeautifulSoup

import datetime
import re

class MAEventScraper(EventScraper):
    state = 'ma'

    def scrape(self, chamber, session):

        if chamber != 'upper': return

        page = self.urlopen('http://www.malegislature.gov/Events/Hearings')
        soup = BeautifulSoup(page)

        events = []

        foundEvents = soup.findAll('tr')
        for foundEvent in foundEvents:
            linkTags = foundEvent.findAll('a')
            tdTags = foundEvent.findAll('td')
            if len(tdTags) == 6 or len(tdTags) == 7:
                events.append(foundEvent)

        for thisEvent in events:

            linkTags = thisEvent.findAll('a')
            tdTags = thisEvent.findAll('td')

            eventRec = {}

            tds = len(tdTags)

            if tds == 7:
                monthTag = thisEvent.findNext('span', { 'class' : 'month' })
                monthStr = re.sub('\.$', '', monthTag.string)

                dayTag = thisEvent.findNext('span', { 'class' : 'day' })
                dayStr = dayTag.string

                yearStr = format(datetime.date.today().year, 'd')

            linkTags = thisEvent.findAll('a')
         
            eventRec['source'] = linkTags[0]['href']
            eventRec['committee'] = linkTags[0].string

            # Remove some of the garbage from the committee names.
            #
            found = re.search(', pt\.', eventRec['committee'])
            if found is not None:
                eventRec['committee'] = eventRec['committee'][:found.start()]

            found = re.search(' \- [A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}$', eventRec['committee'])
            if found is not None:
                eventRec['committee'] = eventRec['committee'][:found.start()]

            timeStr = tdTags[tds-4].string
     
            eventRec['when'] = datetime.datetime.strptime(yearStr + ' ' + monthStr + ' ' + dayStr + ' ' + timeStr, "%Y %b %d %I:%M %p")

            if tdTags[tds-3].string is not None:
                eventRec['location'] = tdTags[tds-3].string
            else:
                eventRec['location'] = 'House Chambers'

            event = Event(session, eventRec['when'], 'committee:meeting', eventRec['committee'], eventRec['location'])

            event.add_participant('committee', eventRec['committee'])

            self.save_event(event)

