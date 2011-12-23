import datetime as dt
import re
from collections import defaultdict
import lxml.html

from urlparse import urlparse

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote


CO_URL_BASE = "http://www.leg.state.co.us"
#                     ^^^ Yes, this is actually required

"""
This scraper is a bit bigger then some of the others, but it's just
a standard billy scraper. Methods are documented just because this
does both bill and vote scraping, and can be a big overwhelming.
"""
class COBillScraper(BillScraper):
    
    state = 'co'
    
    """
    This returns a URL to the bill "folder" - a list of all the bills for that
    session and chamber. If the URL looks funny, it's because CO has made
    some interesting technical choices.
    """
    def get_bill_folder( self, session, chamber ):
        chamber_id = "(bf-3)" if chamber == "House" else "(bf-2)"
        url = CO_URL_BASE + "/CLICS/CLICS" +  session \
            + "/csl.nsf/" + chamber_id + "?OpenView&Count=20000000"
        return url
        
   
    def read_td( self, td_node ):
        return td_node[0].text
        #      ^^^^^^^^^^ font
   

    """
    This will parse a vote page, with a list of who voted which way on what
    bill. This is invoked from `parse_votes', and invoking it directly may
    or may not be very useful.
    """
    def parse_all_votes( self, bill_vote_url ):
        ret = { "meta" : {}, 'votes' : {} }
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
                        passage_actions = to_parse.split()
                        # XXX: Verify we can't do this with recursive splits
                        # it now looks like:
                        # ['Final', 'YES:', '7', 'NO:', '6', 'EXC:', '0',
                        #   'ABS:', '0', 'FINAL_ACTION:', 'PASS']
                        passage_actions = passage_actions[1:]
                        il = iter(passage_actions)
                        final_score = dict(zip(il,il))

                        if not "FINAL_ACTION" in final_score:
                            final_score["FINAL_ACTION"] = False

                        ret['result'] = final_score
                    else:
                        # We've got a vote.
                        person = line[1].text_content() # it's inside a <div><font>
                        vote   = line[2].text_content()
                        if person.strip() != "":
                            ret['votes'][person] = vote
        return ret


    """
    This will parse all the votes on a given bill - basically, it looks on the
    page of all votes, and invokes `parse_all_votes' for each href it finds
    
    We do some minor sanity checking, so the caller will be able to ensure the
    bill IDs match exactly before going ahead with saving the data to the DB
    """
    def parse_votes( self, bill_vote_url ):
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
                        vote_page = CO_URL_BASE + \
                            vote_url
                        vote_dict = self.parse_all_votes( vote_page )  

                        vote_dict['meta']['x-parent-date'] = date
                        vote_dict['meta']['x-parent-ctty'] = ctty

                        ret['votes'].append( vote_dict )
                    except KeyError as e:
                        pass# print e
                    except IndexError as e:
                        pass# print e

        return ret


    """
    URL generator for getting the base vote pages. The links use all sorts of
    JS bouncing, so this will just fetch the end page.
    """
    def get_vote_url(self, billid, session):
        return CO_URL_BASE + \
            "/CLICS%5CCLICS" + session + \
            "%5Ccommsumm.nsf/IndSumm?OpenView&StartKey=" + billid + "&Count=4"

    """
    Parse a bill history page for as much data as we can gleen, such as when
    the bill was introduced (as well as a number of other things)
    """
    def parse_history( self, bill_history_url ):
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
   
    """
    We were able to get a bunch of actions, so this method handles
    mangling the human-readable descriptions in well tagged actions
    that we put into the DB.
    """
    def add_action_to_bill( self, bill, action ):
        # We have a few inner methods that handle each "type" of description.
        # This is mostly to keep things as clear as we can, and avoid huge and
        # unmaintainable chunks of code

        """
        Parse a string that contains "House". On failure to handle the string,
        we will return false, and let the fallback handler resolve the string.
        """
        def _parse_house_action():
            actor = "lower"
            HRActor = "House"
            aText = action['action']
            
            if aText == 'Introduced In House':
                # Typically, we're also including an assigned ctty
                bill_assignd_ctty = action['args'][0]
                assgnd_to = "Assigned to"
                if bill_assignd_ctty[:len(assgnd_to)] == assgnd_to:
                    bill_assignd_ctty = bill_assignd_ctty[len(assgnd_to)+1:]
                bill.add_action( actor, action['orig'], action['date'],
                    type="bill:introduced",
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

            simple_intro_match = [
                "House Second Reading Passed",
                "House Third Reading Passed",
                "Signed by the Speaker of the House"
            ]

            for testStr in simple_intro_match:
                if aText[:len(testStr)] == testStr:
                    bill.add_action( actor, action['orig'],
                        action['date'], brief_action_name=testStr )
                    return True
            return False

        """
        Parse a string that contains "Senate". On failure to handle the string,
        we will return false, and let the fallback handler resolve the string.
        """
        def _parse_senate_action():
            actor = "upper"
            HRActor = "Senate"
            aText = action['action']

            testStr = "Senate Second Reading Special Order"
            if aText[:len(testStr)] == testStr:
                # get the status of the reading next
                bill_passfail = action['args'][0]
                normalized_brief = "Senate Second Reading %s" % ( bill_passfail )
                bill.add_action( actor, action['orig'],
                    action['date'], brief_action_name=normalized_brief)
                return True

            # XXX: mangle this in with the bit above me
            testStr = "Senate Third Reading Special Order"
            if aText[:len(testStr)] == testStr:
                # get the status of the reading next
                bill_passfail = action['args'][0]
                normalized_brief = "Senate Third Reading %s" % ( bill_passfail )
                bill.add_action( actor, action['orig'],
                    action['date'], brief_action_name=normalized_brief)
                return True

            simple_intro_match = [
                "Senate Second Reading Passed",
                "Senate Third Reading Passed",
                "Signed by the President of the Senate"
            ]

            for testStr in simple_intro_match:
                if aText[:len(testStr)] == testStr:
                    bill.add_action( actor, action['orig'],
                        action['date'], brief_action_name=testStr )
                    return True

            if aText == "Introduced In Senate":
                bill_assignd_ctty = action['args'][0]

                assgnd_to = "Assigned to"

                if bill_assignd_ctty[:len(assgnd_to)] == assgnd_to:
                    bill_assignd_ctty = bill_assignd_ctty[len(assgnd_to)+1:]

                bill.add_action( actor, action['orig'], action['date'],
                    type="bill:introduced",
                    assigned_ctty = bill_assignd_ctty,
                    brief_action_name="Introduced")
                return True

            return False
        
        """
        Parse a string that contains "Governor". On failure to handle the string,
        we will return false, and let the fallback handler resolve the string.
        """
        def _parse_governor_action():
            actor = "governor"
            HRActor = "Governor"
            aText = action['action']

            if aText == "Sent to the Governor":
                bill.add_action( "legislature", action['orig'], action['date'],
                    brief_action_name=aText)
                return True

            if aText == "Governor Action":
                bill.add_action( actor, action['orig'], action['date'],
                    brief_action_name=action['args'][0] )
                return True

            return False

        """
        This is our fallback handler. If we haven't been able to process the
        line under other conditions, we will try to mangle this into some sort
        of useful snippit & include it.
        """
        def _parse_action_fallback():
            hasHouse  = "House"  in action['action']
            hasSenate = "Senate" in action['action']
            
            if hasHouse and hasSenate:
                actor = 'legislature'
            elif hasHouse:
                actor = 'lower'
            else:
                actor = 'upper'

            bill.add_action( actor, action['orig'], action['date'],
                brief_action_name=action['action'],
                type="other" ) # XXX: Fix this

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
    
    """
    Scrape the bill sheet (the page full of bills and other small bits of data)
    """
    def scrape_bill_sheet( self, session, chamber ):
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
               
                bill_history_href = CO_URL_BASE + \
                    bill[index["history"]][0][0].attrib['href']
                    # ^^^^^^^ We assume this is a full path to the target.
                    # might want to consider some better rel-path support
                    # XXX: Look at this ^
                
                history = self.parse_history( bill_history_href )
                b = Bill(session, bill_chamber, bill_id, bill_title)
                
                for action in history:
                    self.add_action_to_bill( b, action )
               
                for sponsor in sponsors:
                    b.add_sponsor("primary", sponsor)

                # Now that we have history, let's see if we can't grab some
                # votes

                bill_vote_href = self.get_vote_url( bill_id, session )
                votes = self.parse_votes( bill_vote_href )

                if votes['sanity-check'] != bill_id:
                    print "XXX: READ ME!"
                    print " -> Scraped ID: " + votes['sanity-check']
                    print " -> 'Real' ID:  " + bill_id
                    assert votes['sanity-check'] == bill_id

                for vote in votes['votes']:
                    print vote
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
                        actor = "legislature"
                    elif hasHouse:
                        actor = "lower"
                    else:
                        actor = "upper"

                    v = Vote( actor, pydate, passage['MOTION'],
                        (result['FINAL_ACTION'] == "YES"),
                        int(result['YES']), int(result['NO']),
                        int( result['EXC'] + result['ABS'] ),
                        moved=passage['MOVED'],
                        seconded=passage['SECONDED'] )
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
                    v.add_source( bill_vote_href )
                    b.add_vote( v )
                self.save_bill(b)
            
    """
    Entry point when invoking this from billy (or really whatever else)
    """
    def scrape(self, chamber, session):
        chamber = {'lower': 'House', 'upper': 'Senate'}[chamber]
        self.scrape_bill_sheet( session, chamber )
