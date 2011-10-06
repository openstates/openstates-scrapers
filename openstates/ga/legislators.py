from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from lxml import html
import contextlib
import scrapelib

class GALegislatorScraper(LegislatorScraper):
    """Let me first start by saying, I'm sorry you have to look at this. In a nutshell, the lower legislator
    websites are a nightmare, they all are pretty much formed by hand it appears and a lot has slight differences.
    I did the best I could, the senate scrapping is much better to look at :)

    You can find me at doug.morgan@gmail.com if you have questions.
    """
    state = 'ga'
    PARTY_DICT = {'D': 'Democratic', 'R': 'Republican', 'I': 'Independent'}

    @contextlib.contextmanager
    def lxml_context(self, url, method="GET", body=None):
        body = None
        try:
            body = unicode(self.urlopen(url, method=method, body=body), 'latin-1')
        except scrapelib.HTTPError:
            yield None
        if body:
            elem = html.fromstring(body)
            try:
                yield elem
            except:
                #self.show_error(url, body)
                raise

    def scrape(self, chamber, term):

        if chamber == "upper":
            url = "http://www.senate.ga.gov/senators/en-US/SenateMembersList.aspx"
            self.scrape_upper_house(url, chamber, term)
        else:
            year = int(term[0: term.index('-')])

            session = "%s_%s" % (year, str(year + 1)[-2:])

            if chamber == 'lower':
                base = "http://www1.legis.ga.gov/legis/%s/house/alpha.html" % session #/2009_10/house/alpha.html
            else:
                base = "http://www.legis.ga.gov/legis/%s/leg/sum/%s%s%d.htm"

            self.scrape_lower_house(base, chamber, term)

    def scrape_upper_house(self, url, chamber, term):
        """Scrape the 'upper' (Senate) GA House.

        url: http://www.senate.ga.gov/senators/en-US/SenateMembersList.aspx
        """
        with self.lxml_context(url) as page:
            path = '//div[@style="font-size:13px;"]/span'
            span_tags = page.xpath(path)

            # every set of 3 span tags is one senator, so break that up correctly
            span_tag_sets = []
            i = 0
            while i < len(span_tags):
                span_tag_set = span_tags[i:i+3]
                span_tag_sets.append(span_tag_set)
                i+=3

            for span_tags in span_tag_sets:
                name_and_party_tag = span_tags[0].text_content()
                district_tag = span_tags[1].text_content()
                city_tag = span_tags[2].text_content()

                # Parse Party
                if 'Democrat' in name_and_party_tag:
                    party = "Democratic"
                elif 'Republican' in name_and_party_tag:
                    party = "Republican"
                elif "Independent" == name_and_party_tag:
                    party = "Independent"

                # Parse name
                name_parts = name_and_party_tag.split()
                if len(name_parts) == 2:
                    last_name = name_parts[0].strip(",")
                    first_name = name_parts[1]
                    suffix = None
                elif len(name_parts) == 3:
                    last_name = name_parts[0].strip(",")
                    suffix = name_parts[1].strip(",")
                    first_name = name_parts[2]

                # Parse district
                district = district_tag.strip()

                # Parse city
                city = city_tag.strip()[2:]

                legislator = Legislator(term,
                                        chamber,
                                        district,
                                        first_name + " " + last_name,
                                        first_name = first_name,
                                        last_name = last_name,
                                        suffix = suffix,
                                        party=party,
                                        city=city)
                legislator.add_source(url)
                self.save_legislator(legislator)

    def scrape_lower_house(self, url, chamber, term):
        """Scrape the 'lower' GA House. The representative page contains a list of reps
        but we have to go into their individual bio pages in order to extract all necessary
        information. This will iterate over the main representative list page and follow the
        link to their bio page.

        url e.g. http://www1.legis.ga.gov/legis/2009_10/house/alpha.html
        """
        with self.lxml_context(url) as page:
            page.make_links_absolute(url)
            path = '//table[@id="hoverTable"]/tr'
            roster = page.xpath(path)[1:]
            for row in roster:
                district = row.getchildren()[1].text_content()
                name = row.getchildren()[0]
                # attempt to get the url to the specific legislators page
                for name_child in name.getchildren():
                    if name_child.tag == 'a':
                        # Now that we got the specific legislators page, scrape that page
                        link = name_child.get('href')
                        if 'Bio' in link:
                            link = link.replace('Bio', '')  # Don't go to bio pages
                            # Make sure if it ends in html go to htm as the regular contact pages are htm pages
                            if link.endswith("html"):
                                link = link.replace("html", 'htm')
                        # skip vacant seats
                        if name_child.text == 'VACANT':
                            continue
                        legislator = self._scrape_individual_legislator_page(link, term, chamber, district=district)
                        if legislator is not None:
                            self.save_legislator(legislator)

    def _scrape_individual_legislator_page(self, url, term, chamber, district=None):
        """Scrape a specific lower house legislators page. The function will actually
        call one of three functions as there is 2 different bio templates and a completely
        separate one for the speaker of the house.

        Example url: http://www1.legis.ga.gov/legis/2009_10/house/bios/abdulsalaamRoberta/abdulsalaamRoberta.htm
        """
        if 'speaker/index.htm' in url:
            return self._scrape_speaker_of_the_house(url, term, chamber)

        with self.lxml_context(url) as page:
            # page == None == 404
            if page is None:
                return None

            page.make_links_absolute(url)

            # first check to see if this is the 'original' template or the new one
            stylesheet_path = '//link[@rel="stylesheet"]'
            stylesheets = page.xpath(stylesheet_path)

            for style_sheet in stylesheets:
                if 'legis.ga.gov.house.factsheet.css' in style_sheet.get('href') or \
                   'legis.ga.gov.house.bio.css' in style_sheet.get('href'):
                    return self._scrape_individual_legislator_page_second_template(page, term, chamber, district=district)

            path = '//table[@id="hoverTable"]/tr'
            legislator_info = page.xpath(path)

            # There is one page, "www1.legis.ga.gov/legis/2011_12/house/bios/williamsCoach.htm" that has
            # malformed HTML, going to manually do that one:
            if "www1.legis.ga.gov/legis/2011_12/house/bios/williamsCoach.htm" in url:
                legislator = Legislator(term,
                                        chamber,
                                        district,
                                        '"Coach" Williams',
                                        party="Democrate")
                return legislator

            # See if we got to the first row, some templates don't start with their table as 'hoverTable'
            # in this case let's just get the first table on the page as that is seeming to work well.
            if not legislator_info:
                path = '//table'
                tables = page.xpath(path)
                legislator_info = tables[0].getchildren()
            first_row = legislator_info[0]

            td_elements = first_row.getchildren()[0]
            name = td_elements[0].text_content().strip()
            party = td_elements[1].text_content().strip()[0:1].upper()
            # There was some cases where the party wasn't in a <p> it was after the
            # <h2>name</h2> foo <br />, seriously wtf
            if party not in self.PARTY_DICT:
                elements = td_elements.text_content().split('\n')
                for ele in elements:
                    ele = ele.strip()
                    if " - " in ele:
                        party = ele[0:1]
                        break
                    elif ele.upper() == 'REPUBLICAN':
                        party = 'R'
                        break
                    elif ele.upper() == 'DEMOCRAT':
                        party = 'D'
                        break
                if party == '':
                    party = td_elements.text_content().split('\n')[1].strip()[0:1]

            if not district:
                if len(td_elements) < 3 or "District" not in td_elements[2].text_content():
                    text_content = first_row[1].text_content().split('\n')
                    district = text_content[0].strip()[len("District "):]
                else:
                    district = td_elements[2].text_content().strip()[len("District "):]

            # Not every legislator has a sworn in date or facebook url, so attempt to parse
            # and just pass if it fails
            sworn_in = None
            try:
                sworn_in = td_elements[4].text_content().strip()[len("Sworn in "):]
            except:
                pass

            facebook_url = None
            try:
                facebook_url = td_elements[5].get('href')
            except:
                pass

            photo_url = None
            try:
                td_elements = first_row.getchildren()[1]
                photo_url = td_elements[0].getchildren()[0].get('src')#.replace("../", "")
            except:
                pass

            # Second row:
            second_row = legislator_info[1]
            address_info = second_row.getchildren()[0].text_content().split("<br />")[0].split("\n")
            phone_number = address_info.pop()
            address = " ".join(address_info)

            email = None
            try:
                text_content = second_row.text_content().split('\n')
                for content in text_content:
                    if '@' in content.strip():
                        email = content.strip()
            except IndexError:
                try:
                    email = second_row.getchildren()[1].getchildren()[0].text_content()
                except:
                    pass

            legislator = Legislator(term,
                                    chamber,
                                    district,
                                    name,
                                    party=self.PARTY_DICT[party],
                                    email=email,
                                    photo_url=photo_url,
                                    facebook_url=facebook_url,
                                    address=address,
                                    sworn_in_date=sworn_in,
                                    office_phone=phone_number)
            legislator.add_source(url)
            return legislator

    def _scrape_individual_legislator_page_second_template(self, page, term, chamber, district=None):
        party = None
        li_nodes = page.xpath('//li/text()')
        for li_node in li_nodes:
            if 'Democrat' in li_node:
                party = "Democrat"
                break
            elif 'Republican' in li_node:
                party = "Republican"
                break
            elif "I" == li_node.strip():
                party = "Independent"
                break

        h1_nodes = page.xpath('//h1/text()')
        if len(h1_nodes) > 0:
            name = h1_nodes[0][len("Representative "):]

        return Legislator(term, chamber, district, name, party=party)

    def _scrape_speaker_of_the_house(self, url, term, chamber):
        """The speaker of the house has a special page, because he is just OH so special</sarcasm>

        Main page url like: http://www1.legis.ga.gov/legis/2011_12/house/speaker/index.htm
        but need to scrape: http://www1.legis.ga.gov/legis/2011_12/house/speaker/bio.html
        """
        if url.endswith("index.htm"):
            url = url.replace("index.htm", "bio.html")
        with self.lxml_context(url) as page:
            path = '//div[@id="title"]'
            speaker_info_div = page.xpath(path)
            if speaker_info_div and len(speaker_info_div) == 1:
                # This isn't exactly great but it's the best/quickest solution for now
                speaker_info = speaker_info_div[0].text_content().split()
                name = speaker_info[2] + " " + speaker_info[3]
                party = None
                if "R-" in speaker_info[4]:
                    party = "Republican"
                elif "D-" in speaker_info[4]:
                    party = "Democrat"
                elif "I-" in speaker_info[4]:
                    party = "Independent"

                district = None
                if "district" in speaker_info[6].lower():
                    district = speaker_info[7].strip(")")

                legislator = Legislator(term,
                                        chamber,
                                        district,
                                        name,
                                        party=party)
                legislator.add_source(url)
                return legislator
