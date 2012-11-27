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
    mbills = get_client("Legislation").service
    msource = get_url("Legislation")

    def scrape(self, session, chambers):
        sid = self.metadata['session_details'][session]['_guid']
        legislation = self.mbills.GetLegislationForSession(
            sid
        )['LegislationIndex']
        for leg in legislation:
            lid = leg['Id']
            instrument = self.mbills.GetLegislationDetail(lid)
            print instrument
