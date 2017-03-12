import re

from billy.scrape.committees import CommitteeScraper, Committee

from .utils import db_cursor


class NHCommitteeScraper(CommitteeScraper):
    jurisdiction = 'nh'

    _chamber_map = {
        'upper': 'S',
        'lower': 'H',
    }

    def _parse_committees(self, chamber):
        """Queries and returns a dict for legislative committees."""
        chamber_code = NHCommitteeScraper._chamber_map[chamber]

        query = "SELECT "\
            "Committees.CommitteeCode AS committee_code, "\
            "Committees.committeename AS committee_name "\
            "FROM Committees "\
            "WHERE Committees.CommitteeCode LIKE '{}%' "\
            "AND DATALENGTH(Committees.CommitteeEmailAddress) > 0"\
            .format(chamber_code)

        self.db_cursor.execute(query)

        committees = {}
        for row in self.db_cursor.fetchall():
            # There is technically a potential for duplicated committee
            # records to cause issues here. Haven't decided how to
            # handle this yet, so we're throwing an exception instead.
            if row['committee_code'] not in committees.keys():
                committee = Committee(chamber, row['committee_name'])
                committee_url = 'http://www.gencourt.state.nh.us/house/'\
                    'committees/committeedetails.aspx?code={}'\
                    .format(row['committee_code'])
                committee.add_source(committee_url)
                committees[row['committee_code']] = committee
            else:
                raise ValueError('{} committee is already present.'.format(
                    row['committee_name']))

        return committees

    def _parse_committee_members(self, committees):
        """Queries and parses the members for a given dict of committees."""
        # Adopting the following method of parsing committee members to
        # reduce querying. Grabs a list of members for all committees
        # given instead of querying for each committee individually.
        query = "SELECT "\
            "CommitteeMembers.CommitteeCode AS committee_code, "\
            "CommitteeMembers.comments AS comment, "\
            "Legislators.LastName AS last_name, "\
            "Legislators.FirstName AS first_name, "\
            "Legislators.MiddleName AS middle_name "\
            "FROM CommitteeMembers "\
            "LEFT OUTER JOIN Legislators "\
            "ON CommitteeMembers.EmployeeNumber = Legislators.Employeeno "\
            "WHERE CommitteeMembers.CommitteeCode IN ('{}') "\
            "AND CommitteeMembers.ActiveMember = 1 "\
            "ORDER BY CommitteeCode ASC, SequenceNumber ASC"\
            .format('\', \''.join(committees))

        self.db_cursor.execute(query)

        for row in self.db_cursor.fetchall():
            committee = committees[row['committee_code']]
            member_name = '{} {} {}'.format(row['first_name'],
                row['middle_name'], row['last_name'])
            member_name = re.sub(r'[\s]{2,}', ' ', member_name)

            if row['comment'] in ('Chairman', 'V Chairman'):
                member_role = 'chair'
            else:
                member_role = 'member'

            committee.add_member(member_name, member_role)

        return committees

    def scrape(self, chamber, term):
        self.db_cursor = db_cursor()

        committees = self._parse_committee_members(
            self._parse_committees(chamber))

        for committee_code, committee in committees.iteritems():
            self.save_committee(committee)
