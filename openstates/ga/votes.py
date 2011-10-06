import datetime

import lxml.etree

from billy.scrape.votes import VoteScraper, Vote

class GAVoteScraper(VoteScraper):

    state = 'ga'

    def scrape(self, chamber, session):
        house_url = 'http://www1.legis.ga.gov/legis/%s/list/HouseVotes.xml'
        senate_url = 'http://www1.legis.ga.gov/legis/%s/list/SenateVotes.xml'
        self.scrape_chamber_votes(chamber, session, house_url % session)
        self.scrape_chamber_votes(chamber, session, senate_url % session)


    def scrape_chamber_votes(self, chamber, session, url):
        xml = self.urlopen(url)
        doc = lxml.etree.fromstring(xml)

        for vxml in doc.xpath('//vote'):
            legislation = vxml.get('legislation')
            motion = vxml.get('caption')
            timestamp = datetime.datetime.strptime(vxml.get('dateTime'),
                                                   '%Y-%m-%dT%H:%M:%S')

            leg_prefix = legislation.split(' ')[0]
            if leg_prefix in ('SB', 'SR'):
                bill_chamber = 'upper'
            elif leg_prefix in ('HB', 'HR'):
                bill_chamber = 'lower'
            elif leg_prefix in ('', 'EX', 'ELECTION'):
                continue
            else:
                raise Exception('unknown legislation prefix: ' + legislation)
            # skip bills from other chamber
            if bill_chamber != chamber:
                continue

            unknown_count = int(vxml.xpath('totals/@unknown')[0])
            excused_count = int(vxml.xpath('totals/@excused')[0])
            nv_count = int(vxml.xpath('totals/@not-voting')[0])
            no_count = int(vxml.xpath('totals/@nays')[0])
            yes_count = int(vxml.xpath('totals/@yeas')[0])
            other_count = unknown_count + excused_count + nv_count

            vote = Vote(chamber, timestamp, motion,
                        passed=yes_count > no_count, yes_count=yes_count,
                        no_count=no_count, other_count=other_count,
                        session=session, bill_id=legislation,
                        bill_chamber=bill_chamber)
            vote.add_source(url)

            for m in vxml.xpath('member'):
                vote_letter = m.get('vote')
                member = m.get('name')
                if vote_letter == 'Y':
                    vote.yes(member)
                elif vote_letter == 'N':
                    vote.no(member)
                else:
                    vote.other(member)

            self.save_vote(vote)
