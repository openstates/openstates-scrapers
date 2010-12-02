from zipfile import ZipFile
import datetime

from fiftystates.scrape.votes import VoteScraper, Vote

class NCVoteScraper(VoteScraper):
    state = 'nc'

    def scrape(self, chamber, session):
        vote_data_url = 'ftp://www.ncga.state.nc.us/Votes/Vote%20Data.zip'
        fname, resp = self.urlretrieve(vote_data_url)
        zf = ZipFile(fname)

        chamber_code = 'H' if chamber == 'lower' else 'S'

        # Members.txt
        # 0: id (unique only in chamber)
        # 1: H or S
        # 2: member name
        member_file = zf.open(session + 'Members.txt')
        members = {}
        for line in member_file.readlines():
            data = line.split(';')
            if data[1] == chamber_code:
                members[data[0]] = data[2]

        # Votes.txt
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
        # 15-20: not used
        # 21: PASSED/FAILED
        # 22: legislative day
        vote_file = zf.open(session + 'Votes.txt')
        bill_chambers = {'H':'lower', 'S':'upper'}
        votes = {}
        for line in vote_file.readlines():
            data = line.split(';')
            if data[1] == chamber_code:
                date = datetime.datetime.strptime(data[2][:16],
                                                  '%Y-%m-%d %H:%M')
                if data[3][0] not in bill_chambers:
                    self.log('skipping vote %s' % data[0])
                    continue
                votes[data[0]] = Vote(chamber, date, data[13],
                                      data[21] == 'PASSED',
                                      int(data[5]),
                                      int(data[6]),
                                      int(data[7])+int(data[8])+int(data[9]),
                                      bill_chamber=bill_chambers[data[3][0]],
                                      bill_id=data[3]+data[4], session=session,
                                      filename=data[1]+'seq_'+data[0])

        member_vote_file = zf.open(session + 'MemberVotes.txt')
        # 0: member id
        # 1: chamber (S/H)
        # 2: vote id
        # 3: vote chamber (always same as 1)
        # 4: vote (Y,N,E,X)
        for line in member_vote_file.readlines():
            data = line.split(';')
            if data[1] == chamber_code:
                try:
                    vote = votes[data[2]]
                    if data[4] == 'Y':
                        vote.yes(members[data[0]])
                    elif data[4] == 'N':
                        vote.no(members[data[0]])
                    else:
                        # is either E: excused, X: no vote
                        vote.other(members[data[0]])
                except KeyError:
                    self.debug('not recording roll call for %s' % data[2])
                    pass

        for vote in votes.itervalues():
            self.save_vote(vote)
