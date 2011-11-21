from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html
import re

class NECommitteeScraper(CommitteeScraper):
    state = 'nd'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        #testing for chamber
        if chamber == 'upper':
            url_chamber_name = 'senate'
        else:
            url_chamber_name = 'house'

        #testing for starting year
        if int(term) == 62:
            start_year = 2011

        committee_types = ["standing-comm", "pro-comm"]
        for committee in committee_types:
           url = "http://www.legis.nd.gov/assembly/%s-%s/%s/%s/" % (term, start_year, url_chamber_name, committee)
           
           with self.urlopen(url) as page:
               page = lxml.html.fromstring(page)

               if committee == 'standing-comm':
                   self.scrapeStanding(chamber, page, url)
                   test = True
               else:
                   #self.scrapeProcedural(chamber, page, url)
                   test = True

    def scrapeStanding(self, chamber, page, url):
        comm_count = 1
        for comm_names in page.xpath('//div[@class="content"][1]/p//span'):
            name = re.sub('[^A-Za-z0-9]+', ' ', comm_names.text).replace(' ', '')
            comm = Committee(chamber, name)

            member_count = 1
            members_path = '//div[@class="content"][1]/table[@class="p"][%s]//tr/td[2]' % (str(comm_count))
            for members in comm_names.xpath(members_path):
                memberName = members.xpath('a')[0].text
                if memberName == None: #special case for Randy Boehning under Goverment and Vetran Affairs in House
                    memberName = members.xpath('a')[1].text
                memberName = re.sub('[^A-Za-z0-9]+', ' ', memberName)

                #role
                role_path = '//div[@class="content"][1]/table[@class="p"][%s]//tr[%s]/td[2]/a' % (comm_count, member_count)
                role_text = page.xpath(role_path)[0].tail
                if role_text != None:
                    if "Vice" in role_text:
                        role = "Vice-Chairman"
                    elif "Chairman" in role_text:
                        role = "Chairman"
                    else:
                        role = "Member"
                    comm.add_member(memberName, role) 
                else:
                    if member_count == 1:
                        role = "Chairman"
                    elif member_count == 2:
                        role = "Vice-Chairman"
                    else:
                        role = "Member"
                    comm.add_member(memberName, role)
                member_count += 1
            comm.add_source(url)
            self.save_committee(comm)
            comm_count += 1

    def scrapeProcedural(self, chamber, page, url):
        comm_count = 1
        for comm_names in page.xpath('//div[@class="content"][1]/p/a'):
            name = re.sub('[^A-Za-z0-9]+', ' ', comm_names.text).replace(' ', '')
            comm = Committee(chamber, page)
            
            print '\n\n' + name + '\n'
            members_path = '//div[@class="content"][1]/table[@class="p"][%s]//tr/td[2]/a' % (str(comm_count))
            print members_path
            #for members in comm_names.xpath(members_path):
            #    member = members.text
            #    member = re.sub('[^A-Za-z0-9]+', ' ', member)
            #    #print member
