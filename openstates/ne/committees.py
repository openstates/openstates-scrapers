from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

class NECommitteeScraper(CommitteeScraper):
    state = 'ne'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        #self.standing_comm()
        self.select_special_comm()

    def select_special_comm(self):
        main_url = 'http://www.nebraskalegislature.gov/committees/select-committees.php'
        with self.urlopen(main_url) as page:
            page = lxml.html.fromstring(page)

            comm_names = page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[@class="content_box_container"]/div[@class="content_box"]/h2/a')
            for x in range(len(comm_names)):
                print comm_names[x].text

                #senators = page.xpath('/ul[@class="nobullet"]/li/a')
                #print senators
            #print "\n"
            for comm_links in page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[@class="content_box_container"]/div[@class="content_box"]/h2'):
                comm_name = comm_links.text
                if comm_name != None:
                    print comm_name + '\n'
                    senator = comm_links.xpath('/ul[@class="nobullet"]/li/a').text
                    print senator



    def standing_comm(self):
       main_url = 'http://www.nebraskalegislature.gov/committees/standing-committees.php'
       with self.urlopen(main_url) as page:
           page = lxml.html.fromstring(page)
           
           for comm_links in page.xpath('/html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="content_text"]/div[@class="content_box_container"]/div[@class="content_box"][1]/ul[@class="nobullet"]/li/a'):
               detail_link = comm_links.attrib['href']

               with self.urlopen(detail_link) as detail_page:
                   detail_page = lxml.html.fromstring(detail_page)
                   name = detail_page.xpath('/html/body[@class="home blog"]/div[@id="page"]/div[@id="content"]/div[@class="content_header"]/div[@class="content_header_right"]/a')[0].text
                   name = name.split()
                   name = name[0:-1]
                   comm_name = ''
                   for x in range(len(name)):
                       comm_name += name[x] + ' '
                   comm_name = comm_name[0: -1]
                   committee = Committee('upper', comm_name)

                   for senators in detail_page.xpath('/html/body[@class="home blog"]/div[@id="page"]/div[@id="sidebar"]/ul[1]/li[1]/ul/li/a'):
                       senator = senators.text
                       if 'Chairperson' in senator:
                           role = 'Chairperson'
                           senator = senator[6: -13]
                       else:
                            role = 'member'
                            senator = senator[6:-1]
                       committee.add_member(senator, role)
                   committee.add_source(main_url)
                   committee.add_source(detail_link)
                   self.save_committee(committee)
