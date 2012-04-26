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

def legislature_to_number(leg):
    """
    Takes a full session and splits it down to the values for
    FormatDocument.asp.

    session = '49th-1st-regular'
    legislature_to_number(session) --> '49Leg/1s'
    """
    l = leg.lower().split('-')
    return '%sLeg/%s%s' % (l[0][0:2], l[1][0], l[2][0])

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
    'lower': {'APPROP': 'Appropriations',
              'AW': 'Agriculture and Water',
              'BI': 'Banking and Insurance',
              'COM': 'Commerce',
              'ED': 'Education',
              'ENR': 'Energy and Natural Resources',
              'ENV': 'Environment',
              'ERA': 'Employment and Regulatory Affairs',
              'GOV': 'Government',
              'HEIR': 'Higher Education, Innovation and Reform',
              'HHS': 'Health and Human Services',
              'JUD': 'Judiciary',
              'MAPS': 'Military Affairs and Public Safety',
              'RULES': 'Rules',
              'TI': 'Technology and Infrastructure',
              'TRANS': 'Transportation',
              'WM': 'Ways and Means'},
    'upper': {'APPROP': 'Appropriations',
              'BI': 'Banking and Insurance',
              'BSFSS': 'Border Security, Federalism and States Sovereignty',
              'CE': 'Commerce and Energy',
              'ED': 'Education',
              'EDJC': 'Economic Development and Jobs Creation',
              'FIN': 'Finance',
              'GR': 'Government Reform',
              'HMLR': 'Healthcare and Medical Liability Reform',
              'JUD': 'Judiciary',
              'NRT': 'Natural Resources and Transportation',
              'PSHS': 'Public Safety and Human Services',
              'RULES': 'Rules',
              'SUB APPROP HW': 'Appropriations',
              'SUB APPROP RIEN': 'Appropriations',
              'SUB APPROP TCJ': 'Appropriations',
              'VMA': 'Veterans and Military Affairs',
              'WLRD': 'Water, Land Use and Rural Development'}}

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
