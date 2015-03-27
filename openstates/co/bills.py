import datetime as dt
import re
import lxml.html
import scrapelib
from urlparse import urlparse

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

from .actions import Categorizer


CO_URL_BASE = "http://www.leg.state.co.us"
#                     ^^^ Yes, this is actually required


class COBillScraper(BillScraper):
    """
    This scraper is a bit bigger then some of the others, but it's just
    a standard billy scraper. Methods are documented just because this
    does both bill and vote scraping, and can be a bit overwhelming.
    """

    jurisdiction = 'co'
    categorizer = Categorizer()

    def get_bill_folder(self, session, chamber):
        """
        This returns a URL to the bill "folder" - a list of all the bills for that
        session and chamber. If the URL looks funny, it's because CO has made
        some interesting technical choices.
        """
        chamber_id = "(bf-3)" if chamber == "House" else "(bf-2)"
        url = CO_URL_BASE + "/CLICS/CLICS" + session \
            + "/csl.nsf/" + chamber_id + "?OpenView&Count=20000000"
        return url

    def read_td(self, td_node):
        return td_node[0].text
        #      ^^^^^^^^^^ font

    def parse_all_votes(self, bill_vote_url):
        """
        This will parse a vote page, with a list of who voted which way on what
        bill. This is invoked from `parse_votes', and invoking it directly may
        or may not be very useful.
        """
        ret = {"meta": {}, 'votes': {}}
        ret['meta']['url'] = bill_vote_url
        vote_html = self.get(bill_vote_url).text
        bill_vote_page = lxml.html.fromstring(vote_html)
        bill_vote_page.make_links_absolute(bill_vote_url)
        nodes = bill_vote_page.xpath('//table/tr')

        # The first tr is funky and we can ignore it.
        nodes = nodes[1:]

        inVoteSection = False

        for line in nodes:
            to_parse = line.text_content()
            if to_parse == "VOTE":
                inVoteSection = True
                continue
            if not inVoteSection:
                # there are some very header-esque fields if we
                # grab accross the row
                metainf = [a.strip() for a in to_parse.split(":", 1)]
                ret['meta'][metainf[0]] = metainf[1]
            else:
                # OK. We've either got a vote, or the final line.
                if not line[0].text_content().strip() == "":
                    # We've got an ending line
                    # They look like:
                    #    Final     YES: 7     NO: 6     EXC: 0     ABS: 0\
                    #        FINAL ACTION: PASS
                    #
                    to_parse = to_parse.replace("FINAL ACTION",
                        "FINAL_ACTION").replace(":", "")
                    if re.match("^FINAL.*", to_parse):
                        to_parse = to_parse[len("FINAL"):]

                    passage_actions = to_parse.split("  ")
                    final_score = {}
                    for item in passage_actions:
                        if item == "":
                            continue
                        item = item.strip()
                        keys = item.split(" ", 1)
                        final_score[keys[0]] = keys[1]

                    # XXX: Verify we can't do this with recursive splits
                    # it now looks like:
                    # ['Final', 'YES:', '7', 'NO:', '6', 'EXC:', '0',
                    #   'ABS:', '0', 'FINAL_ACTION:', 'PASS']
                    #passage_actions = passage_actions[1:]
                    #il = iter(passage_actions)
                    #final_score = dict(zip(il,il))

                    if not "FINAL_ACTION" in final_score:
                        final_score["FINAL_ACTION"] = False

                    ret['result'] = final_score
                else:
                    # We've got a vote.
                    person = line[1].text_content()  # <div><font>
                    vote = line[2].text_content()
                    if person.strip() != "":
                        ret['votes'][person] = vote
        return ret

    def parse_votes(self, bill_vote_url):
        """
        This will parse all the votes on a given bill - basically, it looks on the
        page of all votes, and invokes `parse_all_votes' for each href it finds

        We do some minor sanity checking, so the caller will be able to ensure the
        bill IDs match exactly before going ahead with saving the data to the DB
        """
        ret = {}

        vote_html = self.get(bill_vote_url).text
        bill_vote_page = lxml.html.fromstring(vote_html)
        bill_vote_page.make_links_absolute(bill_vote_url)
        nodes = bill_vote_page.xpath('//b/font')
        title = nodes[0].text
        ret['sanity-check'] = title[title.find("-") + 1:].strip()
        ret['votes'] = []
        # Just in case we need to add some sanity checking
        # votes = bill_vote_page.xpath('//table/tr/td/a')

        lines = bill_vote_page.xpath('//table/tr/td')

        date = "unknown"
        ctty = "unknown"

        # We can throw out the headers
        lines = lines[2:]

        for line in lines:
            try:
                ctty = line[0][0][0].text_content()
                date = line[0][0][1].text_content()
            except IndexError:
                # We have a vote line for the previous line
                try:
                    vote_url = line.xpath('a')[0].attrib['href']
                    vote_page = vote_url
                    vote_dict = self.parse_all_votes(vote_page)

                    vote_dict['meta']['x-parent-date'] = date
                    vote_dict['meta']['x-parent-ctty'] = ctty

                    ret['votes'].append(vote_dict)
                except KeyError:
                    pass
                except IndexError:
                    pass

        return ret

    def get_vote_url(self, billid, session):
        """
        URL generator for getting the base vote pages. The links use all sorts of
        JS bouncing, so this will just fetch the end page.
        """
        return CO_URL_BASE + \
            "/CLICS%5CCLICS" + session + \
            "%5Ccommsumm.nsf/IndSumm?OpenView&StartKey=" + billid + "&Count=4"

    def parse_versions(self, bill_versions_url):
        """
        Parse a bill versions page for all the versions
        """
        try:
            versions_html = self.get(bill_versions_url).text
            bill_versions_page = lxml.html.fromstring(versions_html)
            bill_versions_page.make_links_absolute(bill_versions_url)
        except scrapelib.HTTPError:  # XXX: Hack for deleted pages - 404s
            return []

        url = re.findall("var url=\"(?P<url>.+)\"", versions_html)[0]

        trs = bill_versions_page.xpath('//form//table//tr')[3:]
        cols = {
            "type": 0,
            "pdf": 1,
            "wpd": 2
        }

        pdfs = bill_versions_page.xpath("//a/font[contains(text(), 'pdf')]")
        cur_version = bill_versions_page.xpath("//a//font[contains(text(), 'Current PDF')]")
        return [{
            "name": x.text,
            "mimetype": "application/pdf",
            "link": CO_URL_BASE + url + (
                re.findall(
                    "_doClick\('(?P<slug>.+)'",
                    x.getparent().attrib['onclick']
                )[0]
            )
        } for x in cur_version + pdfs]

    def parse_history(self, bill_history_url):
        """
        Parse a bill history page for as much data as we can gleen, such as when
        the bill was introduced (as well as a number of other things)
        """
        # their URL is actually a shim. let's get the target GET param
        url = urlparse(bill_history_url)
        get_info = url[4].split("&")
        # This is a bit of a mess. XXX: Better way to get args using
        # url[lib|parse] ?

        clean_args = {}
        ret = []

        for arg in get_info:
            try:
                key, value = (
                    arg[:arg.index("=")],
                    arg[arg.index("=") + 1:]
                )
                clean_args[key] = value
            except ValueError:
                pass

        # </mess>

        try:
            bill_history_url = CO_URL_BASE + clean_args['target']
            # We're wrapping it because guessing at the URL
            # param is not really great.

        except KeyError:
            return ret

        try:
            history_html = self.get(bill_history_url).text
            bill_history_page = lxml.html.fromstring(history_html)
            bill_history_page.make_links_absolute(bill_history_url)
        except scrapelib.HTTPError:  # XXX: Hack for deleted pages - 404s
            return []

        nodes = bill_history_page.xpath('//form/b/font')

        if len(nodes) == 0:
            return

        actions = nodes[3].text_content()

        for action in actions.split('\n'):
            if action.strip() == "":
                continue

            date_string = action[:action.find(" ")]
            if ":" in date_string:
                date_string = action[:action.find(":")]
            if "No" == date_string:  # XXX Remove me
            # as soon as sanity is on:
            # http://www.leg.state.co.us/clics/clics2012a/csl.nsf/billsummary/C150552896590FA587257961006E7C0B?opendocument
                continue

            date_time = dt.datetime.strptime(date_string, "%m/%d/%Y")
            action = action[action.find(" ") + 1:]
            ret.append((action, date_time))

        return ret

    def scrape_bill_sheet(self, session, chamber):
        """
        Scrape the bill sheet (the page full of bills and other small bits of data)
        """
        sheet_url = self.get_bill_folder(session, chamber)

        bill_chamber = {"Senate": "upper", "House": "lower"}[chamber]

        index = {
            "id": 0,
            "title_sponsor": 1,
            "version": 2,
            "history": 3,
            "votes": 7
        }

        sheet_html = self.get(sheet_url).text
        sheet_page = lxml.html.fromstring(sheet_html)
        sheet_page.make_links_absolute(sheet_url)

        bills = sheet_page.xpath('//table/tr')

        for bill in bills:
            bill_id = self.read_td(bill[index["id"]][0])

            if bill_id == None:
                # Every other entry is null for some reason
                continue

            dot_loc = bill_id.find('.')
            if dot_loc != -1:
                # budget bills are missing the .pdf, don't truncate
                bill_id = bill_id[:dot_loc]
            title_and_sponsor = bill[index["title_sponsor"]][0]

            bill_title = title_and_sponsor.text
            bill_title_and_sponsor = title_and_sponsor.text_content()
            if bill_title is None:
                continue  # Odd ...

            sponsors = bill_title_and_sponsor.replace(bill_title, "").\
                replace(" & ...", "").split("--")

            cats = {
                "SB": "bill",
                "HB": "bill",
                "HR": "resolution",
                "SR": "resolution",
                "SCR": "concurrent resolution",
                "HCR": "concurrent resolution",
                "SJR": "joint resolution",
                "HJR": "joint resolution",
                "SM": "memorial",
                "HM": "memorial"
            }

            bill_type = None

            for cat in cats:
                if bill_id[:len(cat)] == cat:
                    bill_type = cats[cat]

            b = Bill(session, bill_chamber, bill_id, bill_title,
                     type=bill_type)

            b.add_source(sheet_url)

            versions_url = \
                bill[index["version"]].xpath('font/a')[0].attrib["href"]
            versions_url = versions_url
            versions = self.parse_versions(versions_url)

            for version in versions:
                b.add_version(version['name'], version['link'],
                    mimetype=version['mimetype'])

            bill_history_href = bill[index["history"]][0][0].attrib['href']

            history = self.parse_history(bill_history_href)
            if history is None:
                self.logger.warning("Bill history for %s is not correctly formatted" % bill_id)
                continue
            b.add_source(bill_history_href)

            chamber_map = dict(Senate='upper', House='lower')
            for action, date in history:
                action_actor = chamber_map.get(chamber, chamber)
                attrs = dict(actor=action_actor, action=action, date=date)
                attrs.update(self.categorizer.categorize(action))
                b.add_action(**attrs)

            for sponsor in sponsors:
                if sponsor != None and sponsor != "(NONE)" and \
                   sponsor != "":
                    if "&" in sponsor:
                        for sponsor in [x.strip() for x in sponsor.split("&")]:
                            b.add_sponsor("primary", sponsor)
                    else:
                        b.add_sponsor("primary", sponsor)

            # Now that we have history, let's see if we can't grab some
            # votes

            bill_vote_href, = bill.xpath(".//a[contains(text(), 'Votes')]")
            bill_vote_href = bill_vote_href.attrib['href']
            #bill_vote_href = self.get_vote_url(bill_id, session)
            votes = self.parse_votes(bill_vote_href)

            if (votes['sanity-check'] == 'This site only supports frames '
                    'compatible browsers!'):
                votes['votes'] = []
            elif votes['sanity-check'] != bill_id:
                self.warning("XXX: READ ME! Sanity check failed!")
                self.warning(" -> Scraped ID: " + votes['sanity-check'])
                self.warning(" -> 'Real' ID:  " + bill_id)
                assert votes['sanity-check'] == bill_id

            for vote in votes['votes']:
                filed_votes = vote['votes']
                passage = vote['meta']
                result = vote['result']

                composite_time = "%s %s" % (
                    passage['x-parent-date'],
                    passage['TIME']
                )
                # It's now like: 04/01/2011 02:10:14 PM
                pydate = dt.datetime.strptime(composite_time,
                    "%m/%d/%Y %I:%M:%S %p")
                hasHouse = "House" in passage['x-parent-ctty']
                hasSenate = "Senate" in passage['x-parent-ctty']

                if hasHouse and hasSenate:
                    actor = "joint"
                elif hasHouse:
                    actor = "lower"
                else:
                    actor = "upper"

                other = (int(result['EXC']) + int(result['ABS']))
                # OK, sometimes the Other count is wrong.
                local_other = 0
                for voter in filed_votes:
                    l_vote = filed_votes[voter].lower().strip()
                    if l_vote != "yes" and l_vote != "no":
                        local_other = local_other + 1

                if local_other != other:
                    self.warning( \
                        "XXX: !!!WARNING!!! - resetting the 'OTHER' VOTES")
                    self.warning(" -> Old: %s // New: %s" % (
                        other, local_other
                    ))
                    other = local_other

                passed = (result['FINAL_ACTION'] == "PASS")
                if passage['MOTION'].strip() == "":
                    continue

                if "without objection" in passage['MOTION'].lower():
                    passed = True

                v = Vote(actor, pydate, passage['MOTION'],
                         passed,
                         int(result['YES']), int(result['NO']),
                         other,
                         moved=passage['MOVED'],
                         seconded=passage['SECONDED'])

                v.add_source(vote['meta']['url'])
                # v.add_source( bill_vote_href )

                # XXX: Add more stuff to kwargs, we have a ton of data
                seen = set([])
                for voter in filed_votes:
                    who = voter
                    if who in seen:
                        raise Exception("Seeing the double-thing. - bug #702")
                    seen.add(who)

                    vote = filed_votes[who]
                    if vote.lower() == "yes":
                        v.yes(who)
                    elif vote.lower() == "no":
                        v.no(who)
                    else:
                        v.other(who)
                b.add_vote(v)
            self.save_bill(b)

    def scrape(self, chamber, session):
        """
        Entry point when invoking this from billy (or really whatever else)
        """
        chamber = {'lower': 'House', 'upper': 'Senate'}[chamber]
        self.scrape_bill_sheet(session, chamber)
