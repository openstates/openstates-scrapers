from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from collections import defaultdict
from .util import get_client, get_url, backoff

#         Methods (7):
#            GetLegislationDetail(xs:int LegislationId, )
#
#            GetLegislationDetailByDescription(ns2:DocumentType DocumentType,
#                                              xs:int Number, xs:int SessionId)
#
#            GetLegislationForSession(xs:int SessionId, )
#
#            GetLegislationRange(ns2:LegislationIndexRangeSet Range, )
#
#            GetLegislationRanges(xs:int SessionId,
#                           ns2:DocumentType DocumentType, xs:int RangeSize, )
#
#            GetLegislationSearchResultsPaged(ns2:LegislationSearchConstraints
#                                               Constraints, xs:int PageSize,
#                                               xs:int StartIndex, )
#            GetTitles()


member_cache = {}
SOURCE_URL = 'http://www.legis.ga.gov/Legislation/en-US/display/{session}/{bid}'


class GABillScraper(BillScraper):
    jurisdiction = 'ga'
    lservice = get_client('Legislation').service
    vservice = get_client('Votes').service
    mservice = get_client('Members').service
    lsource = get_url('Legislation')
    msource = get_url('Members')
    vsource = get_url('Votes')

    def get_member(self, member_id):
        if member_id in member_cache:
            return member_cache[member_id]

        mem = backoff(self.mservice.GetMember, member_id)
        member_cache[member_id] = mem
        return mem

    def scrape(self, session, chambers):
        bill_type_map = {
            'B': 'bill',
            'R': 'resolution',
            'JR': 'joint resolution',
            'CR': 'concurrent resolution',
        }

        chamber_map = {
            'H': 'lower',
            'S': 'upper',
            'J': 'joint',
            'E': 'other', # Effective date
        }

        action_code_map = {
            'HI': ['other'],
            'SI': ['other'],
            'HH': ['other'],
            'SH': ['other'],
            'HPF': ['bill:introduced'],
            'HDSAS': ['other'],
            'SPF': ['bill:introduced'],
            'HSR': ['bill:reading:2'],
            'SSR': ['bill:reading:2'],
            'HFR': ['bill:reading:1'],
            'SFR': ['bill:reading:1'],
            'HRECM': ['bill:withdrawn', 'committee:referred'],
            'SRECM': ['bill:withdrawn', 'committee:referred'],
            'SW&C': ['bill:withdrawn', 'committee:referred'],
            'HW&C': ['bill:withdrawn', 'committee:referred'],
            'HRA': ['bill:passed'],
            'SRA': ['bill:passed'],
            'HPA': ['bill:passed'],
            'HRECO': ['other'],
            'SPA': ['bill:passed'],
            'HTABL': ['other'],  # 'House Tabled' - what is this?
            'SDHAS': ['other'],
            'HCFR': ['committee:passed:favorable'],
            'SCFR': ['committee:passed:favorable'],
            'HRAR': ['committee:referred'],
            'SRAR': ['committee:referred'],
            'STR': ['bill:reading:3'],
            'SAHAS': ['other'],
            'SE': ['bill:passed'],
            'SR': ['committee:referred'],
            'HTRL': ['bill:reading:3', 'bill:failed'],
            'HTR': ['bill:reading:3'],
            'S3RLT': ['bill:reading:3', 'bill:failed'],
            'HASAS': ['other'],
            'S3RPP': ['other'],
            'STAB': ['other'],
            'SRECO': ['other'],
            'SAPPT': ['other'],
            'HCA': ['other'],
            'HNOM': ['other'],
            'HTT': ['other'],
            'STT': ['other'],
            'SRECP': ['other'],
            'SCRA': ['other'],
            'SNOM': ['other'],
            'S2R': ['bill:reading:2'],
            'H2R': ['bill:reading:2'],
            'SENG': ['bill:passed'],
            'HENG': ['bill:passed'],
            'HPOST': ['other'],
            'HCAP': ['other'],
            'SDSG': ['governor:signed'],
            'SSG': ['governor:received'],
            'Signed Gov': ['governor:signed'],
            'HDSG': ['governor:signed'],
            'HSG': ['governor:received'],
            'EFF': ['other'],
            'HRP': ['other'],
            'STH': ['other'],
            'HTS': ['other'],
        }

        sid = self.metadata['session_details'][session]['_guid']
        legislation = backoff(
            self.lservice.GetLegislationForSession,
            sid
        )['LegislationIndex']

        for leg in legislation:
            lid = leg['Id']
            instrument = backoff(self.lservice.GetLegislationDetail, lid)
            history = [x for x in instrument['StatusHistory'][0]]

            actions = reversed([{
                'code': x['Code'],
                'action': x['Description'],
                '_guid': x['Id'],
                'date': x['Date']
            } for x in history])

            guid = instrument['Id']

            # A little bit hacky.
            bill_prefix = instrument['DocumentType']
            bill_chamber = chamber_map[bill_prefix[0]]
            bill_type = bill_type_map[bill_prefix[1:]]

            bill_id = '%s %s' % (
                bill_prefix,
                instrument['Number'],
            )
            if instrument['Suffix']:
                bill_id += instrument['Suffix']

            title = instrument['Caption']
            description = instrument['Summary']

            if title is None:
                continue

            bill = Bill(session, bill_chamber, bill_id, title, type=bill_type,
                description=description, _guid=guid)

            if instrument['Votes']:
                for vote_ in instrument['Votes']:
                    _, vote_ = vote_
                    vote_ = backoff(self.vservice.GetVote, vote_[0]['VoteId'])

                    vote = Vote(
                        {'House': 'lower', 'Senate': 'upper'}[vote_['Branch']],
                        vote_['Date'],
                        vote_['Caption'] or 'Vote on Bill',
                        (vote_['Yeas'] > vote_['Nays']),
                        vote_['Yeas'],
                        vote_['Nays'],
                        (vote_['Excused'] + vote_['NotVoting']),
                        session=session,
                        bill_id=bill_id,
                        bill_chamber=bill_chamber)

                    vote.add_source(self.vsource)

                    methods = {'Yea': vote.yes, 'Nay': vote.no,}

                    for vdetail in vote_['Votes'][0]:
                        whom = vdetail['Member']
                        how = vdetail['MemberVoted']
                        try:
                            m = methods[how]
                        except KeyError:
                            m = vote.other
                        m(whom['Name'])

                    bill.add_vote(vote)

            ccommittees = defaultdict(list)
            committees = instrument['Committees']
            if committees:
                for committee in committees[0]:
                    ccommittees[{
                        'House': 'lower',
                        'Senate': 'upper',
                    }[committee['Type']]].append(committee['Name'])

            for action in actions:
                action_chamber = chamber_map[action['code'][0]]

                try:
                    action_types = action_code_map[action['code']]
                except KeyError:
                    error_msg = ('Code {code} for action {action} not '
                        'recognized.'.format(
                            code=action['code'],
                            action=action['action']))

                    self.logger.warning(error_msg)

                    action_types = ['other']

                committees = []
                if any(('committee' in x for x in action_types)):
                    committees = [str(x) for x in ccommittees.get(
                        action_chamber, [])]

                bill.add_action(action_chamber, action['action'],
                    action['date'], action_types, committees=committees,
                    _code=action['code'], _code_id=action['_guid'])

            sponsors = []
            if instrument['Authors']:
                sponsors = instrument['Authors']['Sponsorship']
                if 'Sponsors' in instrument and instrument['Sponsors']:
                    sponsors += instrument['Sponsors']['Sponsorship']

            sponsors = [
                (x['Type'], self.get_member(x['MemberId'])) for x in sponsors
            ]

            for typ, sponsor in sponsors:
                name = '{First} {Last}'.format(**dict(sponsor['Name']))
                bill.add_sponsor(
                    'primary' if 'Author' in typ else 'seconday',
                     name
                )

            for version in instrument['Versions']['DocumentDescription']:
                name, url, doc_id, version_id = [
                    version[x] for x in [
                        'Description',
                        'Url',
                        'Id',
                        'Version'
                    ]
                ]
                bill.add_version(
                    name,
                    url,
                    mimetype='application/pdf',
                    _internal_document_id=doc_id,
                    _version_id=version_id
                )

            versions = sorted(
                bill['versions'],
                key=lambda x: x['_internal_document_id']
            )
            bill['versions'] = versions

            bill.add_source(self.msource)
            bill.add_source(self.lsource)
            bill.add_source(SOURCE_URL.format(**{
                'session': session,
                'bid': guid,
            }))
            self.save_bill(bill)
