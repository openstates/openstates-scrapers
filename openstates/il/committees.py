from pupa.scrape import Scraper, Organization
import lxml.html

from ._committees import COMMITTEES
from ._utils import canonicalize_url

class IlCommitteeScraper(Scraper):

    def scrape_members(self, o, url):
        data = self.get(url).text
        if 'No members added' in data:
            return
        doc = lxml.html.fromstring(data)

        for row in doc.xpath('//table[@cellpadding="3"]/tr')[1:]:
            tds = row.xpath('td')

            # remove colon and lowercase role
            role = tds[0].text_content().replace(':','').strip().lower()

            name = tds[1].text_content().strip()
            o.add_member(name, role)


    def scrape(self):
        chambers = (('upper', 'senate'), ('lower', 'house'))
        committees = {}

        for chamber, chamber_name in chambers:

            for session in range(93, 101):

                url = 'http://ilga.gov/{0}/committees/default.asp?GA={1}'.format(chamber_name, session)
                html = self.get(url).text
                doc = lxml.html.fromstring(html)
                doc.make_links_absolute(url)

                top_level_com = None

                for a in doc.xpath('//a[contains(@href, "members.asp")]'):
                    name = a.text.strip()
                    code = a.getparent().getnext()
                    com_url = canonicalize_url(a.get('href'))
                    if 'TaskForce' in com_url:
                        code = None
                        o_id = (name, code)
                    else:
                        code = code.text_content().strip()
                        o_id = COMMITTEES[(name, code)]

                    if o_id in committees:
                        committees[o_id]['name'].add(name)
                        committees[o_id]['code'].add(code)
                        committees[o_id]['source'].add(com_url)

                    else:
                        committees[o_id] = {'name': {name},
                                            'code': {code},
                                            'source': {com_url}}

                    if (code is not None and
                         '-' in code and
                        code not in ('HSGA-SGAS',
                                     'HAPE-APES')):
                        committees[o_id]['parent'] = top_level
                    else:
                        committees[o_id]['chamber'] = chamber
                        top_level = o_id

        top_level = {o_id : committee for o_id, committee in
                     committees.items() if 'chamber' in committee}

        sub_committees = {o_id : committee for o_id, committee in
                          committees.items() if 'parent' in committee}

        for o_id, committee in list(top_level.items()):
            o = dict_to_org(committee)
            top_level[o_id] = o
            yield o

        for committee in sub_committees.values():
            committee['parent'] = top_level[committee['parent']]
            o = dict_to_org(committee)
            yield o


def dict_to_org(committee):
    names = sorted(committee['name'])
    first_name = names.pop()
    if 'chamber' in committee:
        o = Organization(first_name,
                         classification='committee',
                         chamber=committee['chamber'])
    else:
        o = Organization(first_name,
                         classification='committee',
                         parent_id=committee['parent'])
    for other_name in names:
        o.add_name(other_name)
    for code in committee['code']:
        if code:
            o.add_name(code)
    for source in committee['source']:
        o.add_source(source)

    return o
