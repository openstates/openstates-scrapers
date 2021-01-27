import re
import datetime
import time
import pytz
import lxml.html
import requests
import pprint
from openstates.scrape import Scraper, Event


class OKEventScraper(Scraper):
    _tz = pytz.timezone("CST6CDT")
    session = requests.Session()

    def scrape(self, chamber=None):
        
        # we need to GET the page once to set up the ASP.net vars
        # then POST to it to set it to monthly
        url = "https://www.okhouse.gov/Committees/MeetingNotices.aspx"

        params = {
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$cbMonthly',
            'ctl00$ScriptManager1': 'ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$cbMonthly',
            'ctl00_FormDecorator1_ClientState': '',
            'ctl00_RadToolTipManager1_ClientState': '',
            'ctl00_mainNav_ClientState': '',
            'ctl00$ContentPlaceHolder1$cbToday': 'on',
            'ctl00$ContentPlaceHolder1$cbMonthly': 'on',
            'ctl00_ContentPlaceHolder1_dgrdNotices_ClientState': '',
            '__ASYNCPOST': 'true',
            'RadAJAXControlID': 'ctl00_ContentPlaceHolder1_RadAjaxPanel1',
        }

        page = self.get(url).content
        page = lxml.html.fromstring(page)

        html = self.asp_post(url, page, params)
        print(html)

        page = lxml.html.fromstring(html)

        for row in page.xpath('//tr[contains(@id,"_dgrdNotices_")]'):
            print(row.text_content())
        
        yield {}

    def asp_post(self, url, page, params):
        page = self.session.get(url)
        page = lxml.html.fromstring(page.content)
        (viewstate,) = page.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator,) = page.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')
        (eventvalidation,) = page.xpath('//input[@id="__EVENTVALIDATION"]/@value')
        (scriptmanager,) = page.xpath('//input[@id="ctl00_ScriptManager1_TSM"]/@value')

        headers = {
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
            'x-microsoftajax': 'Delta=true',
            'referer': 'https://www.okhouse.gov/Committees/MeetingNotices.aspx',
            'origin': 'https://www.okhouse.gov',
        }

        form = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
        }

        form = {**form, **params}


        pprint.pprint(form)
        response = self.session.post(url, form, headers=headers).content
        return response
