import os
import datetime
from zipfile import ZipFile

from billy.scrape.votes import VoteScraper, Vote

class NCVoteScraper(VoteScraper):
    state = 'nc'

    def scrape(self, chamber, session):
        if session == '2009':
            # 2009 files have a different delimiter and naming scheme.
            vote_data_url = 'ftp://www.ncga.state.nc.us/Bill_Status/Vote Data 2009.zip'
            naming_scheme = '{session}{file_label}.txt'
            delimiter = ";"
        else:
            vote_data_url = 'ftp://www.ncga.state.nc.us/Bill_Status/Votes%s.zip' % session
            naming_scheme = '{file_label}_{session}.txt'
            delimiter = "\t"
        fname, resp = self.urlretrieve(vote_data_url)
        # fname = "/Users/brian/Downloads/Vote Data 2009.zip"
        zf = ZipFile(fname)

        chamber_code = 'H' if chamber == 'lower' else 'S'

        # Members_YYYY.txt: tab separated
        # 0: id (unique only in chamber)
        # 1: H or S
        # 2: member name
        # 3-5: county, district, party
        # 6: mmUserId
        member_file = zf.open(naming_scheme.format(file_label='Members', session=session))
        members = {}
        for line in member_file.readlines():
            data = line.split(delimiter)
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
        # 21: PASSED/FAILED
        # 22: legislative day
        vote_file = zf.open(naming_scheme.format(file_label='Votes', session=session))
        bill_chambers = {'H':'lower', 'S':'upper'}
        votes = {}
        for line in vote_file.readlines():
            data = line.split(delimiter)
            if data[1] == chamber_code:
                date = datetime.datetime.strptime(data[2][:16],
                                                  '%Y-%m-%d %H:%M')
                if data[3][0] not in bill_chambers:
                    # skip votes that aren't on bills
                    self.log('skipping vote %s' % data[0])
                    continue

                votes[data[0]] = Vote(chamber, date, data[13],
                                      data[20] == 'PASSED',
                                      int(data[5]),
                                      int(data[6]),
                                      int(data[7])+int(data[8])+int(data[9]),
                                      bill_chamber=bill_chambers[data[3][0]],
                                      bill_id=data[3]+data[4], session=session)

        member_vote_file = zf.open(naming_scheme.format(file_label='MemberVotes', session=session))
        # 0: member id
        # 1: chamber (S/H)
        # 2: vote id
        # 3: vote chamber (always same as 1)
        # 4: vote (Y,N,E,X)
        # 5: pair ID (member)
        # 6: pair order
        # If a vote is paired then it should not be counted as a yes or no vote.
        # See https://github.com/sunlightlabs/openstates/issues/164
        for line in member_vote_file.readlines():
            data = line.split(delimiter)
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

        # remove file
        zf.close()
        os.remove(fname)
