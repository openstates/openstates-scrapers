from spatula import JsonPage, URL
from openstates.models import ScrapeCommittee
import json
import re

class CommitteeList(JsonPage):
    def process_page(self):
        com_membership = json.loads(self.data[1][0]['CommitteeMembership'])
        new_com_list = []
        for com in self.data[0]:
            name = com['Code_Description']
            if com['Code_House'] == 'S':
                chamber = 'upper'
            elif com['Code_House'] == 'A':
                chamber = 'lower'
            else:
                chamber = 'legislature'

            #TODO: Check classification and parent
            new_com = ScrapeCommittee(name = name, chamber=chamber)

            try:
                members = com_membership['Committees'][com['Comm_Status']]
            except KeyError:
                members = []
            for member in members:
                name = member['FullName']
                name_regex = re.compile("(.*?), +(.*)")
                name_match = name_regex.match(name)
                new_name = " ".join([name_match.group(2), name_match.group(1)])
                role = member['Position']
                if role != "":
                    new_com.add_member(name = new_name, role = role)
                else:
                    new_com.add_member(name = new_name)
            
            new_com.add_source(str(self.source))
            new_com_list.append(new_com)

        return new_com_list

class JointCommitteeList(CommitteeList):
    source = "https://www.njleg.state.nj.us/api/legislatorData/committeeInfo/joint-committees"

class SenateCommitteeList(CommitteeList):
    source = "https://www.njleg.state.nj.us/api/legislatorData/committeeInfo/senate-committees"

class AssemblyCommitteeList(CommitteeList):
    source = "https://www.njleg.state.nj.us/api/legislatorData/committeeInfo/assembly-committees"

class OtherCommitteeList(CommitteeList):
    source = "https://www.njleg.state.nj.us/api/legislatorData/committeeInfo/other-committees"
