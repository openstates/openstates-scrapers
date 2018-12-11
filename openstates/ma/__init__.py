import re

import requests
import lxml.html
from pupa.scrape import Jurisdiction, Organization

# from .people import MAPersonScraper
# from .committees import MACommitteeScraper
from .bills import MABillScraper


class Massachusetts(Jurisdiction):
    division_id = "ocd-division/country:us/state:ma"
    classification = "government"
    name = "Massachusetts"
    url = "http://mass.gov"
    scrapers = {
        # 'people': MAPersonScraper,
        # 'committees': MACommitteeScraper,
        'bills': MABillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "186th",
            "classification": "primary",
            "identifier": "186th",
            "name": "186th Legislature (2009-2010)"
        },
        {
            "_scraped_name": "187th",
            "classification": "primary",
            "identifier": "187th",
            "name": "187th Legislature (2011-2012)"
        },
        {
            "_scraped_name": "188th",
            "classification": "primary",
            "identifier": "188th",
            "name": "188th Legislature (2013-2014)"
        },
        {
            "_scraped_name": "189th",
            "classification": "primary",
            "identifier": "189th",
            "name": "189th Legislature (2015-2016)"
        },
        {
            "_scraped_name": "190th",
            "classification": "primary",
            "identifier": "190th",
            "name": "190th Legislature (2017-2018)",
            'start_date': '2017-01-04',
            'end_date': '2017-11-15',
        }
    ]
    ignored_scraped_sessions = []

    def get_organizations(self):
        legislature_name = "Massachusetts General Court"
        lower_title = "Senator"
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        lower_divs = [
            ("Tenth Bristol", "ocd-division/country:us/state:ma/sldl:10th_bristol"),
            ("Tenth Essex", "ocd-division/country:us/state:ma/sldl:10th_essex"),
            ("Tenth Hampden", "ocd-division/country:us/state:ma/sldl:10th_hampden"),
            ("Tenth Middlesex", "ocd-division/country:us/state:ma/sldl:10th_middlesex"),
            ("Tenth Norfolk", "ocd-division/country:us/state:ma/sldl:10th_norfolk"),
            ("Tenth Plymouth", "ocd-division/country:us/state:ma/sldl:10th_plymouth"),
            ("Tenth Suffolk", "ocd-division/country:us/state:ma/sldl:10th_suffolk"),
            ("Tenth Worcester", "ocd-division/country:us/state:ma/sldl:10th_worcester"),
            ("Eleventh Bristol", "ocd-division/country:us/state:ma/sldl:11th_bristol"),
            ("Eleventh Essex", "ocd-division/country:us/state:ma/sldl:11th_essex"),
            ("Eleventh Hampden", "ocd-division/country:us/state:ma/sldl:11th_hampden"),
            ("Eleventh Middlesex", "ocd-division/country:us/state:ma/sldl:11th_middlesex"),
            ("Eleventh Norfolk", "ocd-division/country:us/state:ma/sldl:11th_norfolk"),
            ("Eleventh Plymouth", "ocd-division/country:us/state:ma/sldl:11th_plymouth"),
            ("Eleventh Suffolk", "ocd-division/country:us/state:ma/sldl:11th_suffolk"),
            ("Eleventh Worcester", "ocd-division/country:us/state:ma/sldl:11th_worcester"),
            ("Twelfth Bristol", "ocd-division/country:us/state:ma/sldl:12th_bristol"),
            ("Twelfth Essex", "ocd-division/country:us/state:ma/sldl:12th_essex"),
            ("Twelfth Hampden", "ocd-division/country:us/state:ma/sldl:12th_hampden"),
            ("Twelfth Middlesex", "ocd-division/country:us/state:ma/sldl:12th_middlesex"),
            ("Twelfth Norfolk", "ocd-division/country:us/state:ma/sldl:12th_norfolk"),
            ("Twelfth Plymouth", "ocd-division/country:us/state:ma/sldl:12th_plymouth"),
            ("Twelfth Suffolk", "ocd-division/country:us/state:ma/sldl:12th_suffolk"),
            ("Twelfth Worcester", "ocd-division/country:us/state:ma/sldl:12th_worcester"),
            ("Thirteenth Bristol", "ocd-division/country:us/state:ma/sldl:13th_bristol"),
            ("Thirteenth Essex", "ocd-division/country:us/state:ma/sldl:13th_essex"),
            ("Thirteenth Middlesex", "ocd-division/country:us/state:ma/sldl:13th_middlesex"),
            ("Thirteenth Norfolk", "ocd-division/country:us/state:ma/sldl:13th_norfolk"),
            ("Thirteenth Suffolk", "ocd-division/country:us/state:ma/sldl:13th_suffolk"),
            ("Thirteenth Worcester", "ocd-division/country:us/state:ma/sldl:13th_worcester"),
            ("Fourteenth Bristol", "ocd-division/country:us/state:ma/sldl:14th_bristol"),
            ("Fourteenth Essex", "ocd-division/country:us/state:ma/sldl:14th_essex"),
            ("Fourteenth Middlesex", "ocd-division/country:us/state:ma/sldl:14th_middlesex"),
            ("Fourteenth Norfolk", "ocd-division/country:us/state:ma/sldl:14th_norfolk"),
            ("Fourteenth Suffolk", "ocd-division/country:us/state:ma/sldl:14th_suffolk"),
            ("Fourteenth Worcester", "ocd-division/country:us/state:ma/sldl:14th_worcester"),
            ("Fifteenth Essex", "ocd-division/country:us/state:ma/sldl:15th_essex"),
            ("Fifteenth Middlesex", "ocd-division/country:us/state:ma/sldl:15th_middlesex"),
            ("Fifteenth Norfolk", "ocd-division/country:us/state:ma/sldl:15th_norfolk"),
            ("Fifteenth Suffolk", "ocd-division/country:us/state:ma/sldl:15th_suffolk"),
            ("Fifteenth Worcester", "ocd-division/country:us/state:ma/sldl:15th_worcester"),
            ("Sixteenth Essex", "ocd-division/country:us/state:ma/sldl:16th_essex"),
            ("Sixteenth Middlesex", "ocd-division/country:us/state:ma/sldl:16th_middlesex"),
            ("Sixteenth Suffolk", "ocd-division/country:us/state:ma/sldl:16th_suffolk"),
            ("Sixteenth Worcester", "ocd-division/country:us/state:ma/sldl:16th_worcester"),
            ("Seventeenth Essex", "ocd-division/country:us/state:ma/sldl:17th_essex"),
            ("Seventeenth Middlesex", "ocd-division/country:us/state:ma/sldl:17th_middlesex"),
            ("Seventeenth Suffolk", "ocd-division/country:us/state:ma/sldl:17th_suffolk"),
            ("Seventeenth Worcester", "ocd-division/country:us/state:ma/sldl:17th_worcester"),
            ("Eighteenth Essex", "ocd-division/country:us/state:ma/sldl:18th_essex"),
            ("Eighteenth Middlesex", "ocd-division/country:us/state:ma/sldl:18th_middlesex"),
            ("Eighteenth Suffolk", "ocd-division/country:us/state:ma/sldl:18th_suffolk"),
            ("Eighteenth Worcester", "ocd-division/country:us/state:ma/sldl:18th_worcester"),
            ("Nineteenth Middlesex", "ocd-division/country:us/state:ma/sldl:19th_middlesex"),
            ("Nineteenth Suffolk", "ocd-division/country:us/state:ma/sldl:19th_suffolk"),
            ("First Barnstable", "ocd-division/country:us/state:ma/sldl:1st_barnstable"),
            ("First Berkshire", "ocd-division/country:us/state:ma/sldl:1st_berkshire"),
            ("First Bristol", "ocd-division/country:us/state:ma/sldl:1st_bristol"),
            ("First Essex", "ocd-division/country:us/state:ma/sldl:1st_essex"),
            ("First Franklin", "ocd-division/country:us/state:ma/sldl:1st_franklin"),
            ("First Hampden", "ocd-division/country:us/state:ma/sldl:1st_hampden"),
            ("First Hampshire", "ocd-division/country:us/state:ma/sldl:1st_hampshire"),
            ("First Middlesex", "ocd-division/country:us/state:ma/sldl:1st_middlesex"),
            ("First Norfolk", "ocd-division/country:us/state:ma/sldl:1st_norfolk"),
            ("First Plymouth", "ocd-division/country:us/state:ma/sldl:1st_plymouth"),
            ("First Suffolk", "ocd-division/country:us/state:ma/sldl:1st_suffolk"),
            ("First Worcester", "ocd-division/country:us/state:ma/sldl:1st_worcester"),
            ("Twentieth Middlesex", "ocd-division/country:us/state:ma/sldl:20th_middlesex"),
            ("Twenty-First Middlesex", "ocd-division/country:us/state:ma/sldl:21st_middlesex"),
            ("Twenty-Second Middlesex", "ocd-division/country:us/state:ma/sldl:22nd_middlesex"),
            ("Twenty-Third Middlesex", "ocd-division/country:us/state:ma/sldl:23rd_middlesex"),
            ("Twenty-Fourth Middlesex", "ocd-division/country:us/state:ma/sldl:24th_middlesex"),
            ("Twenty-Fifth Middlesex", "ocd-division/country:us/state:ma/sldl:25th_middlesex"),
            ("Twenty-Sixth Middlesex", "ocd-division/country:us/state:ma/sldl:26th_middlesex"),
            ("Twenty-Seventh Middlesex", "ocd-division/country:us/state:ma/sldl:27th_middlesex"),
            ("Twenty-Eighth Middlesex", "ocd-division/country:us/state:ma/sldl:28th_middlesex"),
            ("Twenty-Ninth Middlesex", "ocd-division/country:us/state:ma/sldl:29th_middlesex"),
            ("Second Barnstable", "ocd-division/country:us/state:ma/sldl:2nd_barnstable"),
            ("Second Berkshire", "ocd-division/country:us/state:ma/sldl:2nd_berkshire"),
            ("Second Bristol", "ocd-division/country:us/state:ma/sldl:2nd_bristol"),
            ("Second Essex", "ocd-division/country:us/state:ma/sldl:2nd_essex"),
            ("Second Franklin", "ocd-division/country:us/state:ma/sldl:2nd_franklin"),
            ("Second Hampden", "ocd-division/country:us/state:ma/sldl:2nd_hampden"),
            ("Second Hampshire", "ocd-division/country:us/state:ma/sldl:2nd_hampshire"),
            ("Second Middlesex", "ocd-division/country:us/state:ma/sldl:2nd_middlesex"),
            ("Second Norfolk", "ocd-division/country:us/state:ma/sldl:2nd_norfolk"),
            ("Second Plymouth", "ocd-division/country:us/state:ma/sldl:2nd_plymouth"),
            ("Second Suffolk", "ocd-division/country:us/state:ma/sldl:2nd_suffolk"),
            ("Second Worcester", "ocd-division/country:us/state:ma/sldl:2nd_worcester"),
            ("Thirtieth Middlesex", "ocd-division/country:us/state:ma/sldl:30th_middlesex"),
            ("Thirty-First Middlesex", "ocd-division/country:us/state:ma/sldl:31st_middlesex"),
            ("Thirty-Second Middlesex", "ocd-division/country:us/state:ma/sldl:32nd_middlesex"),
            ("Thirty-Third Middlesex", "ocd-division/country:us/state:ma/sldl:33rd_middlesex"),
            ("Thirty-Fourth Middlesex", "ocd-division/country:us/state:ma/sldl:34th_middlesex"),
            ("Thirty-Fifth Middlesex", "ocd-division/country:us/state:ma/sldl:35th_middlesex"),
            ("Thirty-Sixth Middlesex", "ocd-division/country:us/state:ma/sldl:36th_middlesex"),
            ("Thirty-Seventh Middlesex", "ocd-division/country:us/state:ma/sldl:37th_middlesex"),
            ("Third Barnstable", "ocd-division/country:us/state:ma/sldl:3rd_barnstable"),
            ("Third Berkshire", "ocd-division/country:us/state:ma/sldl:3rd_berkshire"),
            ("Third Bristol", "ocd-division/country:us/state:ma/sldl:3rd_bristol"),
            ("Third Essex", "ocd-division/country:us/state:ma/sldl:3rd_essex"),
            ("Third Hampden", "ocd-division/country:us/state:ma/sldl:3rd_hampden"),
            ("Third Hampshire", "ocd-division/country:us/state:ma/sldl:3rd_hampshire"),
            ("Third Middlesex", "ocd-division/country:us/state:ma/sldl:3rd_middlesex"),
            ("Third Norfolk", "ocd-division/country:us/state:ma/sldl:3rd_norfolk"),
            ("Third Plymouth", "ocd-division/country:us/state:ma/sldl:3rd_plymouth"),
            ("Third Suffolk", "ocd-division/country:us/state:ma/sldl:3rd_suffolk"),
            ("Third Worcester", "ocd-division/country:us/state:ma/sldl:3rd_worcester"),
            ("Fourth Barnstable", "ocd-division/country:us/state:ma/sldl:4th_barnstable"),
            ("Fourth Berkshire", "ocd-division/country:us/state:ma/sldl:4th_berkshire"),
            ("Fourth Bristol", "ocd-division/country:us/state:ma/sldl:4th_bristol"),
            ("Fourth Essex", "ocd-division/country:us/state:ma/sldl:4th_essex"),
            ("Fourth Hampden", "ocd-division/country:us/state:ma/sldl:4th_hampden"),
            ("Fourth Middlesex", "ocd-division/country:us/state:ma/sldl:4th_middlesex"),
            ("Fourth Norfolk", "ocd-division/country:us/state:ma/sldl:4th_norfolk"),
            ("Fourth Plymouth", "ocd-division/country:us/state:ma/sldl:4th_plymouth"),
            ("Fourth Suffolk", "ocd-division/country:us/state:ma/sldl:4th_suffolk"),
            ("Fourth Worcester", "ocd-division/country:us/state:ma/sldl:4th_worcester"),
            ("Fifth Barnstable", "ocd-division/country:us/state:ma/sldl:5th_barnstable"),
            ("Fifth Bristol", "ocd-division/country:us/state:ma/sldl:5th_bristol"),
            ("Fifth Essex", "ocd-division/country:us/state:ma/sldl:5th_essex"),
            ("Fifth Hampden", "ocd-division/country:us/state:ma/sldl:5th_hampden"),
            ("Fifth Middlesex", "ocd-division/country:us/state:ma/sldl:5th_middlesex"),
            ("Fifth Norfolk", "ocd-division/country:us/state:ma/sldl:5th_norfolk"),
            ("Fifth Plymouth", "ocd-division/country:us/state:ma/sldl:5th_plymouth"),
            ("Fifth Suffolk", "ocd-division/country:us/state:ma/sldl:5th_suffolk"),
            ("Fifth Worcester", "ocd-division/country:us/state:ma/sldl:5th_worcester"),
            ("Sixth Bristol", "ocd-division/country:us/state:ma/sldl:6th_bristol"),
            ("Sixth Essex", "ocd-division/country:us/state:ma/sldl:6th_essex"),
            ("Sixth Hampden", "ocd-division/country:us/state:ma/sldl:6th_hampden"),
            ("Sixth Middlesex", "ocd-division/country:us/state:ma/sldl:6th_middlesex"),
            ("Sixth Norfolk", "ocd-division/country:us/state:ma/sldl:6th_norfolk"),
            ("Sixth Plymouth", "ocd-division/country:us/state:ma/sldl:6th_plymouth"),
            ("Sixth Suffolk", "ocd-division/country:us/state:ma/sldl:6th_suffolk"),
            ("Sixth Worcester", "ocd-division/country:us/state:ma/sldl:6th_worcester"),
            ("Seventh Bristol", "ocd-division/country:us/state:ma/sldl:7th_bristol"),
            ("Seventh Essex", "ocd-division/country:us/state:ma/sldl:7th_essex"),
            ("Seventh Hampden", "ocd-division/country:us/state:ma/sldl:7th_hampden"),
            ("Seventh Middlesex", "ocd-division/country:us/state:ma/sldl:7th_middlesex"),
            ("Seventh Norfolk", "ocd-division/country:us/state:ma/sldl:7th_norfolk"),
            ("Seventh Plymouth", "ocd-division/country:us/state:ma/sldl:7th_plymouth"),
            ("Seventh Suffolk", "ocd-division/country:us/state:ma/sldl:7th_suffolk"),
            ("Seventh Worcester", "ocd-division/country:us/state:ma/sldl:7th_worcester"),
            ("Eighth Bristol", "ocd-division/country:us/state:ma/sldl:8th_bristol"),
            ("Eighth Essex", "ocd-division/country:us/state:ma/sldl:8th_essex"),
            ("Eighth Hampden", "ocd-division/country:us/state:ma/sldl:8th_hampden"),
            ("Eighth Middlesex", "ocd-division/country:us/state:ma/sldl:8th_middlesex"),
            ("Eighth Norfolk", "ocd-division/country:us/state:ma/sldl:8th_norfolk"),
            ("Eighth Plymouth", "ocd-division/country:us/state:ma/sldl:8th_plymouth"),
            ("Eighth Suffolk", "ocd-division/country:us/state:ma/sldl:8th_suffolk"),
            ("Eighth Worcester", "ocd-division/country:us/state:ma/sldl:8th_worcester"),
            ("Ninth Bristol", "ocd-division/country:us/state:ma/sldl:9th_bristol"),
            ("Ninth Essex", "ocd-division/country:us/state:ma/sldl:9th_essex"),
            ("Ninth Hampden", "ocd-division/country:us/state:ma/sldl:9th_hampden"),
            ("Ninth Middlesex", "ocd-division/country:us/state:ma/sldl:9th_middlesex"),
            ("Ninth Norfolk", "ocd-division/country:us/state:ma/sldl:9th_norfolk"),
            ("Ninth Plymouth", "ocd-division/country:us/state:ma/sldl:9th_plymouth"),
            ("Ninth Suffolk", "ocd-division/country:us/state:ma/sldl:9th_suffolk"),
            ("Ninth Worcester", "ocd-division/country:us/state:ma/sldl:9th_worcester"),
            ("Barnstable, Dukes and Nantucket",
             "ocd-division/country:us/state:ma/sldl:barnstable_dukes_and_nantucket"),
        ]

        upper_divs = [
            ("Berkshire, Hampshire, Franklin and Hampden",
             "ocd-division/country:us/state:ma/sldu:berkshire_hampshire_franklin_and_hampden"),
            ("Bristol and Norfolk", "ocd-division/country:us/state:ma/sldu:bristol_and_norfolk"),
            ("Cape and Islands", "ocd-division/country:us/state:ma/sldu:cape_and_islands"),
            ("Fifth Middlesex", "ocd-division/country:us/state:ma/sldu:5th_middlesex"),
            ("First Bristol and Plymouth",
             "ocd-division/country:us/state:ma/sldu:1st_bristol_and_plymouth"),
            ("First Essex", "ocd-division/country:us/state:ma/sldu:1st_essex"),
            ("First Essex and Middlesex",
             "ocd-division/country:us/state:ma/sldu:1st_essex_and_middlesex"),
            ("First Hampden and Hampshire",
             "ocd-division/country:us/state:ma/sldu:1st_hampden_and_hampshire"),
            ("First Middlesex", "ocd-division/country:us/state:ma/sldu:1st_middlesex"),
            ("First Middlesex and Norfolk",
             "ocd-division/country:us/state:ma/sldu:1st_middlesex_and_norfolk"),
            ("First Plymouth and Bristol",
             "ocd-division/country:us/state:ma/sldu:1st_plymouth_and_bristol"),
            ("First Suffolk", "ocd-division/country:us/state:ma/sldu:1st_suffolk"),
            ("First Suffolk and Middlesex",
             "ocd-division/country:us/state:ma/sldu:1st_suffolk_and_middlesex"),
            ("First Worcester", "ocd-division/country:us/state:ma/sldu:1st_worcester"),
            ("Fourth Middlesex", "ocd-division/country:us/state:ma/sldu:4th_middlesex"),
            ("Hampden", "ocd-division/country:us/state:ma/sldu:hampden"),
            ("Hampshire, Franklin and Worcester",
             "ocd-division/country:us/state:ma/sldu:hampshire_franklin_and_worcester"),
            ("Middlesex and Suffolk",
             "ocd-division/country:us/state:ma/sldu:middlesex_and_suffolk"),
            ("Middlesex and Worcester",
             "ocd-division/country:us/state:ma/sldu:middlesex_and_worcester"),
            ("Norfolk, Bristol and Middlesex",
             "ocd-division/country:us/state:ma/sldu:norfolk_bristol_and_middlesex"),
            ("Norfolk, Bristol and Plymouth",
             "ocd-division/country:us/state:ma/sldu:norfolk_bristol_and_plymouth"),
            ("Norfolk and Plymouth", "ocd-division/country:us/state:ma/sldu:norfolk_and_plymouth"),
            ("Norfolk and Suffolk", "ocd-division/country:us/state:ma/sldu:norfolk_and_suffolk"),
            ("Plymouth and Barnstable",
             "ocd-division/country:us/state:ma/sldu:plymouth_and_barnstable"),
            ("Plymouth and Norfolk", "ocd-division/country:us/state:ma/sldu:plymouth_and_norfolk"),
            ("Second Bristol and Plymouth",
             "ocd-division/country:us/state:ma/sldu:2nd_bristol_and_plymouth"),
            ("Second Essex", "ocd-division/country:us/state:ma/sldu:2nd_essex"),
            ("Second Essex and Middlesex",
             "ocd-division/country:us/state:ma/sldu:2nd_essex_and_middlesex"),
            ("Second Hampden and Hampshire",
             "ocd-division/country:us/state:ma/sldu:2nd_hampden_and_hampshire"),
            ("Second Middlesex", "ocd-division/country:us/state:ma/sldu:2nd_middlesex"),
            ("Second Middlesex and Norfolk",
             "ocd-division/country:us/state:ma/sldu:2nd_middlesex_and_norfolk"),
            ("Second Plymouth and Bristol",
             "ocd-division/country:us/state:ma/sldu:2nd_plymouth_and_bristol"),
            ("Second Suffolk", "ocd-division/country:us/state:ma/sldu:2nd_suffolk"),
            ("Second Suffolk and Middlesex",
             "ocd-division/country:us/state:ma/sldu:2nd_suffolk_and_middlesex"),
            ("Second Worcester", "ocd-division/country:us/state:ma/sldu:2nd_worcester"),
            ("Third Essex", "ocd-division/country:us/state:ma/sldu:3rd_essex"),
            ("Third Middlesex", "ocd-division/country:us/state:ma/sldu:3rd_middlesex"),
            ("Worcester, Hampden, Hampshire and Middlesex",
             "ocd-division/country:us/state:ma/sldu:worcester_hampden_hampshire_and_middlesex"),
            ("Worcester and Middlesex",
             "ocd-division/country:us/state:ma/sldu:worcester_and_middlesex"),
            ("Worcester and Norfolk",
             "ocd-division/country:us/state:ma/sldu:worcester_and_norfolk"),
        ]

        for name, division_id in lower_divs:
            lower.add_post(label=name, role=lower_title, division_id=division_id)
        for name, division_id in upper_divs:
            upper.add_post(label=name, role=upper_title, division_id=division_id)

        yield Organization(name='Office of the Governor', classification='executive')
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        doc = lxml.html.fromstring(requests.get(
            'https://malegislature.gov/Bills/Search').text)
        sessions = doc.xpath("//div[@data-refinername='lawsgeneralcourt']/div/label/text()")

        # Remove all text between parens, like (Current) (7364)
        return list(
            filter(None, [re.sub(r'\([^)]*\)', "", session).strip() for session in sessions]))
