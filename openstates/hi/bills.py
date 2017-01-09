import datetime as dt
import lxml.html
import re

from .utils import get_short_codes
from urlparse import urlparse

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

HI_URL_BASE = "http://capitol.hawaii.gov"
SHORT_CODES = "%s/committees/committees.aspx?chamber=all" % (HI_URL_BASE)

def create_bill_report_url( chamber, year, bill_type ):
    cname = { "upper" : "s", "lower" : "h" }[chamber]
    bill_slug = {
        "bill" : "intro%sb" % ( cname ),
        "cr"   : "%sCR" % ( cname.upper() ),
        "r"    : "%sR"  % ( cname.upper() )
    }

    return HI_URL_BASE + "/report.aspx?type=" + bill_slug[bill_type] + \
        "&year=" + year

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
        # Note, occasionally the gov sends intent to veto then doesn't. So use Vetoed not Veto
        ('Vetoed .* line-item', 'governor:vetoed:line-item'),
        ('Vetoed', 'governor:vetoed'),
        ('Veto overridden', 'bill:veto_override:passed'),
        # these are for resolutions
        ('Offered', 'bill:introduced'),
        ('Adopted', 'bill:passed'),
    )
    ctty = None
    for pattern, types in classifiers:
        if re.match(pattern, action):
            if "committee:referred" in types:
                ctty = re.findall(r'\w+', re.sub(pattern, "", action))
            return (types, ctty)
    # return other by default
    return ('other', ctty)

def split_specific_votes(voters):
    if voters is None or voters.startswith('none'):
        return []
    elif voters.startswith('Senator(s)'):
        voters = voters.replace('Senator(s) ', '')
    elif voters.startswith('Representative(s)'):
        voters = voters.replace('Representative(s)', '')
    return voters.split(', ')

class HIBillScraper(BillScraper):

    jurisdiction = 'hi'

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

    def parse_bill_actions_table(self, bill, action_table):
        for action in action_table.xpath('*')[1:]:
            date   = action[0].text_content()
            date   = dt.datetime.strptime(date, "%m/%d/%Y")
            actor  = action[1].text_content()
            string = action[2].text_content()
            actor = {
                "S" : "upper",
                "H" : "lower",
                "D" : "Data Systems",
                "$" : "Appropriation measure",
                "ConAm" : "Constitutional Amendment"
            }[actor]
            act_type, committees = categorize_action(string)
            # XXX: Translate short-code to full committee name for the
            #      matcher.

            real_committees = []

            if committees:
                for committee in committees:
                    try:
                        committee = self.short_ids[committee]['name']
                        real_committees.append(committee)
                    except KeyError:
                        pass

            bill.add_action(actor, string, date,
                            type=act_type, committees=real_committees)

            vote = self.parse_vote(string)
            if vote:
                v, motion = vote
                vote = Vote(actor, date, motion, 'passed' in string.lower(),
                    int( v['n_yes'] or 0 ),
                    int( v['n_no'] or 0 ),
                    int( v['n_excused'] or 0))

                def _add_votes( attrib, v, vote ):
                    for voter in split_specific_votes(v):
                        getattr(vote, attrib)(voter)

                _add_votes('yes',   v['yes'],      vote)
                _add_votes('yes',   v['yes_resv'], vote)
                _add_votes('no',    v['no'],       vote)
                _add_votes('other', v['excused'],  vote)

                bill.add_vote(vote)

    def parse_bill_versions_table(self, bill, versions):
        versions = versions.xpath("./*")
        if len(versions) > 1:
            versions = versions[1:]

        if versions == []:
            raise Exception("Missing bill versions.")

        for version in versions:
            tds = version.xpath("./*")
            if 'No other versions' in tds[0].text_content():
                return

            http_href = tds[0].xpath("./a")
            name = http_href[0].text_content().strip()
            # category  = tds[1].text_content().strip()
            pdf_href  = tds[1].xpath("./a")

            http_link = http_href[0].attrib['href']
            pdf_link  = pdf_href[0].attrib['href']

            bill.add_version(name, http_link, mimetype="text/html")
            bill.add_version(name, pdf_link, mimetype="application/pdf")

    def scrape_bill(self, session, chamber, bill_type, url):
        bill_html = self.get(url).text
        bill_page = lxml.html.fromstring(bill_html)
        scraped_bill_id = bill_page.xpath(
            "//a[contains(@id, 'LinkButtonMeasure')]")[0].text_content()
        bill_id = scraped_bill_id.split(' ')[0]
        versions = bill_page.xpath( "//table[contains(@id, 'GridViewVersions')]" )[0]

        tables = bill_page.xpath("//table")
        metainf_table = bill_page.xpath('//div[contains(@id, "itemPlaceholder")]//table[1]')[0]
        action_table  = bill_page.xpath('//div[contains(@id, "UpdatePanel1")]//table[1]')[0]

        meta  = self.parse_bill_metainf_table(metainf_table)

        subs = [ s.strip() for s in meta['Report Title'].split(";") ]
        if "" in subs:
            subs.remove("")

        b = Bill(session, chamber, bill_id, title=meta['Measure Title'],
                 summary=meta['Description'],
                 referral=meta['Current Referral'],
                 subjects=subs,
                 type=bill_type)
        b.add_source(url)

        companion = meta['Companion'].strip()
        if companion:
            b['companion'] = companion

        for sponsor in meta['Introducer(s)']:
            b.add_sponsor(type='primary', name=sponsor)

        actions  = self.parse_bill_actions_table(b, action_table)
        versions = self.parse_bill_versions_table(b, versions)

        self.save_bill(b)

    def parse_vote(self, action):
        vote_re = (r'''
                (?P<n_yes>\d+)\sAye\(?s\)?  # Yes vote count
                (:\s+(?P<yes>.*?))?;\s+  # Yes members
                Aye\(?s\)?\swith\sreservations:\s+(?P<yes_resv>.*?);?  # Yes with reservations members
                (?P<n_no>\d*)\sNo\(?es\)?:\s+(?P<no>.*?);?
                (\s+and\s+)?
                (?P<n_excused>\d*)\sExcused:\s(?P<excused>.*)\.?
                ''')
        result = re.search(vote_re, action, re.VERBOSE)
        if result is None:
            return None
        result = result.groupdict()
        motion = action.split('.')[0] + '.'
        return result, motion

    def scrape_type(self, chamber, session, billtype):
        session_urlslug = \
            self.metadata['session_details'][session]['_scraped_name']
        report_page_url = create_bill_report_url(chamber, session_urlslug,
                                                 billtype)
        billy_billtype = {
            "bill" : "bill",
            "cr"   : "concurrent resolution",
            "r"    : "resolution"
        }[billtype]

        list_html = self.get(report_page_url).text
        list_page = lxml.html.fromstring(list_html)
        for bill_url in list_page.xpath("//a[@class='report']"):
            bill_url = HI_URL_BASE + bill_url.attrib['href']
            self.scrape_bill(session, chamber, billy_billtype, bill_url)


    def scrape(self, session, chamber):
        get_short_codes(self)
        bill_types = ["bill", "cr", "r"]
        for typ in bill_types:
            self.scrape_type(session, chamber, typ)
