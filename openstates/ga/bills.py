from billy.scrape.bills import BillScraper, Bill
from .util import get_client, get_url

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


class GABillScraper(BillScraper):
    jurisdiction = 'ga'
    lservice = get_client("Legislation").service
    mservice = get_client("Members").service
    lsource = get_url("Legislation")
    msource = get_url("Members")

    def get_member(self, member_id):
        if member_id in member_cache:
            return member_cache[member_id]
        mem = self.mservice.GetMember(member_id)
        member_cache[member_id] = mem
        return mem

    def scrape(self, session, chambers):
        sid = self.metadata['session_details'][session]['_guid']
        legislation = self.lservice.GetLegislationForSession(
            sid
        )['LegislationIndex']
        for leg in legislation:
            lid = leg['Id']
            instrument = self.lservice.GetLegislationDetail(lid)

            guid = instrument['Id']

            bill_type = instrument['DocumentType']
            chamber = {
                "H": "lower",
                "S": "upper",
                "J": "joint"
            }[bill_type[0]]  # XXX: This is a bit of a hack.

            bill_id = "%s %s" % (
                bill_type,
                instrument['Number'],
            )
            if instrument['Suffix']:
                bill_id += instrument['Suffix']

            title = instrument['Caption']
            description = instrument['Summary']

            bill = Bill(
                session,
                chamber,
                bill_id,
                title,
                description=description,
                _guid=guid
            )

            sponsors = instrument['Authors']['Sponsorship']
            if 'Sponsors' in instrument:
                sponsors += instrument['Sponsors']['Sponsorship']

            sponsors = [
                (x['Type'], self.get_member(x['MemberId'])) for x in sponsors
            ]

            for typ, sponsor in sponsors:
                name = "{First} {Last}".format(**dict(sponsor['Name']))
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

            bill.add_source(self.msource)
            bill.add_source(self.lsource)
            self.save_bill(bill)
