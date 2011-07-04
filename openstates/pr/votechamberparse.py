# coding= utf-8

import re
import datetime
import urlparse
import lxml.html
from lxml import etree

def parse_chamber():
    f = open('/tmp/{1F4D2323-1229-4EBA-BC06-F364AF97303F}.html','r')
    doc = lxml.html.fromstring(f.read())
    header = doc.xpath('/html/body/div/table[1]/tbody/tr[1]/td[2]')
    header_txt = header[0][0][0].text_content();
    assembly_number = header[0][0][1].text_content();
    bill_id = header[0][0][3].text_content().lstrip().rstrip();
    
    if u'Cámara de Representantes de Puerto Rico' == header_txt:
       bill_chamber = 'lower'
    else:
       bill_chamber = 'uknown: ' + header_txt
    #get session number, time this measure has been voted,day,date
    header2 = doc.xpath('/html/body/div/table[1]/tbody/tr[1]/td[3]')
    header2_txt = header2[0][0].text_content();
    match=re.search(r'(\d+/\d+/\d+)',header2_txt)
    #datetime.datetime.strptime("11/12/98","%m/%d/%y")
    date =  match.group(1)
    #split on <br>
    #print header2_txt
    #show legislator,party,yes,no,abstention,observations
    table = doc.xpath('/html/body/div/table[2]/tbody')
   
    #loop thru table and skip first one
    #print table[0].xpath('tr')[::-1];
    vote = None;
    for row in table[0].xpath('tr')[::-1]:
        tds = row.xpath('td')
        party = tds[1].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','');
        #yes
        yes_td =  tds[2].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','')
        #nays
        nays_td =  tds[3].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','')
        #absent
        abstent_td =  tds[4].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','')
        #if party == 'Total':
        if len(party) == 7:
            yes_count = int(yes_td)
            no_count =  int(nays_td)
            other_count =  int(abstent_td)
            #vote = Vote(bill_chamber, date, motion, True, yes_count, no_count, other_count)
 
        else:
            #name
            name_td = tds[0].text_content().replace('\n', ' ');
            if yes_td == 'r':
                #vote.yes(name_td);
                print '^'
            if nays_td == 'r':
                #vote.no(name_td)
                print '\/'
            if abstent_td == 'r':
                #vote.other(name_td)
                print '-'
            #observaciones
            #observations_td =  tds[5].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','')
           

    
parse_chamber()
