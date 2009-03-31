import urllib, re, sys
from BeautifulSoup import BeautifulSoup as BS
sys.path.insert(0, '../pyutils')
from legislation import LegislationScraper, NoDataForYear

def cleansource(data):
    '''Remove some irregularities from WV's HTML.

It includes a spurious </HEAD> before the useful data begins and lines like '<option value="Bill"selected="selected">Bill</option>', in which the lack of a space between the attributes confuses BeautifulSoup.
'''
#' <- emacs crud
    data = data.replace('</HEAD>', '')
    return re.sub('(="[^"]+")([a-zA-Z])', r'\1 \2', data)

def cleansponsor(sponsor):
    if sponsor.endswith('President)'):
        ## in the senate:
        ## Soandso (Salutation President)
        return sponsor.split(' ')[0]
    if ' Speaker' in sponsor: # leading space in case there is a Rep. Speaker
        ## in the house:
        ## Salutation Speaker (Salutation Soandso)
        return sponsor.split(' ')[-1][:-1]
    return sponsor

def issponsorlink(a):
    return a['title'].startswith('View bills Delegate') or \
           a['title'].startswith('View bills Senator')

def sessionexisted(data):
    return not re.search('Please choose another session', data)

urlbase = 'http://www.legis.state.wv.us/Bill_Status/%s'

class WVLegislationScraper(LegislationScraper):
    state = 'wv'
    sessions = 'RS 1X 2X 3X 4X 5X 6X 7X'.split()
    def scrape_session(self, chamber, session, year):
        if chamber == 'upper': c = 's'
        else:                  c = 'h'
        q = 'Bills_all_bills.cfm?year=%s&sessiontype=%s&btype=bill&orig=%s' % (year, session, c)
        data = urllib.urlopen(urlbase % q).read()
        if not sessionexisted(data):
            return False
        soup = BS(cleansource(data))
        rows = soup.findAll('table')[1].findAll('tr')[1:]
        for row in rows:
            histlink = urlbase % row.td.a['href']
            billid = row.td.a.contents[0].contents[0]
            self.scrape_bill(chamber, session, billid, histlink, year)
        return True

    def scrape_bills(self, chamber, year):
        if int(year) < 1993:
            raise NoDataForYear
        for session in self.sessions:
            if not self.scrape_session(chamber, session, year):
                return

    def scrape_bill(self, chamber, session, billid, histurl, year):
        session = '%s %s' % (year, session) # a fiction.
        data = urllib.urlopen(histurl).read()
        soup = BS(cleansource(data))
        basicinfo = soup.findAll('div', id='bhistleft')[0]
        hist = basicinfo.table
        for b in basicinfo.findAll('b'):
            if b.next.startswith('SUMMARY'):
                title = b.findNextSiblings(text=True)[0].strip()
                self.add_bill(chamber, session, billid, title)
            elif b.next.startswith('SPONSOR'):
                for a in b.findNextSiblings('a'):
                    if not issponsorlink(a):
                        break
                    sponsor = cleansponsor(a.contents[0])
                    self.add_sponsorship(chamber, session, billid, 'primary', sponsor)
        for row in hist.findAll('tr'):
            link = row.td.a
            vlink = urlbase % link['href']
            vname = link.contents[0].strip()
            self.add_bill_version(chamber, session, billid, vname, vlink)
        history = soup.findAll('div', id='bhisttab')[0].table
        rows = history.findAll('tr')[1:]
        for row in rows:
            date, action = row.findAll('td')[:2]
            date = date.contents[0]
            action = action.contents[0].strip()
            if 'House' in action:
                actionchamber = 'lower'
            elif 'Senate' in action:
                actionchamber = 'upper'
            else: # for lack of a better
                actionchamber = chamber
            self.add_action(chamber, session, billid, actionchamber, action, date)

if __name__ == '__main__':
    WVLegislationScraper().run()
