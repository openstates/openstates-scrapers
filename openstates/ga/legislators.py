from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from lxml import html
import contextlib
import re
import scrapelib

class GALegislatorScraper(LegislatorScraper):
    state = 'ga'
    PARTY_DICT = {'D': 'Democratic', 'R': 'Republican', 'I': 'Independent'}
    email_matcher = re.compile("[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+(?:[A-Z]{2}|com|org|net|edu|gov|mil|biz|info|mobi|name|aero|asia|jobs|museum)\b")

    @contextlib.contextmanager
    def lxml_context(self, url):
        body = None
        try:
            body = unicode(self.urlopen(url), 'latin-1')
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
        year = int(term)

        if (year < 2000):
            raise NoDataForPeriod(year)
        if (year % 2 == 0):
            raise NoDataForPeriod(year)

        session = "%s_%s" % (year, str(year + 1)[-2:])

        if chamber == 'lower':
            base = "http://www1.legis.ga.gov/legis/%s/house/alpha.html" % session #/2009_10/house/alpha.html
        else:
            base = "http://www.legis.ga.gov/legis/%s/leg/sum/%s%s%d.htm"

        self.scrape_lower_house(base, chamber, term)

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
            found_it = True
            for row in roster:
                name = row.getchildren()[0]
                # attempt to get the url to the specific legislators page
                for name_child in name.getchildren():
                    if name_child.tag == 'a':
                        # Now that we got the specific legislators page, scrape that page
                        link = name_child.get('href')
                        if 'wilkinsonJoe' not in link and not found_it:
                            continue
                        found_it = True
                        legislator = self._scrape_individual_legislator_page(link, chamber, term)
                        if legislator is not None:
                            self.save_legislator(legislator)

    def _scrape_individual_legislator_page(self, url, term, chamber):
        """Scrape a specific lower house legislators page. The function will actually
        call one of three functions as there is 2 different bio templates and a completely
        separate one for the speaker of the house.
        
        Example url: http://www1.legis.ga.gov/legis/2009_10/house/bios/abdulsalaamRoberta/abdulsalaamRoberta.htm
        """
        print url
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
                   'legis.ga.gov.house.bio.css' in style_sheet.get('href') :
                    return self._scrape_individual_legislator_page_second_template(page, term, chamber)


            path = '//table[@id="hoverTable"]/tr'
            legislator_info = page.xpath(path)

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

            district = None
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

    def _scrape_individual_legislator_page_second_template(self, page, term, chamber):
        print 'found a second template one!!!'
        return Legislator(term, chamber, 'district #', 'Foo Bar Name', party='Democratic')

    def _scrape_speaker_of_the_house(self, url, term, chamber):
        pass
