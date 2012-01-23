import datetime as dt
import lxml.html
import re

from urlparse import urlparse

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

HI_URL_BASE = "http://capitol.hawaii.gov"


def create_bill_report_url( chamber, year ):
    cname = { "upper" : "s", "lower" : "h" }[chamber]
    return HI_URL_BASE + "/report.aspx?type=intro" + cname + "b&year=" + year

def categorize_action(action):
    classifiers = (
        ('Pass(ed)? First Reading', 'bill:reading:1'),
        ('Introduced and Pass(ed)? First Reading',
             ['bill:introduced', 'bill:reading:1']),
        ('Introduced', 'bill:introduced'),
        #('The committee\(s\) recommends that the measure be deferred', ?
        ('Re(-re)?ferred to ', 'committee:referred'),
        ('Passed Second Reading .* referred to the committee',
         ['bill:reading:2', 'committee:referred']),
        ('.* that the measure be PASSED', 'committee:passed:favorable'),
        ('Received from (House|Senate)', 'bill:introduced'),
        ('Floor amendment .* offered', 'amendment:introduced'),
        ('Floor amendment adopted', 'amendment:passed'),
        ('Floor amendment failed', 'amendment:failed'),
        ('.*Passed Third Reading', 'bill:passed'),
        ('Enrolled to Governor', 'governor:received'),
        ('Act ', 'governor:signed'),
        # these are for resolutions
        ('Offered', 'bill:introduced'),
        ('Adopted', 'bill:passed'),
    )
    for pattern, types in classifiers:
        if re.match(pattern, action):
            return types
    # return other by default
    return 'other'

def split_specific_votes(voters):
    if voters.startswith('none'):
        return []
    elif voters.startswith('Senator(s)'):
        voters = voters.replace('Senator(s) ', '')
    elif voters.startswith('Representative(s)'):
        voters = voters.replace('Representative(s)', '')
    return voters.split(', ')

class HIBillScraper(BillScraper):
    
    state = 'hi'

    def parse_bill_metainf_table( self, metainf_table ):
        def _sponsor_interceptor(line):
            return [ guy.strip() for guy in line.split(",") ]

        interceptors = {
            "Introducer(s)" : _sponsor_interceptor    
        }

        ret = {}
        for tr in metainf_table:
            row = tr.xpath( "td" )
            key   = row[0].text_content().strip()
            value = row[1].text_content().strip()
            if key[-1:] == ":":
                key = key[:-1]
            if key in interceptors:
                value = interceptors[key](value)
            ret[key] = value
        return ret

    def parse_bill_actions_table( self, action_table ):
        ret = []
        for action in action_table.xpath('*')[1:]:
            date   = action[0].text_content()
            date   = dt.datetime.strptime(date, "%m/%d/%Y")
            actor  = action[1].text_content()
            string = action[2].text_content()
            actor = {
                "S" : "Senate",
                "H" : "House",
                "D" : "Data Systems",
                "$" : "Appropriation measure",
                "ConAm" : "Constitutional Amendment"
            }[actor]
            cat = categorize_action( string )
            vote = self.parse_vote( string )
            ret.append({
                "date"   : date,
                "actor"  : actor,
                "string" : string,
                "cat"    : cat,
                "vote"   : vote
            })
        return ret

    def parse_bill_versions_table( self, versions ):
        vs = []
        for version in versions.xpath("./*")[1:]:
            tds = version.xpath("./*")
            http_href = tds[0].xpath("./a")
            name      = tds[1].text_content().strip()
            pdf_href  = tds[2].xpath("./a")

            http_link = http_href[0].attrib['href']
            pdf_link  = pdf_href[0].attrib['href']

            vs.append( { "name" : name, "links" : {
                "application/pdf" : pdf_link,
                "text/html"       : http_link
            }})
        return vs

    def scrape_bill( self, url ):
        ret = {
            "url" : url
        }
        with self.urlopen(url) as bill_html: 
            bill_page = lxml.html.fromstring(bill_html)
            scraped_bill_name = bill_page.xpath(
                "//a[@id='LinkButtonMeasure']")[0].text_content()
            ret['bill_name'] = scraped_bill_name # for sanity checking
            versions = bill_page.xpath( "//table[@id='GridViewVersions']" )[0]

            tables = bill_page.xpath("//table")
            metainf_table = tables[0]
            action_table  = tables[1]

            metainf  = self.parse_bill_metainf_table( metainf_table )
            actions  = self.parse_bill_actions_table( action_table )
            versions = self.parse_bill_versions_table( versions )

            ret['metainf']  = metainf
            ret['versions'] = versions
            ret['actions']  = actions
        return ret

    def scrape_report_page(self, url):
        ret = []
        with self.urlopen(url) as list_html: 
            list_page = lxml.html.fromstring(list_html)
            bills = [ HI_URL_BASE + bill.attrib['href'] for bill in \
                list_page.xpath("//a[@class='report']") ]
            for bill in bills:
                b_data = self.scrape_bill( bill )
                ret.append( b_data )
        return ret

    def parse_vote(self, action):
        pattern = r"were as follows: (?P<n_yes>\d+) Aye\(?s\)?:\s+(?P<yes>.*?);\s+Aye\(?s\)? with reservations:\s+(?P<yes_resv>.*?);\s+(?P<n_no>\d*) No\(?es\)?:\s+(?P<no>.*?);\s+and (?P<n_excused>\d*) Excused: (?P<excused>.*)"
        if 'as follows' in action:
            result = re.search(pattern, action).groupdict()
            motion = action.split('.')[0] + '.'
            return result, motion
        return None

    def scrape(self, chamber, session):
        session_urlslug = \
            self.metadata['session_details'][session]['_scraped_name']
        bills = self.scrape_report_page( \
            create_bill_report_url( chamber, session_urlslug ) )
        for bill in bills:
            meta      = bill['metainf']
            versions  = bill['versions']
            actions   = bill['actions']
            companion = meta['Companion']
            name      = bill['bill_name']
            descr     = meta['Description']
            title     = meta['Report Title']
            ref       = meta['Current Referral']
            sponsors  = meta['Introducer(s)']
            m_title   = meta['Measure Title']

            b = Bill(session, chamber, name, title,
                companion=companion,
                description=descr,
                referral=ref,
                measure_title=m_title)
            b.add_source( bill['url'] )
            for version in versions:
                for link in version['links']:
                    b.add_version(version['name'], version['links'][link],
                        mimetype=link)

            for sponsor in sponsors:
                b.add_sponsor( type="primary", name=sponsor )

            for action in actions:

                b.add_action(action['actor'], action['string'], action['date'],
                    type=action['cat'])

                if action['vote'] != None:
                    v, motion = action['vote']
                    vote = Vote(chamber, action['date'], motion,
                        'PASSED' in action['string'],
                        int( v['n_yes'] or 0 ),
                        int( v['n_no'] or 0 ),
                        int( v['n_excused'] or 0))

                    def _add_votes( attrib, v, vote ):
                        for voter in split_specific_votes(v):
                            getattr(vote, attrib)(voter)

                    _add_votes( 'yes',   v['yes'],      vote )
                    _add_votes( 'yes',   v['yes_resv'], vote )
                    _add_votes( 'no',    v['no'],       vote )
                    _add_votes( 'other', v['excused'],  vote )

                    b.add_vote( vote )

            self.save_bill(b)
