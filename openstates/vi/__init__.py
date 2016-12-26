from .bills import VIBillScraper
#from .legislators import VTLegislatorScraper
from .committees import VICommitteeScraper
#from .events import VTEventScraper

metadata = dict(
    name='US Virgin Islands',
    abbreviation='vi',
    capitol_timezone='America/St_Thomas',
    legislature_name='Senate of the Virgin Islands',
    legislature_url='http://www.legvi.org/',
    chambers = { 'upper': { 'name': 'Senate', 'title': 'Senator' } },
    terms=[
           {'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['30']},
           {'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['31']},
           ],
    session_details={'30': {'type': 'primary',
                                   'display_name': '2013-2013 Regular Session',
                                   '_scraped_name': '30'
                                  },
                     '31': {'type': 'primary',
                                   'display_name': '2015-2016 Regular Session',
                                   '_scraped_name': '31'
                                  },
                     },
    feature_flags=[],
    _ignored_scraped_sessions= ['21', '22', '23', '24', '25', '26', '27', '28', '29']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath(
            'http://www.legvi.org/vilegsearch/',
            '//select[@name="ctl00$ContentPlaceHolder$leginum"]/option/text()')

def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
