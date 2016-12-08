import re
import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin

class DECommitteeScraper(CommitteeScraper,LXMLMixin):
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

        if chamber == "lower":
            #only scrape joint comms once
            self.scrape_joint_committees(term,session)

        url = urls[chamber] % (session,)
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

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

    def scrape_joint_committees(self,term,session):
        url = "http://legis.delaware.gov/legislature.nsf/testside.html?OpenPage&BaseTarget=right"
        page = self.lxmlize(url)
        joint_comms = page.xpath("//a[text()='Joint Committees']")
        comm_list = joint_comms[0].getnext()
        for li in comm_list.xpath("./li/a"):
            comm_name = li.text
            comm_link = li.attrib["href"]

            if comm_name.strip() == "Sunset": #I don't even want to go into it.
                new_link = "http://legis.delaware.gov/Sunset/"\
                    "Sunset.nsf/general+Info/JSC+Members?opendocument"
                assert new_link != comm_link, "Remove Sunset Committee special casing"
                comm_link = new_link

            committee = Committee("joint", comm_name)
            committee.add_source(comm_link)
            comm_page = self.lxmlize(comm_link)
            people = comm_page.xpath("//a/b")
            things_to_replace = ["Senator",
                                "Representative",
                                "(D)","(R)",
                                "House Minority Whip",
                                "House Majority Whip",
                                "Senate Minority Whip",
                                "Senate Majority Whip",
                                "House Minority Leader",
                                "House Majority Leader",
                                "Senate Minority Leader",
                                "Senate Majority Leader",
                                "President Pro Tempore",
                                "Speaker of the House"]
            for person in people:
                person_name = person.text_content()
                for thing in things_to_replace:
                    person_name = person_name.replace(thing,"")
                person_name = person_name.strip().strip(",")
                role = "Member"
                if person_name.strip()[-1] == ")":
                    person_name,role = person_name.rsplit("(",1)
                    role = role.replace(")","").strip()
                elif ", Vice-Chair" in person_name:
                    role = "Vice-Chair"
                    person_name = person_name.replace(", Vice-Chair","")
                elif ", Chair" in person_name:
                    role = "Chair"
                    person_name = person_name.replace(", Chair","")
                person_name = person_name.strip().strip(",").strip()
                committee.add_member(person_name,role)
            self.save_committee(committee)

