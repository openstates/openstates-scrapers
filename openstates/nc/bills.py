import datetime as dt
import lxml.html
import re
from pupa.scrape import Bill, Scraper, VoteEvent
import pytz

eastern = pytz.timezone("US/Eastern")

archived_votes = {}

class NCBillScraper(Scraper):

    _action_classifiers = {
        "Vetoed": "executive-veto",
        "Signed By Gov": "executive-signature",
        "Signed by Gov": "executive-signature",
        "Pres. To Gov.": "executive-receipt",
        "Withdrawn from ": "withdrawal",
        "Ref ": "referral-committee",
        "Re-ref ": "referral-committee",
        "Reptd Fav": "committee-passage-favorable",
        "Reptd Unfav": "committee-passage-unfavorable",
        "Passed 1st Reading": "reading-1",
        "Passed 2nd Reading": "reading-2",
        "Passed 3rd Reading": ["passage", "reading-3"],
        "Passed 2nd & 3rd Reading": ["passage", "reading-2", "reading-3"],
        "Failed 3rd Reading": ["failure", "reading-3"],
        "Filed": "introduction",
        "Adopted": "passage",  # resolutions
        "Concurred In": "amendment-passage",
        "Com Amend Adopted": "amendment-passage",
        "Assigned To": "referral-committee",
        "Amendment Withdrawn": "amendment-withdrawal",
        "Amendment Offered": "amendment-introduction",
        "Amend Failed": "amendment-failure",
        "Amend Adopted": "amendment-passage",
        "Became Law W/o Signature": "became-law",
        "Ch.": "became-law",
        "Veto Overridden": "veto-override-passage",
    }

    def scrape_bill(self, chamber, session, bill_id):
        # there will be a space in bill_id if we're doing a one-off bill scrape
        # convert HB 102 into H102
        if " " in bill_id:
            bill_id = bill_id[0] + bill_id.split(" ")[-1]

        # if chamber comes in as House/Senate convert to lower/upper
        if chamber == "Senate":
            chamber = "upper"
        elif chamber == "House":
            chamber = "lower"

        bill_detail_url = (
            "http://www.ncleg.net/gascripts/"
            "BillLookUp/BillLookUp.pl?Session=%s&BillID=%s&votesToView=all"
        ) % (session, bill_id)

        # parse the bill data page, finding the latest html text
        data = self.get(bill_detail_url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(bill_detail_url)

        title_div_txt = doc.xpath('//div[contains(@class, "h2")]/text()')[0]
        if "Joint Resolution" in title_div_txt:
            bill_type = "joint resolution"
            bill_id = bill_id[0] + "JR " + bill_id[1:]
        elif "Resolution" in title_div_txt:
            bill_type = "resolution"
            bill_id = bill_id[0] + "R " + bill_id[1:]
        elif "Bill" in title_div_txt:
            bill_type = "bill"
            bill_id = bill_id[0] + "B " + bill_id[1:]


        bill_title = doc.xpath(    
            '/html[1]/body[1]/div[1]/div[1]/main[1]/div[2]/div[1]'
        )[0]
        bill_title = bill_title.text_content().strip()
        if bill_title is '':
            bill_title = bill_id.replace(" ", "")

        bill = Bill(
            bill_id,
            legislative_session=session,
            title=bill_title,
            chamber=chamber,
            classification=bill_type,
        )
        bill.add_source(bill_detail_url)

        # skip first PDF link (duplicate link to cur version)
        if chamber == "lower":
            link_xpath = '//a[contains(@href, "/Bills/House/PDF/")]'
        else:
            link_xpath = '//a[contains(@href, "/Bills/Senate/PDF/")]'
        for vlink in doc.xpath(link_xpath)[1:]:
            # get the name from the PDF link...
            version_name = vlink.text.replace(u"\xa0", " ")
            version_url = vlink.attrib["href"]

            media_type = "text/html"
            if version_url.lower().endswith(".pdf"):
                media_type = "application/pdf"

            bill.add_version_link(
                version_name, version_url, media_type=media_type, on_duplicate="ignore"
            )

        # rows with a 'adopted' in the text and an amendment link, skip failed amds
        for row in doc.xpath(
            '//div[@class="card-body"]/div[contains(., "Adopted")'
            ' and contains(@class,"row")]//a[@title="Amendment"]'
        ):
            version_url = row.xpath("@href")[0]
            version_name = row.xpath("string(.)").strip()
            bill.add_version_link(
                version_name,
                version_url,
                media_type="application/pdf",
                on_duplicate="ignore",
            )

        # sponsors
        spon_row = doc.xpath(
            '//div[contains(text(), "Sponsors")]/following-sibling::div'
        )[0]
        # first sponsors are primary, until we see (Primary)
        spon_type = "primary"
        spon_lines = spon_row.text_content().replace("\r\n", ";")
        for leg in spon_lines.split(";"):
            name = leg.replace(u"\xa0", " ").strip()
            if name.startswith("(Primary)") or name.endswith("(Primary)"):
                name = name.replace("(Primary)", "").strip()
                spon_type = "cosponsor"
            if not name:
                continue
            bill.add_sponsorship(
                name,
                classification=spon_type,
                entity_type="person",
                primary=(spon_type == "primary"),
            )

        # keywords
        kw_row = doc.xpath(
            '//div[contains(text(), "Keywords:")]/following-sibling::div'
        )[0]
        for subject in kw_row.text_content().split(", "):
            bill.add_subject(subject)

        # actions
        action_tr_xpath = (
            '//h6[contains(text(), "History")]'
            '/ancestor::div[contains(@class, "gray-card")]'
            '//div[contains(@class, "card-body")]'
            '/div[@class="row"]'
        )

        # skip two header rows
        for row in doc.xpath(action_tr_xpath):
            cols = row.xpath("div")
            act_date = cols[1].text
            actor = cols[3].text or ""
            # if text is blank, try diving in
            action = (cols[5].text or "").strip() or cols[5].text_content().strip()

            if act_date is None:
                search_action_date = action.split()
                for act in search_action_date:
                    try:
                        if '/' in act:
                            # try:
                            act_date = dt.datetime.strptime(act, '%m/%d/%Y').strftime('%Y-%m-%d')
                            #     print(type(act_date))
                            # except KeyError:
                            #     raise Exception("No Action Date Provided")
                    except KeyError:
                        raise Exception("No Action Date Provided")
            else:
                act_date = dt.datetime.strptime(act_date, '%m/%d/%Y').strftime('%Y-%m-%d')

            if actor == "Senate":
                actor = "upper"
            elif actor == "House":
                actor = "lower"
            else:
                actor = "executive"

            for pattern, atype in self._action_classifiers.items():
                if action.startswith(pattern):
                    break
            else:
                atype = None
            if act_date is not None:
                bill.add_action(action, act_date, chamber=actor, classification=atype)

        # TODO: Fix vote scraper
        for row in doc.xpath("//h6[@id='vote-header']"):
            yield from self.scrape_votes(bill, doc)

        # For archived votes
        if session in ['1997', '1999']:
            yield from self.add_archived_votes(bill, bill_id)

        yield bill

    def scrape_votes(self, bill, doc):
        vote_tr_path = (
            '//h6[@id="vote-header"]'
            '/ancestor::div[contains(@class, "gray-card")]'
            '//div[contains(@class, "card-body")]'
            '//div[@class="row"]'
        )

        for vote_row in doc.xpath(vote_tr_path):
            entries = [each.text_content() for each in vote_row.xpath("div")[1:-1:2]]
            date, subject, rcs, aye, no, nv, abs, exc, total = entries
            result = vote_row.xpath("div/a")[0]
            result_text = result.text
            result_link = result.get("href")

            if "H" in rcs:
                chamber = "lower"
            elif "S" in rcs:
                chamber = "upper"

            date = eastern.localize(
                dt.datetime.strptime(date.replace(".", ""), "%m/%d/%Y %H:%M %p")
            )
            date = date.isoformat()

            ve = VoteEvent(
                chamber=chamber,
                start_date=date,
                motion_text=subject,
                result="pass" if "PASS" in result_text else "fail",
                bill=bill,
                classification="passage",  # TODO: classify votes
            )
            ve.set_count("yes", int(aye))
            ve.set_count("no", int(no))
            ve.set_count("not voting", int(nv))
            ve.set_count("absent", int(abs))
            ve.set_count("excused", int(exc))
            ve.add_source(result_link)

            data = self.get(result_link).text
            vdoc = lxml.html.fromstring(data)

            # only one table that looks like this
            vote_table = vdoc.xpath("//div[@class='row ncga-row-no-gutters']")

            # Grabs names for how people voted
            for row in vote_table:
                votes_names = []
                row = row.text_content()
                if "None" in row:
                    vote_type = "Nope"
                elif "Ayes (" in row:
                    row = row.replace("\n", ";")
                    votes_names = row.replace(" ", "").strip().split(";")[2:-1]
                    vote_type = "yes"
                elif "Noes (" in row:
                    row = row.replace("\n", ";")
                    votes_names = row.replace(" ", "").strip().split(";")[2:-1]
                    vote_type = "no"
                elif "Excused Absence (" in row:
                    row = row.replace("\n", ";")
                    votes_names = row.replace(" ", "").strip().split(";")[2:-1]
                    vote_type = "absent"
                elif "Not Voting (" in row:
                    row = row.replace("\n", ";")
                    votes_names = row.replace(" ", "").strip().split(";")[2:-1]
                    vote_type = "abstain"
                else:
                    vote_type = "Not a vote"
                if votes_names:
                    for name in votes_names:
                        ve.vote(vote_type, name)

            yield ve

    # Adds archived votes
    def add_archived_votes(self, bill, bill_id):
        bill_id = bill_id.split()
        bill_id[0] = bill_id[0][0]
        if len(bill_id[-1]) == 2:
            bill_id[-1] = "00" + bill_id[-1]
        if len(bill_id[-1]) == 3:
            bill_id[-1] = "0" + bill_id[-1]
        bill_id = "".join(bill_id)
        print("Bill ID", bill_id)
        if bill_id in archived_votes:
            votes = archived_votes[bill_id]
            print("Total votes for bill:", len(votes))
        yield bill

    # Specifically meant for scraping 1997 and 1999 sessions
    def scrape_archived_votes(self, chamber, session):
        chamber_abbr = "S" if chamber == "upper" else "H"
        url = f"https://www.ncleg.gov/Legislation/Votes/MemberVoteHistory/{session}/{chamber_abbr}"
        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(url)

        rep_links = doc.xpath('//option/@value')[1:]
        print("Representatives:", len(rep_links))
        for rep_link in rep_links:
            rep_url = f"https://www.ncleg.gov/Legislation/Votes/MemberVoteHistory/{session}/{chamber_abbr}/{rep_link}"
            print(rep_url)

            # Scrapping detailed vote pages for archived representatives
            rep_data = self.get(rep_url).text
            rep_doc = lxml.html.fromstring(rep_data)
            rep_doc.make_links_absolute(rep_url)

            rep_name = rep_doc.xpath("//div[@class='section-title']")[0].text.split()[1:-2]
            rep_name = " ".join(rep_name)

            # print(rep_name)

            vote_text = rep_doc.xpath('//pre')[0].text.splitlines()
            for x in range(len(vote_text)):
                line = vote_text[x].split()
                if line and re.match(r"[H, S]\d\d\d\d", line[0]):
                    bill_id = line[0]

                    # Designates where the X is placed to indicate a vote
                    yes_location = 59
                    no_location = 64
                    noVt_location = 69
                    exAb_location = 74
                    exVt_location = 79

                    vote_details_line = vote_text[x+1]
                    vote_date = vote_details_line[2:20]
                    vote_date = dt.datetime.strptime(vote_date, "%b %d, %Y %H:%M")
                    print(vote_date)

                    r_number = vote_details_line[21:23]
                    a_number = vote_details_line[25:28]

                    rep_vote = vote_text[x+2]
                    vote_location = rep_vote.rfind("X")

                    if vote_location == yes_location:
                        how_voted = "yes"
                    elif vote_location == no_location:
                        how_voted = "no"
                    elif vote_location == noVt_location:
                        how_voted = "other"
                    elif vote_location == exAb_location:
                        how_voted == "absent"
                    else:
                        how_voted = "excused"

                    # print("Bill ID", bill_id, "How Voted:", how_voted)
                    if bill_id in archived_votes:
                        archived_votes[bill_id].append({
                            "leg": rep_name,
                            "how_voted": how_voted})
                    else:
                        archived_votes[bill_id] = [{
                            "leg": rep_name,
                            "how_voted": how_voted
                        }]


    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:

            if session in ['1997', '1999']:
                self.scrape_archived_votes(chamber, session)
                # yield from self.scrape_chamber(chamber, session)
                # print(archived_votes)
            else:
                yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber = {"lower": "House", "upper": "Senate"}[chamber]
        url = "https://www3.ncleg.gov/gascripts/SimpleBillInquiry/displaybills.pl"
        post_data = {"Session": session, "tab": "Chamber", "Chamber": chamber}

        data = self.post(url, post_data).text
        doc = lxml.html.fromstring(data)
        for row in doc.xpath("//table[@cellpadding=3]/tr")[1:]:
            bill_id = row.xpath("td[1]/a/text()")[0]
            yield from self.scrape_bill(chamber, session, bill_id)


def vote_list_to_names(names):
    title, rest = names.split(": ", 1)
    if "None" in rest:
        return []
    return rest.split("; ")
