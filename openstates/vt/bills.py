import datetime
import json
import re

from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote
from openstates.utils import LXMLMixin


class VTBillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'vt'

    def scrape(self, session, chambers):
        HTML_TAGS_RE = r'<.*?>'

        year_slug = session[5: ]
        
        # Load all bills via the private API
        bill_dump_url = \
                'http://legislature.vermont.gov/bill/loadBillsIntroduced/{}/'.\
                format(year_slug)
        json_data = self.urlopen(bill_dump_url)
        bills = json.loads(json_data)['data']

        # Parse the information from each bill
        for info in bills:
            # Strip whitespace from strings
            info = { k:v.strip() for k, v in info.iteritems() }

            # Create the bill using its basic information
            bill = Bill(
                    session=session,
                    bill_id=info['BillNumber'],
                    title=info['Title'],
                    chamber=(
                            'lower' if info['BillNumber'].startswith('H')
                            else 'upper'
                            ),
                    type='bill'
                    )
            bill.add_source(bill_dump_url)

            # Load the bill's information page to access its metadata
            bill_url = \
                    'http://legislature.vermont.gov/bill/status/{0}/{1}'.\
                    format(year_slug, info['BillNumber'])
            doc = self.lxmlize(bill_url)
            bill.add_source(bill_url)

            # Capture sponsors
            sponsors = doc.xpath(
                    '//dl[@class="summary-table"]/dt[text()="Sponsor(s)"]/'
                    'following-sibling::dd[1]/ul/li'
                    )
            sponsor_type = 'primary'
            for sponsor in sponsors:
                if sponsor.xpath('span/text()') == ['Additional Sponsors']:
                    sponsor_type = 'cosponsor'
                else:
                    sponsor_name = sponsor.xpath('a/text()')[0]

                if sponsor_name.startswith("Less") and len(sponsor_name) == 5:
                    continue

                if sponsor_name.startswith("Rep. "):
                    sponsor_name = sponsor_name[len("Rep. "): ]
                elif sponsor_name.startswith("Sen. "):
                    sponsor_name = sponsor_name[len("Sen. "): ]

                if sponsor_name.strip():
                    bill.add_sponsor(sponsor_type, sponsor_name)

            # Capture bill text versions
            versions = doc.xpath(
                    '//dl[@class="summary-table"]/dt[text()="Bill/Resolution Text"]/'
                    'following-sibling::dd[1]/ul/li/a'
                    )
            for version in versions:
                bill.add_version(
                        name=version.xpath('@href')[0],
                        url=version.xpath('text()')[0],
                        mimetype='application/pdf'
                        )

            # Identify the internal bill ID, used for actions and votes
            internal_bill_id = re.search(
                    r'"bill/loadBillDetailedStatus/{}/(\d+)"'.format(year_slug),
                    self.urlopen(bill_url)
                    ).group(1)

            # Capture actions
            actions_json = self.urlopen(
                    'http://legislature.vermont.gov/bill/loadBillDetailedStatus/{0}/{1}'.
                    format(year_slug, internal_bill_id)
                    )
            actions = json.loads(actions_json)['data']
            chambers_passed = ""
            for action in actions:
                action = { k:v.strip() for k, v in action.iteritems() }

                if "Signed by Governor" in action['FullStatus']:
                    actor = 'governor'
                elif action['ChamberCode'] == 'H':
                    actor = 'lower'
                elif action['ChamberCode'] == 'S':
                    actor = 'upper'
                else:
                    raise AssertionError("Unknown actor for bill action")

                # Categorize action
                if "Signed by Governor" in action['FullStatus']:
                    assert (
                            "H" in chambers_passed and
                            "S" in chambers_passed and
                            len(chambers_passed) == 2
                            )
                    action_type = 'governor:signed'
                elif actor == 'lower' and \
                        action['FullStatus'] in ("Passed", "Read Third time and Passed"):
                    action_type = 'bill:passed'
                    chambers_passed += "H"
                elif actor == 'upper' and \
                        action['FullStatus'].startswith("Read 3rd time & passed"):
                    action_type = 'bill:passed'
                    chambers_passed += "S"
                else:
                    action_type = 'other'

                bill.add_action(
                        actor=actor,
                        action=re.sub(HTML_TAGS_RE, "", action['FullStatus']),
                        date=datetime.datetime.strptime(action['StatusDate'], '%m/%d/%Y'),
                        type=action_type
                        )

            # Capture votes
            vote_url = 'http://legislature.vermont.gov/bill/loadBillRollCalls/{0}/{1}'.\
                    format(year_slug, internal_bill_id)
            vote_json = self.urlopen(vote_url)
            votes = json.loads(vote_json)['data']
            for vote in votes:
                
                roll_call_id = vote['VoteHeaderID']
                roll_call_url = 'http://legislature.vermont.gov/bill/loadBillRollCallDetails/{0}/{1}'.\
                        format(year_slug, roll_call_id)
                roll_call_json = self.urlopen(roll_call_url)
                roll_call = json.loads(roll_call_json)['data']

                roll_call_yea = []
                roll_call_nay = []
                roll_call_other = []
                for member in roll_call:
                    (member_name, _district) = member['MemberName'].split("of")
                    member_name = member_name.strip()
                    
                    if member['MemberVote'] == "Yea":
                        roll_call_yea.append(member_name)
                    elif member['MemberVote'] == "Nay":
                        roll_call_nay.append(member_name)
                    else:
                        roll_call_other.append(member_name)

                if "Passed -- " in vote['FullStatus']:
                    did_pass = True
                elif "Failed -- " in vote['FullStatus']:
                    did_pass = False
                else:
                    raise AssertionError("Roll call vote result is unclear")

                # Check vote counts
                yea_count = \
                        int(re.search(r'Yeas = (\d+)', vote['FullStatus']).group(1))
                nay_count = \
                        int(re.search(r'Nays = (\d+)', vote['FullStatus']).group(1))
                if yea_count != len(roll_call_yea) or \
                        nay_count != len(roll_call_nay):
                    raise AssertionError(
                            "Yea and/or nay counts incongruous:\n" +
                            "Yeas from vote text: {}\n".format(yea_count) +
                            "Yeas from number of members: {}\n".format(len(roll_call_yea)) +
                            "Nays from vote text: {}\n".format(nay_count) +
                            "Nays from number of members: {}".format(len(roll_call_nay))
                            )

                vote_to_add = Vote(
                        chamber=(
                                'lower' if vote['ChamberCode'] == 'H'
                                else 'upper'
                                ),
                        date=datetime.datetime.strptime(vote['StatusDate'], '%m/%d/%Y'),
                        motion=re.sub(HTML_TAGS_RE, "", vote['FullStatus']).strip(),
                        passed=did_pass,
                        yes_count=yea_count,
                        no_count=nay_count,
                        other_count=len(roll_call_other)
                        )
                vote_to_add.add_source(vote_url)
                vote_to_add.add_source(roll_call_url)

                for member in roll_call_yea:
                    vote_to_add.yes(member)
                for member in roll_call_nay:
                    vote_to_add.no(member)
                for member in roll_call_other:
                    vote_to_add.other(member)

                bill.add_vote(vote_to_add)

            # Capture extra information
            # This is not in the OpenStates spec, but is available
            # Not yet implemented
            # Witnesses: http://legislature.vermont.gov/bill/loadBillWitnessList/{year_slug}/{internal_bill_id}
            # Conference committee members: http://legislature.vermont.gov/bill/loadBillConference/{year_slug}/{bill_number}
            # Committee meetings: http://legislature.vermont.gov/committee/loadHistoryByBill/{year_slug}?LegislationId={internal_bill_id}

            self.save_bill(bill)
