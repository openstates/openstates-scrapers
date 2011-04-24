from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html
import urllib
import re

class WYLegislatorScraper(LegislatorScraper):
    state = 'wy'
    url = "http://legisweb.state.wy.us/LegislatorSummary/LegislatorList.aspx?strHouse=%s&strStatus=N"
    parties = {"R":"Republican", "D":"Democratic"}
    
    def scrape(self, chamber, term):
        if chamber == 'lower':
            chamber_type = 'H'
        else:
            chamber_type = 'S'
        
#Build lxml tree for basic information
        doc = lxml.html.parse(url%chamber_type)
        tbl = doc.xpath('//div/table/tr') 

#Parse page to obtain email id and photo_url
        text = urllib.urlopen(url%chamber_type).read()
        url_entry = re.findall("(<tr valign[.\s\w\d=\"\ \:\;\>\<\ \-\,\?\/\@]+</tr>)",text)[0].split('</tr>')[:30]

        i = 0

        for row in tbl[3:].getchildren():
            row = row.text_content().split()
            full_name = row[0])
            
            party = parties[row[2]]
            district = row[3]
            
            first_name = row[0][0]
            last_name = row[0][1]
            full_name = first_name + ' ' + last_name

            legid = re.findall("LegID\=([\d]+)",url_entry[i])[0]
            member_url = "http://legisweb.state.wy.us/LegislatorSummary/LegDetail.aspx?LegID="+legid
            member_page = lxml.html.parse(member_url)
            photo_url = "http://legisweb.state.wy.us/LegislatorSummary/" + member_page.xpath("//img[@id='ctl00_cphContent_LegPhoto']/@src")

            legmail = re.findall("Mailto:([.\@._@\d\w]+)\"",url_entry[i])[0]
            
            legislator = Legislator(term, chamber, district, full_name, first_name=first_name, last_name=last_name, party=party)

            legislator['photo_url'] = photo_url
            legislator['email'] = legmail
            
            legislator.add_source(url)
            self.save_legislator

