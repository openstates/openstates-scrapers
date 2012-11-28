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


class GABillScraper(BillScraper):
    state = 'ga'
    lservice = get_client("Legislation").service
    mservice = get_client("Members").service
    lsource = get_url("Legislation")
    msource = get_url("Members")

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

            bill = Bill(
                session,
                chamber,
                bill_id,
                title,
                description=description,
                _guid=guid
            )

            sponsors = [
                self.mservice.GetMember(x['MemberId']) for x in
                    instrument['Authors']['Sponsorship']
            ]
            print bill
            raise Exception
