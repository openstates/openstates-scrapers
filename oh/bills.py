import os
import datetime
from operator import itemgetter

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import xlrd
import scrapelib
import lxml.html


class OHBillScraper(BillScraper):
    jurisdiction = 'oh'

    def scrape(self, session, chambers):
        # Bills endpoint can sometimes take a very long time to load
        self.timeout = 300

        if int(session) < 128:
            raise AssertionError("No data for period {}".format(session))

        elif int(session) < 131:
            #they changed their data format starting in 131st and added
            #an undocumented API
            self.old_scrape(session)


            
        else:
            chamber_dict = {"Senate":"upper","House":"lower","House of Representatives":"lower","house":"lower","senate":"upper"}
            
            #so presumanbly not everything passes, but we haven't
            #seen anything not pass yet, so we'll need to wait
            #till it fails and get the right language in here
            vote_results = {"approved":True,
                            "passed":True,
                            "adopted":True,
                            "true":True,
                            "false":False,
                            "failed":False,
                            True:True,
                            False:False}

            action_dict = {"ref_ctte_100":"committee:referred",
                            "intro_100":"bill:introduced",
                            "pass_300":"bill:passed",
                            "intro_110":"bill:reading:1",
                            "refer_210":"committee:referred",
                            "crpt_301":"other",
                            "crpt_317": "other",
                            "concur_606": "bill:passed",
                            "pass_301": "bill:passed",
                            "refer_220": "committee:referred",
                            "intro_102":["bill:introduced","bill:passed"],
                            "intro_105":["bill:introduced","bill:passed"],
                            "intro_ref_ctte_100":"committee:referred",
                            "refer_209":"other",
                            "intro_108":["bill:introduced","bill:passed"],
                            "intro_103": ["bill:introduced","bill:passed"],
                            "msg_reso_503": "bill:passed",
                            "intro_107": ["bill:introduced","bill:passed"],
                            "imm_consid_360": "bill:passed",
                            "refer_213":"other",
                            "adopt_reso_100":"bill:passed",
                            "msg_507":"amendment:passed",
                            "confer_713":"other",
                            "concur_603":"other",
                            "confer_712":"other",
                            "msg_506":"amendment:failed",
                            "receive_message_100":"bill:passed",
                            }


            base_url = "http://search-prod.lis.state.oh.us"
            first_page = base_url + "/solarapi/v1/general_assembly_{session}/".format(session=session)
            legislators = self.get_legislator_ids(first_page)
            all_amendments = self.get_other_data_source(first_page,base_url,"amendments")
            all_fiscals = self.get_other_data_source(first_page,base_url,"fiscals")
            all_synopsis = self.get_other_data_source(first_page,base_url,"synopsiss")
            all_analysis = self.get_other_data_source(first_page,base_url,"analysiss")
            doc_types = ["bills","resolutions"]
            for doc_type in doc_types:
                bill_versions = {}
                for doc in self.pages(base_url,first_page+doc_type):
                    for v in doc["items"]:
                        #bills is actually a list of versions
                        #going to create a dictionary as follows:
                        #key=bill_id
                        #value = dict of all versions, where keys are versionids
                        #and values are the bill data from the api.
                        #then loop through that to avoid duplicate bills

                        try:
                            bill_id = v["number"]
                        except KeyError:
                            self.warning("Apparent bill has no information:\n{}".format(v))
                            continue

                        version_id = v["versionid"]
                        if bill_id in bill_versions:
                            if version_id in bill_versions[bill_id]:
                                self.logger.warning("There are two versions of {bill_id} called the same thing. Bad news bears!".format(bill_id=bill_id))
                            else:
                                bill_versions[bill_id][version_id] = v
                        else:
                            bill_versions[bill_id] = {}
                            bill_versions[bill_id][version_id] = v

                    

                for b in bill_versions:
                    bill = None
                    for bill_version in bill_versions[b].values():
                        if not bill:
                            bill_id = bill_version["number"]
                            title = bill_version["shorttitle"] or bill_version["longtitle"]

                            title = title.strip()

                            chamber = "lower" if "h" in bill_id else "upper"

                            subjects = []
                            for subj in bill_version["subjectindexes"]:
                                try:
                                    subjects.append(subj["primary"])
                                except KeyError:
                                    pass
                                try:
                                    secondary_subj = subj["secondary"]
                                except KeyError:
                                    secondary_subj = ""
                                if secondary_subj:
                                    subjects.append(secondary_subj)



                            #they use bill id of format HB 1 on the site
                            #but hb1 in the API.
    
                            for idx,char in enumerate(bill_id):
                                try:
                                    int(char)
                                except ValueError:
                                    continue

                                display_id = bill_id[:idx]+" "+bill_id[idx:]
                                break

                            assert doc_type.endswith('s'), "Only bills and resolutions accepted"
                            bill = Bill(session,chamber,display_id.upper(),title,subjects=subjects,type=doc_type[:-1])

                            #this stuff is the same for all versions

                            bill.add_source(first_page+doc_type+"/"+bill_id)

                            sponsors = bill_version["sponsors"]
                            for sponsor in sponsors:
                                sponsor_name = self.get_sponsor_name(sponsor)
                                bill.add_sponsor("primary",sponsor_name)

                            cosponsors = bill_version["cosponsors"]
                            for sponsor in cosponsors:
                                sponsor_name = self.get_sponsor_name(sponsor)
                                bill.add_sponsor("cosponsor",sponsor_name)

                            #actions
                            blacklist = ["/solarapi/v1/general_assembly_131/resolutions/lr_131_0035-1/actions"]
                            #the page in the blacklist just plain old failed to load
                            #and everything got stuck
                            try:
                                action_doc = self.get(base_url+bill_version["action"][0]["link"])
                            except scrapelib.HTTPError:
                                pass
                            else:

                                actions = action_doc.json()
                                for action in actions["items"]:
                                    actor = chamber_dict[action["chamber"]]
                                    action_desc = action["description"]
                                    try:
                                        action_type = action_dict[action["actioncode"]]
                                    except KeyError:
                                        self.warning("Unknown action {desc} with code {code}. Add it to the action_dict.".format(desc=action_desc, code=action["actioncode"]))
                                        action_type = "other"


                                    date = datetime.datetime.strptime(action["datetime"],"%Y-%m-%dT%H:%M:%S")

                                    committees = None
                                    if "committee" in action:
                                        committees = action["committee"]

                                    bill.add_action(actor,
                                                    action_desc,
                                                    date,
                                                    type = action_type,
                                                    committees = committees)

                            self.add_document(all_amendments, bill_id,"amendment",bill,base_url)
                            self.add_document(all_fiscals,bill_id,"fiscal",bill,base_url)
                            self.add_document(all_synopsis,bill_id,"synopsis",bill,base_url)
                            self.add_document(all_analysis,bill_id,"analysis",bill,base_url)

                            vote_url = base_url+bill_version["votes"][0]["link"]
                            vote_doc = self.get(vote_url)
                            votes = vote_doc.json()
                            self.process_vote(votes,vote_url,base_url,bill,legislators,chamber_dict,vote_results)

                            vote_url = base_url+bill_version["cmtevotes"][0]["link"]
                            try:
                                vote_doc = self.get(vote_url)
                            except scrapelib.HTTPError:
                                self.warning("Vote page not loading; skipping: {}".format(vote_url))
                                continue
                            votes = vote_doc.json()
                            self.process_vote(votes,vote_url,base_url,bill,legislators,chamber_dict,vote_results)


                            #we have never seen a veto or a disapprove, but they seem important.
                            #so we'll check and throw an error if we find one
                            #life is fragile. so are our scrapers.
                            if "veto" in bill_version:
                                veto_url = base_url+bill_version["veto"][0]["link"]
                                veto_json = self.get(veto_url).json()
                                if len(veto_json["items"]) > 0:
                                    raise AssertionError("Whoa, a veto! We've never gotten one before. Go write some code to deal with it: {}".format(veto_url))

                            if "disapprove" in bill_version:
                                disapprove_url = base_url+bill_version["disapprove"][0]["link"]
                                disapprove_json = self.get(disapprove_url).json()
                                if len(disapprove_json["items"]) > 0:
                                    raise AssertionError("Whoa, a disapprove! We've never gotten one before. Go write some code to deal with it: {}".format(disapprove_url))




                        #this stuff is version-specific
                        version_name = bill_version["version"]
                        version_link = base_url+bill_version["pdfDownloadLink"]
                        mimetype = "application/pdf" if version_link.endswith("pdf") else "application/octet-stream"
                        bill.add_version(version_name,version_link,mimetype=mimetype)

                    # Need to sort bill actions, since they may be jumbled
                    bill['actions'] = sorted(bill['actions'], key=itemgetter('date'))

                    self.save_bill(bill)

    def pages(self,base_url, first_page):
        page = self.get(first_page)
        page = page.json()
        yield page
        while "nextLink" in page:
            page = self.get(base_url+page["nextLink"])
            page = page.json()
            yield page


    def get_other_data_source(self,first_page,base_url,source_name):
        #produces a dictionary from bill_id to a list of
        #one of the following:
        #amendments, analysis, fiscals, synopsis
        #could pull these by bill, but doing it in bulk
        #and then matching on our end will get us by with way fewer
        #api calls
        
        bill_dict = {}
        for page in self.pages(base_url,first_page+source_name):
            for item in page["items"]:
                billno = item["billno"]
                if billno not in bill_dict:
                    bill_dict[billno] = []
                bill_dict[billno].append(item)

        return bill_dict



    def add_document(self,documents,bill_id,type_of_document,bill,base_url):
        try:
            documents = documents[bill_id]
        except KeyError:
            return

        leg_ver_types = {"IN":"Introduction",
                            "RS": "Reported: Senate",
                            "PS":"Passed: Senate",
                            "RH": "Reported: House",
                            "PH": "Passed: House",
                            "":"",
                            "ICS":"",
                            "RCS":"",
                            "EN":"Enacted",
                            "RCH":"Re-referred",
                            "PHC":""
                            }

        for item in documents:
            if type_of_document == "amendment":
                name = item["amendnum"] + " " + item["version"]
            else:
                name = item["name"] or type_of_document
            link = base_url+item["link"]+"?format=pdf"
            try:
                self.head(link)
            except scrapelib.HTTPError:
                self.logger.warning("The link to doc {name} does not exist, skipping".format(name=name))
                continue
            if "legacyver" in item:
                try:
                    ver = leg_ver_types[item["legacyver"]]
                except KeyError:
                    self.logger.warning(
                        "New legacyver; check the type and add it to the "
                        "leg_ver_types dictionary: {} ({})".format(
                        item["legacyver"], item['link']))
                    ver = ""
                if ver:
                    name = name+": "+ver
            bill.add_document(name,link,mimetype="application/pdf")


    def get_legislator_ids(self,base_url):
        legislators = {}
        for chamber in ["House", "Senate"]:
            doc = self.get(base_url+"chamber/{chamber}/legislators?per_page=100".format(chamber=chamber))
            leg_json = doc.json()
            for leg in leg_json["items"]:
                legislators[leg["med_id"]] = leg["displayname"]

        return legislators


    def get_sponsor_name(self,sponsor):
        return " ".join([sponsor["firstname"],sponsor["lastname"]])

    def process_vote(self,votes,url,base_url,bill,legislators,chamber_dict,vote_results):
        for v in votes["items"]:
            try:
                v["yeas"]
            except KeyError:
                #sometimes the actual vote is buried a second layer deep
                v = self.get(base_url+v["link"]).json()
                try:
                    v["yeas"]
                except KeyError:
                    self.logger.warning("No vote info available, skipping")
                    continue

            try:
                chamber = chamber_dict[v["chamber"]]
            except KeyError:
                chamber = "lower" if "house" in v["apn"] else "upper"
            try:
                date = datetime.datetime.strptime(v["date"],"%m/%d/%y")
            except KeyError:
                try:
                    date = datetime.datetime.strptime(v["occurred"],"%m/%d/%y")
                except KeyError:
                    self.logger.warning("No date found for vote, skipping")
                    continue
            try:
                motion = v["action"]
            except KeyError:
                motion = v["motiontype"]

            # Sometimes Ohio's SOLAR will only return part of the JSON, so in that case skip
            if not motion and isinstance(v['yeas'], basestring) and isinstance(v['nays'], basestring):
                self.warning('Malformed JSON found for vote ("revno" of {}); skipping'.format(v['revno']))
                continue

            result = v.get("results") or v.get("passed")
            if result is None:
                if len(v['yeas']) > len(v['nays']):
                    result = "passed"
                else:
                    result = "failed"

            passed = vote_results[result.lower()]
            committee = None
            if "committee" in v:
                vote = Vote(chamber,date,motion,passed,0,0,0,yes_votes=[],no_votes=[],other_votes=[],committee=v["committee"])
            else:
                vote = Vote(chamber,date,motion,passed,0,0,0,yes_votes=[],no_votes=[],other_votes=[])
            #the yea and nay counts are not displayed, but vote totals are
            #and passage status is.
            for voter_id in v["yeas"]:
                vote["yes_votes"].append(legislators[voter_id])
                vote["yes_count"] += 1
            for voter_id in v["nays"]:
                vote["no_votes"].append(legislators[voter_id])
                vote["no_count"] += 1
            if "absent" in v:
                for voter_id in v["absent"]:
                    vote["other_votes"].append(legislators[voter_id])
                    vote["other_count"] += 1
            if "excused" in v:
                for voter_id in v["excused"]:
                    vote["other_votes"].append(legislators[voter_id])
                    vote["other_count"] += 1

            #check to see if there are any other things that look
            #like vote categories, throw a warning if so
            for key,val in v.items():
                if type(val) == list and len(val) > 0 and key not in ["yeas","nays","absent","excused"]:
                    if val[0] in legislators:
                        self.logger.warning("{k} looks like a vote type that's not being counted. Double check it?".format(k = key))
            vote.add_source(url)

            bill.add_vote(vote)


    def old_scrape(self,session):
        status_report_url = "http://www.legislature.ohio.gov/legislation/status-reports"

        #ssl verification off due Ohio not correctly implementing SSL
        doc = self.get(status_report_url,verify=False).text
        doc = lxml.html.fromstring(doc)
        doc.make_links_absolute(status_report_url)

        status_table = doc.xpath("//div[contains(text(),'{}')]/following-sibling::table".format(session))[0]
        status_links = status_table.xpath(".//a[contains(text(),'Excel')]/@href")


        for url in status_links:

            try:
                fname, resp = self.urlretrieve(url)
            except scrapelib.HTTPError:
                self.logger.warning("Missing report {}".format(report))
                continue

            sh = xlrd.open_workbook(fname).sheet_by_index(0)

            # once workbook is open, we can remove tempfile
            os.remove(fname)
            for rownum in range(1, sh.nrows):
                bill_id = sh.cell(rownum, 0).value

                bill_type = "resolution" if "R" in bill_id else "bill"
                chamber = "lower" if "H" in bill_id else "upper"

                bill_title = str(sh.cell(rownum, 3).value)

                bill = Bill(session, chamber, bill_id, bill_title,
                            type=bill_type)
                bill.add_source(url)
                bill.add_sponsor('primary', str(sh.cell(rownum, 1).value))

                # add cosponsor
                if sh.cell(rownum, 2).value:
                    bill.add_sponsor('cosponsor',
                                     str(sh.cell(rownum, 2).value))

                actor = ""

                # Actions start column after bill title
                for colnum in range(4, sh.ncols - 1):
                    action = str(sh.cell(0, colnum).value)
                    cell = sh.cell(rownum, colnum)
                    date = cell.value

                    if len(action) != 0:
                        if action.split()[0] == 'House':
                            actor = "lower"
                        elif action.split()[0] == 'Senate':
                            actor = "upper"
                        elif action.split()[-1] == 'Governor':
                            actor = "executive"
                        elif action.split()[0] == 'Gov.':
                            actor = "executive"
                        elif action.split()[-1] == 'Gov.':
                            actor = "executive"

                    if action in ('House Intro. Date', 'Senate Intro. Date'):
                        atype = ['bill:introduced']
                        action = action.replace('Intro. Date', 'Introduced')
                    elif action == '3rd Consideration':
                        atype = ['bill:reading:3', 'bill:passed']
                    elif action == 'Sent to Gov.':
                        atype = ['governor:received']
                    elif action == 'Signed By Governor':
                        atype = ['governor:signed']
                    else:
                        atype = ['other']

                    if type(date) == float:
                        date = str(xlrd.xldate_as_tuple(date, 0))
                        date = datetime.datetime.strptime(
                            date, "(%Y, %m, %d, %H, %M, %S)")
                        bill.add_action(actor, action, date, type=atype)

                for idx,char in enumerate(bill_id):
                    try:
                        int(char)
                    except ValueError:
                        continue

                    underscore_bill = bill_id[:idx]+"_"+bill_id[idx:]
                    break

                self.scrape_votes_old(bill, underscore_bill, session)
                self.scrape_versions_old(bill, underscore_bill, session)
                self.save_bill(bill)

    def scrape_versions_old(self, bill, billname, session):
        base_url = 'http://archives.legislature.state.oh.us/'

        if 'R' in billname:
            piece = '/res.cfm?ID=%s_%s' % (session, billname)
        else:
            piece = '/bills.cfm?ID=%s_%s' % (session, billname)

        def _get_html_or_pdf_version_old(url):
            doc = lxml.html.fromstring(url)
            name = doc.xpath('//font[@size="2"]/a/text()')[0]
            html_links = doc.xpath('//a[text()="(.html format)"]')
            pdf_links = doc.xpath('//a[text()="(.pdf format)"]')
            if html_links:
                link = html_links[0].get('href')
                bill.add_version(name, base_url + link, on_duplicate='use_old',
                                 mimetype='text/html')
            elif pdf_links:
                link = pdf_links[0].get('href')
                bill.add_version(name, base_url + link,
                                 mimetype='application/pdf')

        html = self.get(base_url + piece).text
        # pass over missing bills - (unclear why this happens)
        if 'could not be found.' in html:
            self.warning('missing page: %s' % base_url + piece)
            return

        _get_html_or_pdf_version_old(html)
        doc = lxml.html.fromstring(html)
        for a in doc.xpath('//a[starts-with(@href, "/bills.cfm")]/@href'):
            if a != piece:
                _get_html_or_pdf_version_old(self.get(base_url + a).text)
        for a in doc.xpath('//a[starts-with(@href, "/res.cfm")]/@href'):
            if a != piece:
                _get_html_or_pdf_version_old(self.get(base_url + a).text)

    def scrape_votes_old(self, bill, billname, session):
        vote_url = ('http://archives.legislature.state.oh.us/bills.cfm?ID=' +
                    session + '_' + billname)

        page = self.get(vote_url).text
        page = lxml.html.fromstring(page)

        for jlink in page.xpath("//a[contains(@href, 'JournalText')]"):
            date = datetime.datetime.strptime(jlink.text,
                                              "%m/%d/%Y").date()

            details = jlink.xpath("string(../../../td[2])")

            chamber = details.split(" - ")[0]
            if chamber == 'House':
                chamber = 'lower'
            elif chamber == 'Senate':
                chamber = 'upper'
            else:
                raise ScrapeError("Bad chamber: %s" % chamber)

            motion = details.split(" - ")[1].split("\n")[0].strip()

            vote_row = jlink.xpath("../../..")[0].getnext()

            yea_div = vote_row.xpath(
                "td/font/div[contains(@id, 'Yea')]")[0]
            yeas = []
            for td in yea_div.xpath("table/tr/td"):
                name = td.xpath("string()")
                if name:
                    yeas.append(name)

            no_div = vote_row.xpath(
                "td/font/div[contains(@id, 'Nay')]")[0]
            nays = []
            for td in no_div.xpath("table/tr/td"):
                name = td.xpath("string()")
                if name:
                    nays.append(name)

            yes_count = len(yeas)
            no_count = len(nays)

            vote = Vote(chamber, date, motion, yes_count > no_count,
                        yes_count, no_count, 0)

            for yes in yeas:
                vote.yes(yes)
            for no in nays:
                vote.no(no)

            vote.add_source(vote_url)

            bill.add_vote(vote)
