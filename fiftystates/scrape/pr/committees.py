import lxml.html
import datetime as dt
from fiftystates.scrape import NoDataForPeriod

from fiftystates.scrape.committees import CommitteeScraper, Committee

class PRComitteeScraper(CommitteeScraper):
    state = 'pr'
    
    def scrape(self, chamber, term):
        # Data available for this year only
        if int(year) != dt.date.today().year:
            raise NoDataForPeriod(term)

        if chamber == "upper":
            self.scrape_senate()
        elif chamber == "lower":
            self.scrape_house()
    
    def scrape_senate(self):
        permanent_commisions = 'http://senadopr.us/Pages/ComisionesPermanentes.aspx'
        special_commisions = 'http://senadopr.us/Pages/ComisionesEspeciales.aspx'
        joint_commisions = 'http://senadopr.us/Pages/ComisionesConjuntas.aspx'
        
    
    def scrape_house(self):
        permanent_commisions = 'http://www.camaraderepresentantes.org/comisiones.asp'
        joint_commisions = 'http://www.camaraderepresentantes.org/comisiones3.asp'