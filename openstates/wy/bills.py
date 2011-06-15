from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill 

import lxml.html
import re

class WYBillScraper(BillScraper):
    """
    2006-Present: 
        Bills - http://legisweb.state.wy.us/2010/billindex/BillCrossRef.aspx?type=ALL
        Votes - http://legisweb.state.wy.us/2011/SessionVotes/VoteList.aspx?ID=HB0092
        Vote Detail - http://legisweb.state.wy.us/2011/SessionVotes/VoteDetail.aspx?ID=5142
        Digest - http://legisweb.state.wy.us/2011/Digest/HB0092.htm

        Most actions only available in digest (very hard to scrape).


    2003 - 2005: 
        http://legisweb.state.wy.us/2005/HBIndex.HTM
        http://legisweb.state.wy.us/2005/SFIndex.HTM

        Doesn't list sponsors in index, only in digest; votes only available in the bill digest (boo). Skip these years for now.
    """

    state = "wy"

    def scrape(self, chamber, session):
        pass
