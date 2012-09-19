from billy.utils.fulltext import oyster_text, worddata_to_text

metadata = dict(
    name='Kentucky',
    abbreviation='ky',
    capitol_timezone='America/New_York',
    legislature_name='Kentucky General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
    dict(name='2011-2012',
        start_year=2011,
        end_year=2011,
        sessions=[
            '2011 Regular Session', '2011SS', '2012RS', '2012SS'
            ])
    ],
    session_details={
        '2011 Regular Session': {'type': 'primary',
                                 'display_name': '2011 Regular Session',
                                 '_scraped_name': '2011 Regular Session',
                                },
        '2011SS': {'type': 'special',
                   'display_name': '2011 Extraordinary Session',
                   '_scraped_name': '2011 Extraordinary Session'},
        '2012RS': {'type': 'primary',
                   'display_name': '2012 Regular Session',
                   '_scraped_name': '2012 Regular Session',
                  },
        '2012SS': {'type': 'special',
                   'display_name': '2012 Extraordinary Session',
                   '_scraped_name': '2012 Extraordinary Session'},
    },
    feature_flags=['subjects', 'events', 'influenceexplorer'],
    _ignored_scraped_sessions=[],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.lrc.ky.gov/legislation.htm',
                     '//a[contains(@href, "record.htm")]/img/@alt')

@oyster_text
def extract_text(oyster_doc, data):
    return worddata_to_text(data)

document_class = dict(
    AWS_PREFIX = 'documents/ky/',
    update_mins = 7*24*60,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
