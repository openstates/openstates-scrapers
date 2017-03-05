import os
from zipfile import ZipFile
from pupa.scrape import VoteEvent, Scraper


class NCVoteScraper(Scraper):

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        # special sessions need a ftp_session set
        if 'E' in session:
            ftp_session = session.replace('E', '_E')
        else:
            ftp_session = session
        # Unfortunately, you now have to request access to FTP.
        # This method of retrieving votes needs to be be changed or
        # fall back to traditional web scraping.
        if session == '2009':
            # 2009 files have a different delimiter and naming scheme.
            vote_data_url = 'ftp://www.ncleg.net/Bill_Status/Vote Data 2009.zip'
            naming_scheme = '{session}{file_label}.txt'
            delimiter = ";"
        else:
            vote_data_url = 'ftp://www.ncleg.net/Bill_Status/Votes%s.zip' % ftp_session
            naming_scheme = '{file_label}_{session}.txt'
            delimiter = "\t"
        fname, resp = self.urlretrieve(vote_data_url)
        zf = ZipFile(fname)

        chamber_code = 'H' if chamber == 'lower' else 'S'

        # Members_YYYY.txt: tab separated
        # 0: id (unique only in chamber)
        # 1: H or S
        # 2: member name
        # 3-5: county, district, party
        # 6: mmUserId
        member_file = zf.open(naming_scheme.format(file_label='Members', session=ftp_session))
        members = {}
        for line in member_file.readlines():
            data = line.decode().split(delimiter)
            if data[1] == chamber_code:
                members[data[0]] = data[2]

        # Votes_YYYY.txt
        # 0: sequence number
        # 1: chamber (S/H)
        # 2: date
        # 3: prefix
        # 4: bill_id
        # 5: yes votes
        # 6: no votes
        # 7: excused absences
        # 8: excused votes
        # 9: didn't votes
        # 10: total yes+no
        # 11: sponsor
        # 12: reading info
        # 13: info
        # 20: PASSED/FAILED
        # 21: legislative day
        vote_file = zf.open(naming_scheme.format(file_label='Votes', session=ftp_session))
        bill_chambers = {'H': 'lower', 'S': 'upper'}
        votes = {}
        for line in vote_file.readlines():
            data = line.decode().split(delimiter)
            if len(data) < 24:
                self.warning('line too short %s', data)
                continue
            if data[1] == chamber_code:
                date = data[2][:19]
                if data[3][0] not in bill_chambers:
                    # skip votes that aren't on bills
                    self.info('skipping vote %s' % data[0])
                    continue

                ve = VoteEvent(chamber=chamber,
                               start_date=date,
                               motion_text=data[13],
                               result='pass' if 'PASS' in data[20] else 'fail',
                               bill_chamber=bill_chambers[data[3][0]],
                               bill=data[3]+data[4],
                               legislative_session=session,
                               classification='passage',
                               )
                ve.set_count('yes', int(data[5]))
                ve.set_count('no', int(data[6]))
                ve.set_count('absent', int(data[7]))
                ve.set_count('excused', int(data[8]))
                ve.set_count('not voting', int(data[9]))
                votes[data[0]] = ve

        member_vote_file = zf.open(naming_scheme.format(file_label='MemberVotes',
                                                        session=ftp_session))
        # 0: member id
        # 1: chamber (S/H)
        # 2: vote id
        # 3: vote chamber (always same as 1)
        # 4: vote (Y,N,E,X)
        # 5: pair ID (member)
        # 6: pair order
        # If a vote is paired then it should be counted as an 'other'
        for line in member_vote_file.readlines():
            data = line.decode().split(delimiter)
            if data[1] == chamber_code:
                try:
                    member_voting = members[data[0]]
                except KeyError:
                    self.debug('Member %s not found.' % data[0])
                    continue
                try:
                    vote = votes[data[2]]
                except KeyError:
                    self.debug('Vote %s not found.' % data[2])
                    continue

                # -1 votes are Lt. Gov, not included in count, so we use a hacky way to
                # increment the counts
                if data[4] == 'Y' and not data[5]:
                    if data[0] == '-1':
                        for c in ve.counts:
                            if c['option'] == 'yes':
                                c['count'] += 1
                    vote.yes(member_voting)
                elif data[4] == 'N' and not data[5]:
                    if data[0] == '-1':
                        for c in ve.counts:
                            if c['option'] == 'no':
                                c['count'] += 1
                    vote.no(member_voting)
                else:
                    # for some reason other_count is high for paired votes so we use the hack
                    # to decrement counts
                    if data[5]:
                        for c in ve.counts:
                            if c['option'] == 'other':
                                c['count'] -= 1
                    # is either E: excused, X: no vote, or paired (doesn't count)
                    vote_type = {'E': 'excused', 'X': 'not voting', 'V': 'other'}[data[4]]
                    vote.vote(vote_type, member_voting)

        for vote in votes.values():
            vote.add_source(vote_data_url)
            yield vote

        # remove file
        zf.close()
        os.remove(fname)
