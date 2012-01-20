from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from billy.scrape.committees  import Committee

import lxml.html
import re, contextlib

HI_BASE_URL = "http://capitol.hawaii.gov"

def get_chamber_listing_url( chamber ):
    chamber_translation = {
        "upper" : "S",
        "lower" : "H"
    }
    return "%s/members/legislators.aspx?chamber=%s" % (
        HI_BASE_URL,
        chamber_translation[chamber]
    )

class HILegislatorScraper(LegislatorScraper):
    state = 'hi'

    def get_page( self, url ):
        with self.urlopen(url) as html:
            page = lxml.html.fromstring(html)
            return ( page, html )
        raise ScrapeError("Error getting the page. Sorry, man.")

    def scrape_homepage( self, url ):
        page, html = self.get_page( url )
        ret = { "source" : url }

        return ret

    def scrape_leg_page( self, url ):
        page, html = self.get_page(url)
        people = page.xpath( \
            "//table[@id='ctl00_ContentPlaceHolderCol1_GridView1']")[0]
        people = people.xpath('./tr')[1:]
        display_order = {
            "image"    : 0,
            "contact"  : 1,
            "district" : 2
        }

        ret = []

        for person in people:
            image    = person[display_order["image"]]
            contact  = person[display_order["contact"]]
            district = person[display_order["district"]]
            metainf  = self.scrape_contact_info( contact )
            district = self.scrape_district_info( district )
            homepage = self.scrape_homepage( metainf['homepage'] )

            image = "%s/%s" % (
                HI_BASE_URL,
                image.xpath("./*/img")[0].attrib['src']
            )

            pmeta = {
                "image"    : image,
                "source"   : [ url, homepage['source'] ],
                "district" : district
            }

            for meta in metainf:
                pmeta[meta] = metainf[meta]

            ret.append(pmeta)
        return ret

    def br_split( self, contact ):
        cel = []
        els = [ cel ]

        # krufty HTML requires stupid hacks
        elements = contact.xpath("./*")
        for element in elements:
            if element.tag == "br":
                cel = []
                els.append(cel)
            else:
                cel.append( element )
        return els

    def scrape_district_info( self, district ):
        return district[2].text_content()

    def scrape_contact_info( self, contact ):
        homepage = "%s/%s" % ( # XXX: Dispatch a read on this page
            HI_BASE_URL,
            contact.xpath("./a")[0].attrib['href']
        )

        els = self.br_split( contact )

        def _scrape_title( els ):
            return els[0].text_content()

        def _scrape_name( els ):
            lName = els[0].text_content()
            fName = els[2].text_content()
            return "%s %s" % ( fName, lName )

        def _scrape_party( els ):
            party = {
                "(D)" : "Democratic",
                "(R)" : "Republican"
            }

            try:
                return party[els[4].text_content()]
            except KeyError:
                return "Other"

        def _scrape_addr( els ):
            room_number = els[1].text_content()
            slug        = els[0].text_content()
            return "%s %s" % ( slug, room_number )

        def _scrape_room( els ):
            return els[1].text_content()

        def _scrape_phone( els ):
            return els[1].text_content()

        def _scrape_fax( els ):
            return els[1].text_content()

        def _scrape_email( els ):
            return els[1].text_content()

        contact_entries = {
            "title" : ( 0, _scrape_title ),
            "name"  : ( 1, _scrape_name ),
            "party" : ( 1, _scrape_party ),
            "addr"  : ( 2, _scrape_addr ),
            "room"  : ( 2, _scrape_room ),
            "phone" : ( 3, _scrape_phone ),
            "fax"   : ( 4, _scrape_fax ),
            "email" : ( 5, _scrape_email )
        }

        ret = {
            "homepage" : homepage
        }

        for entry in contact_entries:
            index, callback = contact_entries[entry]
            ret[entry] = callback( els[index] )
        return ret

    def scrape(self, chamber, session):
        metainf = self.scrape_leg_page(get_chamber_listing_url( chamber ))
        for leg in metainf:
            p = Legislator( session, chamber, leg['district'], leg['name'],
                party=leg['party'],
                # some additional things the website provides:
                photo_url=leg['image'],
                url=leg['homepage'],
                room=leg['room'],
                phone=leg['phone'],
                fax=leg['fax'],
                email=leg['email'],
                address=leg['addr'])
            for source in leg['source']:
                p.add_source( source )
            self.save_legislator( p )

