from lxml import html, cssselect
import re, datetime
doc_for_bills_url = 'http://www.azleg.gov/DocumentsForBill.asp?Bill_Number=%s&Session_ID=%s'
base_url = 'http://www.azleg.gov/'
select_session_url = 'http://avilrockroadorg/SelectSession.asp.html'

def parse_link_id(link):
    return link.get('href')[link.get('href').find("'") + 1 : link.get('href').rfind("'")]
    
def get_action(abbr):
    """
    get_action('PFCA W/FL') --> 
    'proper for consideration amended with recommendation for a floor amendment'
    """
    return action[abbr]

def get_bill_type(bill_prefix):
    """
    takes a bill prefix and returns a bill type.
    bill_id = sb1004
    get_bill_type(bill_id[:-4]) --> bill
    """
    prefix = bill_prefix.lower()
    for x in bill_types:
        if x[0] == prefix:
            return x[1]
            
def text_to_number(num):
    """
    Takes 'Forty-SiXth' and returns 46
    """
    num = num.lower().replace('-', ' ').split()
    total = 0
    for x in num:
        for y in word_key:
            if x == y[0]:
                total = total + int(y[1])
    return total
    
def legislature_to_number(leg):
    """
    Takes a full session and splits it down to the values for 
    FormatDocument.asp.
    
    session = 'Forty-ninth Legislature - First Special Session'
    legislature_to_number(session) --> '49Leg/1s'
    """
    l = leg.lower().replace('-', ' ').split()
    session = [x[1] for y in l for x in word_key if x[0] == y]
    if len(session) == 4:
        return '%dLeg/%s%s' % (int(session[0]) + int(session[1]), session[2], session[3])
    else:
        return '%sLeg/%s%s' % (session[0], session[1], session[2])
        
def get_date(elem):
    """
    Returns the date object or an empty string, silly but it will really save 
    some typing since a table might have a date field or it might be empty
    """
    try:
        return_date = datetime.datetime.strptime(elem.text_content().strip(), '%m/%d/%y')
    except ValueError:
        return_date = elem.text_content().strip() or ''
    return return_date
    
def img_check(elem):
    """
    Checks if the cell contains an image and returns true or false
    used to see if a calendar was modified revised or cancelled.
    """
    img = elem.xpath('img')
    if img:
        return 'Y'
    else:
        text = elem.text_content().strip()
        if text:
            return 'Y'
        else:
            return 'N'
def get_href(elem):
    href = elem.xpath('string(a/@href)')
    if href:
        return href
    else:
        return elem.xpath('string(font/a/@href)')
        
def get_session_details(s):
    url = 'http://www.azleg.gov/xml/sessions.asp'
    with s.urlopen(url) as page:
        root = etree.fromstring(page)
        session_file = open('session_details.py', 'w')
        detail = """
                 '%s':
                    {'type': '%s', 'session_id': %s,
                     'start_date': datetime.date(%s),
                     'end_date': datetime.date(%s)},
                 """
        for session in root.xpath('//session'):
            session_type = 'primary' if re.find('Regular', session.get('Session_Full_Name')) else 'special'
            start_date = datetime.datetime.strptime(
                                              session.get('Session_Start_Date'),
                                              '%Y-%m-%dT%H:%M:%S')
            end_date = datetime.datetime.strptime(session.get('Sine_Die_Day'),
                                                  '%Y-%m-%dT%H:%M:%S')
            session_file.write(detail % ( session.get('Session_Full_Name'),
                                           session_type,
                                           session.get('Session_ID'),
                                           start_date,
                                           end_date))
            
def get_committee_name(abbrv, chamber):
    return com_names[chamber][abbrv]
    
com_names = { 
    'lower': {
        'APPROP': 'Appropriations',
        'BI': 'Banking and Insurance',
        'COM': 'Commerce',
        'ED': 'Education',
        'ENV': 'Environment',
        'GOV': 'Government',
        'HHS': 'Health and Human Services',
        'JUD': 'Judiciary',
        'MAPS': 'Military Affairs and Public Safety',
        'NRRA': 'Natural Resources and Rural Affairs',
        'PERER': 'Public Employees, Retirement and Entitlement Reform',
        'RULES': 'Rules',
        'TI': 'Transportation and Infrastructure',
        'WE': 'Water and Energy',
        'WM': 'Ways and Means'
    },
    'upper' : {
        'APPROP': 'Appropriations',
        'CED': 'Commerce and Economic Development',
        'ED': 'Education Accountability and Reform',
        'FIN': 'Finance',
        'GOV': 'Government Institutions',
        'HEALTH': 'Healthcare and Medical Liability Reform',
        'JUD': 'Judiciary',
        'NRIPD': 'Natural Resources, Infrastructure and Public Debt',
        'PSHS': 'Public Safety and Human Services',
        'RRD': 'Retirement and Rural Development',
        'RULES': 'Rules',
        'VMA': 'Veterans and Military Affairs',
        'SUB APPROP ENR': 'Appropriations Subcommittee on Education and Natural Resources',
        'SUB APPROP H&W': 'Appropriations Subcommittee on Health and Welfare',
        'SUB APPROP TCJ': 'Appropriations Subcommittee on Transportation and Criminal Justice'
    }
}
common_abbrv = {
    'AM C&P ON RECON': 'amended c&p on reconsideration',
    'AM C&P ON REREF': 'amend c&p on rereferral',
    'AMEND C&P': 'amended constitutional and in proper form',
    'C&P': 'constitutional and in proper form',
    'C&P AS AM BY AP': 'constitutional and in proper form as amended by the committee on App',
    'C&P AS AM BY APPR': 'Constitutional and in proper form as amended by Appropriations',
    'C&P AS AM BY EN': 'constitutional and in proper form as amended by the Committee on ENV',
    'C&P AS AM BY GO': 'Constitutional and in proper form as amended by GovOp',
    'C&P AS AM BY HE': 'C&P AS AM BY HE',
    'C&P AS AM BY JU': 'constitutional and in proper form as amended by Jud',
    'C&P AS AM BY TR': 'C&P AS AM BY TR',
    'C&P AS AM BY WM': 'constitutional and in proper form as amended by the Committee on Way & Means',
    'C&P AS AM GOVOP': 'Constitutional and in proper form as amended by Government Operations',
    'C&P ON RECON': 'constitutional and in proper form on reconsideration',
    'C&P ON REREF': 'constitutional and in proper form on rereferral',
    'C&P W/FL': 'constitutional and in proper form with a floor amendment',
    'CAUCUS': 'Caucus',
    'CONCUR': 'rec to concur',
    'CONCUR FAILED': 'motion to concur failed',
    'DISC PETITION': 'discharge petition',
    'DISC/HELD': 'Discussed and Held',
    'DISC/ONLY': 'discussion only',
    'DISC/S/C': 'discussd and assigned to subcommittee',
    'DNP': 'do not pass',
    'DP': 'do pass',
    'DP ON RECON': 'do pass on reconsideration',
    'DP ON REREFER': 'do passed on rereferral',
    'DP W/MIN RPT': 'do pass with minority report',
    'DP/PFC': 'do pass and proper for consideration',
    'DP/PFC W/FL': 'do pass and proper for consideration with recommendation for a floor amendment',
    'DP/PFCA': 'do pass and proper for consideration amended',
    'DPA': 'do pass amended',
    'DPA CORRECTED': 'DPA CORRECTED',
    'DPA ON RECON': 'do pass amended on reconsideration',
    'DPA ON REREFER': 'do pass amended on rereferral',
    'DPA/PFC': 'do pass amended and proper for consideration',
    'DPA/PFC W/FL': 'do pass amended and proper for consideration with recommendation for a floor amendment',
    'DPA/PFCA': 'do pass amended and proper for consideration amended',
    'DPA/PFCA W/FL': 'do pass amended and proper for consideration with recommendation for a floor amendment',
    'DPA/SE': 'do pass amended/strike-everything',
    'DPA/SE CORRECTED': 'do pass amended/strike everything corrected',
    'DPA/SE ON RECON': 'do pass amended/ strike everything on reconsideration',
    'DPA/SE ON REREF': 'do pass amended/strike everything on rereferral',
    'FAILED': 'failed to pass',
    'FAILED BY S/V 0': 'failed by standing vote',
    'FAILED ON RECON': 'failed ON RECONSIDERATION',
    'FIRST': 'First Reading',
    'FURTHER AMENDED': 'further amended',
    'HELD': 'held',
    'HELD 1 WK': 'held one week',
    'HELD INDEF': 'held indefinitely',
    'HELD ON RECON': 'held on reconsideration',
    'None': 'No Action',
    'NOT CONCUR': 'rec not concur',
    'NOT HEARD': 'not heard',
    'NOT IN ORDER': 'not in order',
    'PASSED': 'Passed',
    'PFC': 'proper for consideration',
    'PFC W/FL': 'proper for consideration with recommendation for a floor amendment',
    'PFCA': 'proper for consideration amended',
    'PFCA W/FL': 'proper for consideration amended with recommendation for a floor amendment',
    'POSTPONE INDEFI': 'postponed indefinitely',
    'REC REREF TO COM': 'recommend rereferral to committee',
    'RECOMMIT TO COM': 'recommit to committee',
    'REMOVAL REQ': 'removal request from Rules Committee',
    'REREF GOVOP': 'Rereferred to GovOp',
    'REREF JUD': 'Rereferred to Judiciary',
    'REREF WM': 'Rereferred to Ways & Means',
    'RET FOR CON': 'returned for consideration',
    'RET ON CAL': 'Retained on the Calendar',
    'RETAINED': 'retained',
    'RULE 8J PROPER': 'proper legislation and deemed not derogatory or insulting',
    'S/C': 'subcommittee',
    'S/C REPORTED': 'Subcommittee reported',
    'W/D': 'withdrawn',
}
BILL_TYPES = (
    ('SB', 'Senate Bill'),
    ('SR', 'Senate Resolution'),
    ('SCR', 'Senate Concurrent Resolution'),
    ('HB', 'House Bill'),
    ('HR', 'House Resolution'),
    ('HCR', 'House Concurrent Resolution')
)
bill_types = {
    'sb': 'bill',
    'sr': 'resolution',
    'scr': 'concurrent resolution',
    'scm': 'concurrent memorial',
    'hb': 'bill',
    'hr': 'resolution',
    'hcr': 'concurrent resolution',
    'hcm': 'concurrent memorial',
}
word_key = (
    ('fifty', '50'),
    ('fiftieth', '50'),
    ('forty', '40'),
    ('first', '1'),
    ('second', '2'),
    ('third', '3'),
    ('fourth', '4'),
    ('fifth', '5'),
    ('sixth', '6'),
    ('seventh', '7'),
    ('eighth', '8'),
    ('ninth', '9'),
    ('tenth', '10'),
    ('eleventh', '11'),
    ('twelth', '12'),
    ('regular', 'r'),
    ('special', 's'),
)
