from billy.scrape import Scraper
import datetime
import re
from lxml import etree, html

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

# borrowed from django.contrib.humanize.templatetags
def ordinal(value):
    """
    Converts an integer to its ordinal as a string. 1 is '1st', 2 is '2nd',
    3 is '3rd', etc. Works for any integer.
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    t = ('th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th')
    if value % 100 in (11, 12, 13): # special case
        return u"%d%s" % (value, t[0])
    return u'%d%s' % (value, t[value % 10])

def get_session_name(leg):
    l = leg.lower().replace('-', ' ').split()
    session = [x[1] for y in l for x in word_key if x[0] == y]
    try:
        if len(session) == 4:
            one = ordinal(int(session[0]) + int(session[1]))
            two = ordinal(session[2])
        else:
            one = ordinal(int(session[0]))
            two = ordinal(int(session[1]))
        three = {'s': 'special', 'r': 'regular'}[session[-1]]
        return "%s-%s-%s" % (one, two, three)
    except IndexError:
        return None

def get_date(d):
    if d:
        d = datetime.datetime.strptime(d, '%Y-%m-%dT%H:%M:%S').date()
        return '%d, %d, %d' % (d.year, d.month, d.day)
    else:
        return ''

class AZTermScraper(Scraper):
    state = 'az'

    def scrape_session_details(self):
        """
        writes the terms and session details to session_detail.py
        still needs some hand work to make sure that regular sessions are
        where they should be.
        """
        url = 'http://www.azleg.gov/xml/sessions.asp'
        page = self.get(url).text
        root = etree.fromstring(page)
        session_file = open('session_details.py', 'w')
        terms = """
        {'name': '%s',
         'sessions': [
            %s
         ],
         'start_year': %s, 'end_year': %s
        },
        """
        term_list = {}
        detail = """
                 '%s':
                    {'type': '%s', 'session_id': %s,
                     'verbose_name': '%s',
                     'start_date': datetime.date(%s),
                     'end_date': datetime.date(%s)},\n"""
        sessions = root.xpath('//session')
        sessions = sorted(sessions, key=lambda x: x.get('Sine_Die_Date') or
                                        "%s" % datetime.datetime.today())
        terms_text = ""
        details_text = ""
        for session in sessions:
            session_type = 'primary' if re.search('Regular', session.get('Session_Full_Name')) else 'special'
            start_date = get_date(session.get('Session_Start_Date', None))
            end_date = get_date(session.get('Sine_Die_Date', None))
            session_name = get_session_name(session.get('Session_Full_Name'))
            details_text += detail % (session_name,
                                      session_type,
                                      session.get('Session_ID'),
                                      session.get('Session_Full_Name'),
                                      start_date,
                                      end_date,)
            try:
                s_name = session_name[0:2]
            except TypeError:
                s_name = 'misc'
            if s_name in term_list:
                term_list[s_name]['sessions'] += "                '%s',\n" % session_name
                if end_date[0:4] > term_list[s_name]['end_date']:
                    term_list[s_name]['end_date'] = end_date[0:4]
                if start_date[0:4] < term_list[s_name]['start_date']:
                    term_list[s_name]['start_date'] = start_date[0:4]
            else:
                term_list[s_name] = {}
                term_list[s_name]['sessions'] = "'%s',\n" % session_name
                term_list[s_name]['end_date'] = end_date[0:4]
                term_list[s_name]['start_date'] = start_date[0:4]

        for key in sorted(term_list.keys()):
            session_file.write(terms % (
                    key, term_list[key]['sessions'],
                    term_list[key]['start_date'],
                    term_list[key]['end_date']
                ))
        session_file.write(details_text)
        session_file.close()

if __name__ == '__main__':
    from . import metadata
    scraper = AZTermScraper(metadata)
    scraper.scrape_session_details()
