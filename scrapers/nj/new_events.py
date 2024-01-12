# import json
import pytz
from openstates.scrape import Scraper


class NJEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    # def scrape(self, session=None):
    # year_abr = ((int(session) - 209) * 2) + 2000
    # url = f"https://www.njleg.state.nj.us/api/billSearch/allBills/{session}"
    #
    # json_data = self.get(url).text
    # event_list = json.loads(json_data)[0]

    # for item in event_list:
    # name = item["Code_Description"]
    # start_date = item["Agenda_Time_Start"]
    # end_date = item["Agenda_Time_End"]
    # status = item["ScheduleStatus"]
    # location = item["Agenda_Location"]
    # description = item["AgendaComment"]
