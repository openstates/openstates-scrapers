from lxml import etree
import re, datetime
doc_for_bills_url = 'http://www.azleg.gov/DocumentsForBill.asp?Bill_Number=%s&Session_ID=%s'
base_url = 'http://www.azleg.gov/'
select_session_url = 'http://www.azleg/SelectSession.asp.html'

def parse_link_id(link):
    """
    extracts the div[@id] from the links on the DocumentsForBill pages
    """
    return link.get('href')[link.get('href').find("'") + 1 : link.get('href').rfind("'")]

def get_bill_type(bill_id):
    """
    bill_id = 'SJR2204'
    get_bill_type(bill_id) --> 'joint resolution'
    """
    prefix = re.match('([a-z]*)', bill_id.lower()).group()
    if prefix in bill_types:
        return bill_types[prefix]
    else:
        return 'bill'
            
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
        return_date = ''
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
        
def get_session_details(s):
    """
    gets the session list and writes them to session_details.py
    still needs some hand editing to insure that a primary session is default
    """
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
            session_type = 'primary' if re.search('Regular', session.get('Session_Full_Name')) else 'special'
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
            
def get_rows(rows, header):
    """
    takes the rows and header and returns a dict for each row with { key : <td> }
    """
    header = [x.text_content().strip() for x in header]
    keyed_rows = []
    for r in rows:
        dict_row = {}
        for k,v in zip(header, r.xpath('td')):
            dict_row.update({k:v})
        keyed_rows.append(dict_row)
    return keyed_rows
    
def get_actor(tr, chamber):
    """
    gets the actor of a given action based on presence of a 'TRANSMIT TO' action
    """
    actor = tr[0].text_content().strip()
    if actor.startswith('H') or actor.startswith('S'):
        actor = actor[0]
        return {'H': 'lower', 'S': 'upper'}[actor]
    else:
        h_or_s = tr.xpath('ancestor::table[1]/preceding-sibling::' + 
                                  'table/tr/td/b[contains(text(), "TRANSMIT TO")]')
        if h_or_s:
            # actor is the last B element
            h_or_s = h_or_s[-1].text_content().strip()
            actor = 'upper' if h_or_s.endswith('SENATE:') else 'lower'
        else:
            actor = chamber
        return actor
    
def get_committee_name(abbrv, chamber):
    try:
        return com_names[chamber][abbrv]
    except KeyError:
        return abbrv
    
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

bill_types = {
    'sb': 'bill',
    'sm': 'memorial',
    'sr': 'resolution',
    'scr': 'concurrent resolution',
    'scm': 'concurrent memorial',
    'scj': 'joint resolution',
    'hb': 'bill',
    'hm': 'memorial',
    'hr': 'resolution',
    'hcr': 'concurrent resolution',
    'hcm': 'concurrent memorial',
    'hjr': 'joint resolution',
    'mis': 'miscellaneous' 
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
