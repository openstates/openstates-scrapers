
from BeautifulSoup import BeautifulSoup

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill

from datetime import datetime

import re

# Go to: http://www.malegislature.org
# Click on "Bills"
# Leave search criteria on "187th Session (2011-2012)" and nothing else:
#
# URL: http://www.malegislature.gov/Bills/SearchResults?Input.Keyword=&Input.BillNumber=&
#           Input.GeneralCourtId=1&Input.City=&Input.DocumentTypeId=&Input.CommitteeId=&x=102&y=18

class MABillScraper(BillScraper):
    state = 'ma'

    def scrape(self, chamber, session):

        # we only need to go through this once
        #
        if chamber == 'upper': return

        self.validate_session(session)

        # print 'session: '+session

        # an <option> with the session in it gives me a number to use in the search below.
        #
        page = self.urlopen('http://www.malegislature.gov/Bills/Search')
        soup = BeautifulSoup(page)
        optionsFound = soup.findAll('option')
        for optionFound in optionsFound:
            if optionFound.string == session:
                sessionSelectValue = optionFound['value']

        urls = {}
        titles = {}
        subjects = {}
        altSubjects = {}

        beginBlanks = re.compile("^\s+")
        endBlanks = re.compile("\s+$")

        houseBill = re.compile("^H")
        senateBill = re.compile("^S")

        bills = {}

        # -------------
        # Just one bill, using the scrape_ma_bill call directly. Need to set up: title, subject, altSubject
        #
        # bills['H00048'] = {}
        # bills['H00048']['title'] = 'H00048'
        # bills['H00048']['altSubject'] = 'By Ms. Jennifer  E. Benson of Lunenburg, petition (accompanied by bill, House, No. 00048) of ...'
        # bills['H00048']['source'] = 'http://malegislature.gov/Bills/187/House/H00048'

        # self.scrape_ma_bill('187th Session(2011-2012)', 'H00048', bills, 'http://malegislature.gov/Bills/187/House/H00048')
        # return
        # --------------

        # Uncomment this in order to get the list of all the bills to process.
        #
        page = self.urlopen('http://www.malegislature.gov/Bills/SearchResults?Input.GeneralCourtId='+sessionSelectValue+'&perPage=50000')

        # Uncomment this in order to get a shortened list of about ten bills (one page - partial search results)
        #
        # page = self.urlopen('http://www.malegislature.gov/Bills/SearchResults?Input.GeneralCourtId='+sessionSelectValue)

        # Process the search result page. I can get the title here also. Should I rather just get the id and pass this on? We will see.
        #
        # Note that, in the search results, we have first a shortest title, which is really the id. Then we have a short title, which we
        # will probably throw away. Then we have the longer title, which we use as the title. If the longer title is missing, I am
        # attempting to use the shorter title. I am not sure that this comes up.:w

        soup = BeautifulSoup(page)
        linksFound = soup.findAll('a', attrs={'href' : re.compile("^/Bills/")})

        for linkFound in linksFound:
            id = linkFound['title']
            if re.match("^[H|S]\d+$", id):
                if id not in bills: bills[id] = {}

                bills[id]['source'] = 'http://www.malegislature.gov'+linkFound['href']

                if re.match(houseBill, id): bills[id]['chamber'] = 'lower'
                if re.match(senateBill, id): bills[id]['chamber'] = 'upper'

                if 'title' not in bills[id]:
                    bills[id]['title'] = linkFound.string
                    bills[id]['title'] = re.sub(beginBlanks, '', re.sub(endBlanks, '', bills[id]['title']))
                else:
                    if 'subject' not in bills[id]:
                        bills[id]['subject'] = linkFound.string
                        bills[id]['subject'] = re.sub(beginBlanks, '', re.sub(endBlanks, '', bills[id]['subject']))
                    else:
                        bills[id]['altSubject'] = linkFound.string
                        bills[id]['altSubject'] = re.sub(beginBlanks, '', re.sub(endBlanks, '', bills[id]['altSubject']))

        print 'titles:'
        for id in bills:
            self.scrape_ma_bill(session, id, bills, bills[id]['source'])

    def scrape_ma_bill(self, session, id, bills, url):
 
        if re.match("^H", id): chamber = 'lower'
        if re.match("^S", id): chamber = 'upper'

        realTitle = ''

        if 'altSubject' in bills[id]:
            realTitle = bills[id]['altSubject']
        elif 'subject' in bills[id]:
            realTitle = bills[id]['subject']

        bill = Bill(session, chamber, id, realTitle, subjects=[], type='bill')

        bill.add_source(bills[id]['source'])

        # For setting the chamber of the action. There is going to be a better way to do this.
        #
        # See the headers="bBranch", below.
        #
        chamberAlt = {}
        chamberAlt['House'] = 'lower'
        chamberAlt['Senate'] = 'upper'
        chamberAlt['Joint'] = 'joint'

        page = self.urlopen(bills[id]['source'])
        # print page
        soup = BeautifulSoup(page)

        # Find and record bill actions. Each bill action looks like this in the page:
        #     <tr>
        #         <td headers="bDate">1/14/2011</td>
        #         <td headers="bBranch">House</td>
        #         <td headers="bAction">Bill Filed.</td>
        #     </tr>
        #
        actionsFound = soup.findAll('td', attrs={'headers' : "bDate"})
        for actionDate in actionsFound:
            actionActor = actionDate.findNext('td')
            action = actionActor.findNext('td')
            bill.add_action(chamberAlt[actionActor.string], action.string, datetime.strptime(actionDate.string, "%M/%d/%Y"))

        sponsors = {}

        billDetailTags = soup.findAll('div', { "id" : "billDetail" })
        for billDetailTag in billDetailTags:
            peopleTags = billDetailTag.findAll('a', href=re.compile("^/People/"))
            for person in peopleTags:
                if re.match("^Sponsors:", person.parent.contents[0].string):
                    sponsors[person['title']] = 'author';
                else:
                    if person['title'] not in sponsors:
                        sponsors[person['title']] = 'coauthor';

        # I tried to, as I was finding the sponsors above, detect whether a sponsor was already known. One has
        # to do this because an author is listed in the "Sponsors:" section and then the same person will be listed
        # with others in the "Petitioners:" section. We are guessing that "Sponsors" are authors and
        # "Petitioners" are co-authors. Does this make sense?

        for name in sponsors:
            bill.add_sponsor(sponsors[name], name)

        # Now I should be able to get the bill text and put it in "+text". What else to do with it?
        #
        billTextTags = soup.findAll('div', { "id" : "billText" })

        # When I get the line below, what I want to say is: 
        #
        #    if line is of class 'BeautifulSoup.NavigableString' and not 'BeautifulSoup.Tag'.
        #
        # Since I cannot figure out the syntax to say this right, I have to do this complicated crap....

        brTag = soup.findAll('br')[0]
        aTag = soup.findAll('a')[0]

        lastWasTag = False

        output = []
        fixedOutput = []

        for billTextTag in billTextTags:
            for line in billTextTag.contents:

                if not isinstance(line, brTag.__class__) and not isinstance(line, aTag.__class__):
                    if not re.match("^\s$", line):
                        output.append(line)

        for line in output:
            line = line.strip()
            fixedOutput.append(line)

        textValue = "\n".join(fixedOutput)
        bill['+text'] = textValue

        self.save_bill(bill)

