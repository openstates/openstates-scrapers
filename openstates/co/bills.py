import datetime as dt
import re
from collections import defaultdict
import lxml.html

from urlparse import urlparse

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote


CO_URL_BASE = "http://www.leg.state.co.us"
#                     ^^^ Yes, this is actually required

class COBillScraper(BillScraper):
    """
    This scraper is a bit bigger then some of the others, but it's just
    a standard billy scraper. Methods are documented just because this
    does both bill and vote scraping, and can be a bit overwhelming.
    """

    state = 'co'

    def get_bill_folder( self, session, chamber ):
        """
        This returns a URL to the bill "folder" - a list of all the bills for that
        session and chamber. If the URL looks funny, it's because CO has made
        some interesting technical choices.
        """
        chamber_id = "(bf-3)" if chamber == "House" else "(bf-2)"
        url = CO_URL_BASE + "/CLICS/CLICS" +  session \
            + "/csl.nsf/" + chamber_id + "?OpenView&Count=20000000"
        return url


    def read_td( self, td_node ):
        return td_node[0].text
        #      ^^^^^^^^^^ font


    def parse_all_votes( self, bill_vote_url ):
        """
        This will parse a vote page, with a list of who voted which way on what
        bill. This is invoked from `parse_votes', and invoking it directly may
        or may not be very useful.
        """
        ret = { "meta" : {}, 'votes' : {} }
        ret['meta']['url'] = bill_vote_url
        with self.urlopen(bill_vote_url) as vote_html:
            bill_vote_page = lxml.html.fromstring(vote_html)
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
                    self.log(to_parse)
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
                        self.log(final_score)

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
                        # self.log("FOO: " + str([x.text_content() for x in line]))
                        person = line[1].text_content() # <div><font>
                        vote   = line[2].text_content()
                        if person.strip() != "":
                            ret['votes'][person] = vote
        return ret


    def parse_votes( self, bill_vote_url ):
        """
        This will parse all the votes on a given bill - basically, it looks on the
        page of all votes, and invokes `parse_all_votes' for each href it finds

        We do some minor sanity checking, so the caller will be able to ensure the
        bill IDs match exactly before going ahead with saving the data to the DB
        """
        ret = {}

        with self.urlopen(bill_vote_url) as vote_html:
            bill_vote_page = lxml.html.fromstring(vote_html)
            nodes = bill_vote_page.xpath('//b/font')
            title = nodes[0].text
            ret['sanity-check'] = title[title.find("-")+1:].strip()
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
                except IndexError as e:
                    # We have a vote line for the previous line
                    try:
                        vote_url = line.xpath('a')[0].attrib['href']
                        vote_page = CO_URL_BASE + vote_url
                        vote_dict = self.parse_all_votes( vote_page )

                        vote_dict['meta']['x-parent-date'] = date
                        vote_dict['meta']['x-parent-ctty'] = ctty

                        ret['votes'].append( vote_dict )
                    except KeyError as e:
                        pass
                    except IndexError as e:
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

    def parse_versions( self, bill_versions_url ):
        """
        Parse a bill versions page for all the versions
        """
        with self.urlopen(bill_versions_url) as versions_html:
            bill_versions_page = lxml.html.fromstring(versions_html)
            trs = bill_versions_page.xpath('//form/table/tr')[3:]
            cols = {
                "type" : 0,
                "pdf"  : 1,
                "wpd"  : 2
            }
            versions = []
            for tr in trs:
                if len(tr) == 3: # jeezum crackers.
                    name = tr[cols["type"]].text_content()
                    if name[-1:] == ":":
                        name = name[:-1]
                    wpd_link = tr[cols["wpd"]][0]
                    pdf_link = tr[cols["pdf"]][0]

                    wpd_text = wpd_link.text_content().strip()
                    pdf_text = wpd_link.text_content().strip()

                    wpd_link = wpd_link.attrib["href"]
                    pdf_link = pdf_link.attrib["href"]

                    format = None

                    if pdf_link.strip() != "" and pdf_text != "":
                        link = CO_URL_BASE + pdf_link
                        format = "application/pdf"

                    elif wpd_link.strip() != "" and wpd_text != "":
                        link = CO_URL_BASE + wpd_link
                        format = "application/vnd.wordperfect"

                    if format != None:
                        versions.append({
                            "name"     : name,
                            "mimetype" : format,
                            "link"     : link
                        })

            return versions


    def parse_history( self, bill_history_url ):
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
        ret        = []

        for arg in get_info:
            try:
                key, value = (
                    arg[:arg.index("=")],
                    arg[arg.index("=")+1:]
                )
                clean_args[key] = value
            except ValueError as e:
                pass

        # </mess>

        try:
            bill_history_url = CO_URL_BASE + \
                clean_args['target']
            # We're wrapping it because guessing at the URL
            # param is not really great.

        except KeyError:
            return ret

        with self.urlopen(bill_history_url) as history_html:
            bill_history_page = lxml.html.fromstring(history_html)
            nodes = bill_history_page.xpath('//form/b/font')

            bill_id = nodes[1].text
            actions = nodes[3].text_content()

            for action in actions.split('\n'):

                date_string = action[:action.find(" ")]
                if ":" in date_string:
                    date_string = action[:action.find(":")]

                date_time   = dt.datetime.strptime( date_string, "%m/%d/%Y" )
                action = action[action.find(" ") + 1:]

                action_ids = [a.strip() for a in action.split('-')]

                item_info = {
                    "action"      : action_ids[0],
                    "date"        : date_time,
                    "args"        : action_ids[1:],
                    "orig"        : action
                }

                ret.append( item_info )

            return ret

    def add_action_to_bill( self, bill, action ):
        """
        We were able to get a bunch of actions, so this method handles
        mangling the human-readable descriptions in well tagged actions
        that we put into the DB.
        """
        # We have a few inner methods that handle each "type" of description.
        # This is mostly to keep things as clear as we can, and avoid huge and
        # unmaintainable chunks of code

        def _parse_house_action():
            """
            Parse a string that contains "House". On failure to handle the string,
            we will return false, and let the fallback handler resolve the string.
            """
            actor = "lower"
            aText = action['action']

            if aText == 'Introduced In House':
                # Typically, we're also including an assigned ctty
                bill_assignd_ctty = action['args'][0]
                assgnd_to = "Assigned to"
                if bill_assignd_ctty[:len(assgnd_to)] == assgnd_to:
                    bill_assignd_ctty = bill_assignd_ctty[len(assgnd_to)+1:]
                bill.add_action( actor, action['orig'], action['date'],
                    type=[ "bill:introduced", "committee:referred" ],
                    assigned_ctty=bill_assignd_ctty,
                    brief_action_name='Introduced'
                    )
                return True

            testStr = "House Second Reading Special Order"
            if aText[:len(testStr)] == testStr:
                # get the status of the reading next
                bill_passfail = action['args'][0]
                normalized_brief = "House Second Reading %s" % ( bill_passfail )
                bill.add_action( actor, action['orig'],
                    action['date'], brief_action_name=normalized_brief)
                return True

            # XXX: mangle this in with the bit above me
            testStr = "House Third Reading Special Order"
            if aText[:len(testStr)] == testStr:
                # get the status of the reading next
                bill_passfail = action['args'][0]
                normalized_brief = "House Third Reading %s" % ( bill_passfail )
                bill.add_action( actor, action['orig'],
                    action['date'], brief_action_name=normalized_brief)
                return True

            simple_intro_match = {
                "House Second Reading Passed"        : [ "bill:reading:2" ],
                "House Third Reading Passed"         : [ "bill:reading:3" ],
                "Signed by the Speaker of the House" : [ "other" ],
                "House Vote to Override Passed"      : \
                    [ "bill:veto_override:passed" ],
                "House Vote to Override Failed"      : \
                    [ "bill:veto_override:failed" ],
            }

            simple_contain = {
                "Refer Amended"   : [ "committee:passed" ],
                "Refer Unamended" : [ "committee:passed" ]
            }

            for testStr in simple_contain:
                if testStr in aText:
                    bill.add_action( actor, action['orig'],
                        action['date'], brief_action_name=action['orig'],
                        type=simple_contain[testStr])
                    return True

            for testStr in simple_intro_match:
                if aText[:len(testStr)] == testStr:
                    bill.add_action( actor, action['orig'],
                        action['date'], brief_action_name=testStr,
                        type=simple_intro_match[testStr])
                    return True
            return False

        def _parse_senate_action():
            """
            Parse a string that contains "Senate". On failure to handle the string,
            we will return false, and let the fallback handler resolve the string.
            """
            actor = "upper"
            aText = action['action']

            testStr = "Senate Second Reading Special Order"
            if aText[:len(testStr)] == testStr:
                # get the status of the reading next
                bill_passfail = action['args'][0]
                normalized_brief = "Senate Second Reading %s" % (bill_passfail)
                bill.add_action( actor, action['orig'],
                    action['date'], brief_action_name=normalized_brief)
                return True

            # XXX: mangle this in with the bit above me
            testStr = "Senate Third Reading Special Order"
            if aText[:len(testStr)] == testStr:
                # get the status of the reading next
                if len(action['args']) == 0:
                    self.log("XXX: Skipping detailed digestion due to malformed"
                            " action line")
                    bill.add_action(actor, action['orig'],
                                    action['date'])
                    return True

                bill_passfail = action['args'][0]
                normalized_brief = "Senate Third Reading %s" % ( bill_passfail )
                bill.add_action( actor, action['orig'],
                    action['date'], brief_action_name=normalized_brief)
                return True

            simple_intro_match = {
                "Senate Second Reading Passed"          : [ "bill:reading:2" ],
                "Senate Third Reading Passed"           : [ "bill:reading:3" ],
                "Signed by the President of the Senate" : [ "other" ],
                "Senate Vote to Override Passed"        : \
                    [ "bill:veto_override:passed" ],
                "Senate Vote to Override Failed"        : \
                    [ "bill:veto_override:failed" ],
            }

            simple_contain = {
                "Refer Amended"   : [ "committee:passed" ],
                "Refer Unamended" : [ "committee:passed" ]
            }

            for testStr in simple_contain:
                if testStr in aText:
                    bill.add_action( actor, action['orig'],
                        action['date'], brief_action_name=action['orig'],
                        type=simple_contain[testStr])
                    return True

            for testStr in simple_intro_match:
                if aText[:len(testStr)] == testStr:
                    bill.add_action( actor, action['orig'],
                        action['date'], brief_action_name=testStr,
                        type=simple_intro_match[testStr] )
                    return True

            if aText == "Introduced In Senate":
                bill_assignd_ctty = action['args'][0]

                assgnd_to = "Assigned to"

                if bill_assignd_ctty[:len(assgnd_to)] == assgnd_to:
                    bill_assignd_ctty = bill_assignd_ctty[len(assgnd_to)+1:]

                bill.add_action( actor, action['orig'], action['date'],
                    type=[ "bill:introduced", "committee:referred" ],
                    assigned_ctty = bill_assignd_ctty,
                    brief_action_name="Introduced")
                return True

            return False

        def _parse_governor_action():
            """
            Parse a string that contains "Governor". On failure to handle the string,
            we will return false, and let the fallback handler resolve the string.
            """
            actor = "governor"
            aText = action['action']

            if aText == "Sent to the Governor":
                bill.add_action( "joint", action['orig'], action['date'],
                    brief_action_name=aText, type="governor:received" )
                return True

            if aText == "Governor Action":
                action_types = {
                    "Signed"       : [ "governor:signed" ],
                    "Partial Veto" : [ "governor:vetoed:line-item" ],
                    "Vetoed"       : [ "governor:vetoed" ],
                    "Became Law"   : [ "other" ],
                }
                scraped_type = "other"
                if action['args'][0] in action_types:
                    scraped_type = action_types[action['args'][0]]
                else:
                    self.log(" - gov. fallback handler for %s" % \
                        action['args'][0])

                bill.add_action( actor, action['orig'], action['date'],
                    brief_action_name=action['args'][0],
                    type=scraped_type)
                return True
            return False

        def _parse_action_fallback():
            """
            This is our fallback handler. If we haven't been able to process the
            line under other conditions, we will try to mangle this into some sort
            of useful snippit & include it.
            """
            hasHouse  = "House"  in action['action']
            hasSenate = "Senate" in action['action']

            if hasHouse and hasSenate:
                actor = 'joint'
            elif hasHouse:
                actor = 'lower'
            else:
                actor = 'upper'

            self.log( " - fallback handler for %s" % action['orig'] )

            bill.add_action( actor, action['orig'],
                action['date'],
                brief_action_name=action['action'],
                type="other")

        translation_routines = {
            "House"    : _parse_house_action,
            "Senate"   : _parse_senate_action,
            "Governor" : _parse_governor_action
        }

        for t in translation_routines:
            if t in action['action']:
                if not translation_routines[t]():
                    _parse_action_fallback()
                return
        _parse_action_fallback()

    def scrape_bill_sheet( self, session, chamber ):
        """
        Scrape the bill sheet (the page full of bills and other small bits of data)
        """
        sheet_url = self.get_bill_folder( session, chamber )

        bill_chamber = { "Senate" : "upper", "House" : "lower" }[chamber]

        index = {
            "id"            : 0,
            "title_sponsor" : 1,
            "version"       : 2,
            "history"       : 3,
            "votes"         : 7
        }

        with self.urlopen(sheet_url) as sheet_html:
            sheet_page = lxml.html.fromstring(sheet_html)

            bills = sheet_page.xpath('//table/tr')

            for bill in bills:
                bill_id = self.read_td(bill[index["id"]][0])

                if bill_id == None:
                    # Every other entry is null for some reason
                    continue

                bill_id = bill_id[:bill_id.find(".")]
                title_and_sponsor = bill[index["title_sponsor"]][0]

                bill_title = title_and_sponsor.text
                bill_title_and_sponsor = title_and_sponsor.text_content()
                sponsors = bill_title_and_sponsor.replace(bill_title, "").\
                    replace(" & ...", "").split("--")

                cats = {
                    "SB" : "bill",
                    "HB" : "bill",
                    "HR" : "resolution",
                    "SR" : "resolution",
                    "SCR" : "concurrent resolution",
                    "HCR" : "concurrent resolution",
                    "SJR" : "joint resolution",
                    "HJR" : "joint resolution",
                    "SM"  : "memorial",
                    "HM"  : "memorial"
                }

                bill_type = None

                for cat in cats:
                    if bill_id[:len(cat)] == cat:
                        bill_type = cats[cat]

                b = Bill(session, bill_chamber, bill_id, bill_title,
                    type=bill_type )

                b.add_source( sheet_url )

                versions_url = \
                    bill[index["version"]].xpath('font/a')[0].attrib["href"]
                versions_url = CO_URL_BASE + versions_url
                versions = self.parse_versions( versions_url )
                for version in versions:
                    b.add_version( version['name'], version['link'],
                        mimetype=version['mimetype'])

                bill_history_href = CO_URL_BASE + \
                    bill[index["history"]][0][0].attrib['href']
                    # ^^^^^^^ We assume this is a full path to the target.
                    # might want to consider some better rel-path support
                    # XXX: Look at this ^

                history = self.parse_history( bill_history_href )
                b.add_source( bill_history_href )

                for action in history:
                    self.add_action_to_bill( b, action )

                for sponsor in sponsors:
                    if sponsor != None and sponsor != "(NONE)" and \
                       sponsor != "":
                        b.add_sponsor("primary", sponsor)

                # Now that we have history, let's see if we can't grab some
                # votes

                bill_vote_href = self.get_vote_url( bill_id, session )
                votes = self.parse_votes( bill_vote_href )

                if votes['sanity-check'] != bill_id:
                    self.warning( "XXX: READ ME! Sanity check failed!" )
                    self.warning( " -> Scraped ID: " + votes['sanity-check'] )
                    self.warning( " -> 'Real' ID:  " + bill_id )
                    assert votes['sanity-check'] == bill_id

                for vote in votes['votes']:
                    filed_votes = vote['votes']
                    passage     = vote['meta']
                    result      = vote['result']

                    composite_time = "%s %s" % (
                        passage['x-parent-date'],
                        passage['TIME']
                    )
                    # It's now like: 04/01/2011 02:10:14 PM
                    pydate = dt.datetime.strptime( composite_time,
                        "%m/%d/%Y %I:%M:%S %p" )
                    hasHouse  = "House"  in passage['x-parent-ctty']
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
                        # self.log("BAZ: " + (l_vote))
                        if l_vote != "yes" and l_vote != "no":
                            local_other = local_other + 1

                    if local_other != other:
                        self.warning( \
                            "XXX: !!!WARNING!!! - resetting the 'OTHER' VOTES" )
                        self.warning( " -> Old: %s // New: %s" % (
                            other, local_other
                        ) )
                        other = local_other

                    v = Vote( actor, pydate, passage['MOTION'],
                        (result['FINAL_ACTION'] == "PASS"),
                        int(result['YES']), int(result['NO']),
                        other,
                        moved=passage['MOVED'],
                        seconded=passage['SECONDED'] )

                    v.add_source( vote['meta']['url'] )
                    # v.add_source( bill_vote_href )

                    # XXX: Add more stuff to kwargs, we have a ton of data
                    for voter in filed_votes:
                        who  = voter
                        vote = filed_votes[who]
                        if vote.lower() == "yes":
                            v.yes( who )
                        elif vote.lower() == "no":
                            v.no( who )
                        else:
                            v.other( who )
                    b.add_vote( v )
                self.save_bill(b)

    def scrape(self, chamber, session):
        """
        Entry point when invoking this from billy (or really whatever else)
        """
        chamber = {'lower': 'House', 'upper': 'Senate'}[chamber]
        self.scrape_bill_sheet( session, chamber )
