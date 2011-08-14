import scrapelib
import lxml.html


def _get_url(url):
    return lxml.html.fromstring(scrapelib.urlopen(url))

def ak_session_info():
    doc = _get_url('http://www.legis.state.ak.us/basis/start.asp')
    sessions = doc.xpath('//ul')[-1].xpath('li/a/nobr/text()')
    return sessions, sessions[0]

def az_session_info():
    doc = _get_url('http://www.azleg.gov/xml/sessions.asp?sort=SessionID')
    sessions = doc.xpath('//session/@session_full_name')
    doc = _get_url('http://www.azleg.gov/')
    current = doc.xpath('//font[@class="headerlinks"]/text()').strip()
    return sessions, current

def ar_session_info():
    current = ' '.join(doc.xpath('//div[@id="ctl00_headerLogo"]/a/text()'))
    # can't get old sessions
    return [], current

def ca_session_info():
    return [], "CA runs from a SQL database"

def ct_session_info():
    html = scrapelib.urlopen("ftp://ftp.cga.ct.gov")
    sessions = [line.split()[-1] for line in html.splitlines()]
    sessions.pop()    # remove pub/
    return sessions, sessions[-1]

def fl_session_info():
    doc = _get_url('http://www.myfloridahouse.gov/Sections/Bills/bills.aspx')
    sessions = doc.xpath('//select[@name="ctl00$ContentPlaceHolder1$ctrlContentBox$ctrlPageContent$ctl00$ddlSession"]/option/text()')
    return sessions, sessions[0]

def hi_session_info():
    doc = _get_url('http://www.capitol.hawaii.gov/site1/archives/archives.asp')
    sessions = doc.xpath('//li/a/text()')
    # hard to get current session, but if it changes sessions should change
    return sessions, 'current session'

def in_session_info():
    # cool URL bro
    doc = _get_url('http://www.in.gov/legislative/2414.htm')
    sessions = doc.xpath('//h3/text()')
    # hard to get current session, but if it changes sessions should change
    return sessions, 'current session'

def la_session_info():
    doc = _get_url('http://www.legis.state.la.us/session.htm')
    sessions = [x.text_content() for x in doc.xpath('//strong')]
    return sessions, sessions[0]

def md_session_info():
    doc = _get_url('http://mlis.state.md.us/other/PriorSession/index.htm')
    sessions = doc.xpath('//table')[1].xpath('.//th/text()')
    # hard to get current session, but if it changes sessions should change
    return sessions, 'current session'

def mi_session_info():
    doc = _get_url('http://www.legislature.mi.gov/mileg.aspx?page=LegBasicSearch')
    sessions = doc.xpath('//option/text()')
    return sessions, sessions[0]

def mn_session_info():
    doc = _get_url('https://www.revisor.mn.gov/revisor/pages/search_status/status_search.php?body=House')
    sessions = doc.xpath('//select[@name="session"]/option/text()')
    return sessions, sessions[0]

def ms_session_info():
    doc = _get_url('http://billstatus.ls.state.ms.us/sessions.htm')
    sessions = doc.xpath('//a/text()')
    return sessions, sessions[0]

def nv_session_info():
    doc = _get_url('http://www.leg.state.nv.us/Session/')
    sessions = [x.text_content() for x in doc.xpath('//*[@class="MainHeading"]')]
    return sessions, sessions[0]

def nj_session_info():
    doc = _get_url('http://www.njleg.state.nj.us/')
    sessions = doc.xpath('//select[@name="DBNAME"]/option/text()')
    return sessions, sessions[0]

def ny_session_info():
    doc = _get_url('http://assembly.state.ny.us/leg/')
    sessions = doc.xpath('//option/text()')
    return sessions, sessions[0]

def nc_session_info():
    doc = _get_url('http://www.ncleg.net')
    sessions = doc.xpath('//select[@name="sessionToSearch"]/option/text()')
    return sessions, sessions[0]

def oh_session_info():
    doc = _get_url('http://www.legislature.state.oh.us/search.cfm')
    sessions = doc.xpath('//form[@action="bill_search.cfm"]//input[@type="RADIO" and @name="SESSION"]/@value')
    return sessions, sessions[0]

def pa_session_info():
    doc = _get_url('http://www.legis.state.pa.us/cfdocs/legis/home/session.cfm')
    sessions = doc.xpath('//select[@id="BTI_sess"]/option/text()')
    return sessions, sessions[0]

def sd_session_info():
    doc = _get_url('http://legis.state.sd.us/PastSessions.aspx')
    sessions = doc.xpath('//span[@class="link"]/text()')

# tx, ut, vt, va, wa, dc, wi
