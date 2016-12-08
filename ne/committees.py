from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html


class NECommitteeScraper(CommitteeScraper):
    jurisdiction = 'ne'
    latest_only = True

    def scrape(self, term, chambers):
        self.standing_comm()
        self.select_special_comm()

    def select_special_comm(self):
        main_url = 'http://www.nebraskalegislature.gov/committees/select-committees.php'
        page = self.get(main_url).text
        page = lxml.html.fromstring(page)

        for comm_names in page.xpath('//div[@class="content_box"]'):
           name = comm_names.xpath('h2')[0].text
           if name != None:
               committee = Committee('upper', name)
               committee.add_source(main_url)
               for senators in comm_names.xpath('ul[@class="nobullet"]/li'):
                   senator = senators[0].text
                   if 'Chairperson' in senator:
                       role = 'Chairperson'
                       senator = senator[5:-13].strip()
                   else:
                       role = 'member'
                       senator = senator[5:].strip()
                   committee.add_member(senator, role)
           else:
               name = comm_names.xpath('h2/a')[0].text
               committee = Committee('upper', name)
               committee.add_source(main_url)
               for senators in comm_names.xpath('ul[@class="nobullet"]/li'):
                   senator = senators[0].text
                   if 'Chairperson' in senator:
                       role = 'chairperson'
                       senator = senator[5:-13].strip()
                   else:
                       role = 'member'
                       senator = senator[5:].strip()
                   committee.add_member(senator, role)

           if not committee['members']:
               self.warning('no members in %s', committee['committee'])
           else:
               self.save_committee(committee)



    def standing_comm(self):
       main_url = 'http://www.nebraskalegislature.gov/committees/standing-committees.php'
       page = self.get(main_url).text
       page = lxml.html.fromstring(page)
       
       for comm_links in page.xpath('//div[@id="content_text"]/div[@class="content_box_container"]/div[@class="content_box"][1]/ul[@class="nobullet"]/li/a'):
           detail_link = comm_links.attrib['href']

           detail_page =  self.get(detail_link).text
           detail_page = lxml.html.fromstring(detail_page)
           name = detail_page.xpath('//div[@id="content"]/div[@class="content_header"]/div[@class="content_header_right"]/a')[0].text
           name = name.split()
           name = name[0:-1]
           comm_name = ''
           for x in range(len(name)):
               comm_name += name[x] + ' '
           comm_name = comm_name[0: -1]
           committee = Committee('upper', comm_name)

           for senators in detail_page.xpath('//div[@id="sidebar"]/ul[1]/li[1]/ul/li/a'):
               senator = senators.text
               if 'Chairperson' in senator:
                   role = 'Chairperson'
                   senator = senator[6:-13].strip()
               else:
                    role = 'member'
                    senator = senator[6:].strip()
               committee.add_member(senator, role)
           committee.add_source(main_url)
           committee.add_source(detail_link)
           self.save_committee(committee)
