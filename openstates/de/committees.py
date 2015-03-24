import re
import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee


class DECommitteeScraper(CommitteeScraper):
    jurisdiction = "de"

    def scrape(self, chamber, term):

        urls = {
            'upper': 'http://legis.delaware.gov/LIS/LIS%s.nsf/SCommittees',
            'lower': 'http://legis.delaware.gov/LIS/LIS%s.nsf/HCommittees'
        }

        # Mapping of term names to session numbers (see metatdata).
        term2session = {"2015-2016": "148", "2013-2014": "147",
                        "2011-2012": "146"}

        session = term2session[term]

        url = urls[chamber] % (session,)
        self.log(url)
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        committees = {}

        for row in page.xpath('//tr'):
            if len(row.xpath('./td')) > 0:
                #if statement removes header tr
                comm = row.xpath('.//a')[1]
                comm_name = comm.text_content().strip()
                comm_url = comm.attrib["href"]

                comm_page = lxml.html.fromstring(self.get(comm_url).text)
                comm_page.make_links_absolute(comm_url)
                committee = Committee(chamber, comm_name)
                committee.add_source(comm_url)
                committee.add_source(url)

                chair = comm_page.xpath(".//div[@class='sub_title']")
                chair = chair[0].text.replace("Chairman:","").strip()
                committee.add_member(chair,"Chairman")

                for table in comm_page.xpath(".//table"):
                    header,content = table.xpath(".//td")
                    header = header.text_content().strip()
                    content = content.text_content().strip()
                    if "Vice" in header:
                        if content:
                            committee.add_member(content,"Vice-Chairman")
                    elif header == "Members:":
                        for m in content.split("\n"):
                            committee.add_member(m.strip())





                self.save_committee(committee)
