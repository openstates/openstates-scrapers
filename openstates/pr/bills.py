# -*- coding: utf-8 -*-
import re
import lxml.html
import datetime
import itertools
import pprint
import math
import sys
import requests
import pytz
from pupa.scrape import Scraper, Bill, VoteEvent as Vote


class NoSuchBill(Exception):
    pass


_voteChambers = (
    (u"Aprobado por el Senado en Votac", "upper"),
    (u"Aprobado por C", "lower"),
)

_docVersion = (
    ("Entirillado del Informe"),
    ("Texto de Aprobaci"),
    # ('Ley N'),
    ("rendido con enmiendas"),
    ("Radicado"),
)

_classifiers = (
    ("Radicado", "", "introduction"),
    (u"Aprobado por Cámara en Votación Final", "lower", "passage"),
    (u"Aprobado por el Senado en Votación", "upper", "passage"),
    ("Aparece en Primera Lectura del", "upper", "reading-1"),
    ("Aparece en Primera Lectura de la", "lower", "reading-1"),
    ("Enviado al Gobernador", "executive", "executive-receipt"),
    ("Veto", "executive", "executive-veto"),
    ("Veto de Bolsillo", "executive", "executive-veto"),
    # comissions give a report but sometimes they dont do any amendments and
    # leave them as they are.
    # i am not checking if they did or not. but it be easy just read the end and
    # if it dosnt have amendments it should say 'sin enmiendas'
    ("1er Informe", "", "amendment-amendment"),
    ("2do Informe", "", "amendment-amendment"),
    ("Aprobado con enmiendas", "", "amendment-passage"),
    (u"Remitido a Comisión", "", "referral-committee"),
    (u"Referido a Comisión", "", "referral-committee"),
    ("Retirada por su Autor", "", "withdrawal"),
    (
        "Comisión : * no recomienda aprobación de la medida",
        "",
        "committee-passage-unfavorable",
    ),
    ("Ley N", "executive", "executive-signature"),
)

# Reports we're not currently using that might come in handy:
# all bill ranges https://sutra.oslpr.org/osl/esutra/VerSQLReportingPRM.aspx?rpt=SUTRA-015
# updated since https://sutra.oslpr.org/osl/esutra/VerSQLReportingPRM.aspx?rpt=SUTRA-016


class PRBillScraper(Scraper):
    _TZ = pytz.timezone("America/Puerto_Rico")
    s = requests.Session()

    bill_types = {
        "P": "bill",
        "R": "resolution",
        "RK": "concurrent resolution",
        "RC": "joint resolution",
        "NM": "appointment",
        # 'PR': 'plan de reorganizacion',
    }

    def asp_post(self, url, params, page=None):
        headers = {
            "User-Agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36',
            'referer': url,
            'origin': 'https://sutra.oslpr.org',
            'authority': 'sutra.oslpr.org'
        }

        if page is None:
            page = self.s.get(url, headers=headers)
            page = lxml.html.fromstring(page.content)

        (viewstate,) = page.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator,) = page.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')
        (eventvalidation,) = page.xpath('//input[@id="__EVENTVALIDATION"]/@value')
        
        hiddenfield_js_url = page.xpath('//script[contains(@src,"?_TSM_HiddenField")]/@src')[0]
        hiddenfield_js_url = '{}{}'.format('https://sutra.oslpr.org/', hiddenfield_js_url)

        hiddenfield_js = self.s.get(hiddenfield_js_url).text

        before = re.escape('get("ctl00_tsm_HiddenField").value += \'')
        after = re.escape('\';Sys.Application.remove_load(fn);')
        token_re = '{}(.*){}'.format(before, after)
        result = re.search(token_re, hiddenfield_js)
        hiddenfield = result.group(1)

        form = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "__LASTFOCUS": "",
            "ctl00_tsm_HiddenField": hiddenfield,
            '__SCROLLPOSITIONX': '0',
            '__SCROLLPOSITIONY': '453',
        }

        form = {**form, **params}

        cookie_obj = requests.cookies.create_cookie(domain='sutra.oslpr.org', name='SUTRASplash', value='NoSplash')
        self.s.cookies.set_cookie(cookie_obj)

        xml = self.s.post(url, data=form, headers=headers).text
        return xml

    def clean_name(self, name):
        for ch in ["Sr,", "Sr.", "Sra.", "Rep.", "Sen."]:
            if ch in name:
                name = name.replace(ch, "")
        return name

    # Additional options:
    # window_start / window_end - Show bills updated between start and end. Format Y-m-d
    # window_end is optional, defaults to today if window_start is set
    def scrape(self, session=None, chamber=None, window_start=None, window_end=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified using %s", session)
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session, 1, window_start, window_end)

    def scrape_chamber(self, chamber, session, page_number=1, window_start=None, window_end=None, page=None):
        start_year = session[0:4]

        print("Scrape page {}".format(page_number))

        chamber_letter = {"lower": "C", "upper": "S"}[chamber]

        # If a window_start is provided, parse it
        # If a window_end is provided, parse it, if not default to today
        if window_start is None:
            start = ''
            end = ''
        else:
            window_start = datetime.datetime.strptime(window_start, "%Y-%m-%d")
            start = window_start.strftime("%m/%d/%Y")

            if window_end is None:
                end = datetime.datetime.now().strftime("%m/%d/%Y")
            else:
                window_end = datetime.datetime.strptime(window_end, "%Y-%m-%d")
                end = window_start.strftime("%m/%d/%Y")            

        # javascript:__doPostBack('ctl00$CPHBody$Tramites$dgResults$ctl54$ctl00','')

        params = {
            'ctl00$CPHBody$lovCuatrienio': start_year,
            'ctl00$CPHBody$lovTipoMedida': '-1',
            'ctl00$CPHBody$lovCuerpoId': chamber_letter,
            'ctl00$CPHBody$txt_Medida': '',
            'ctl00$CPHBody$txt_FechaDesde': start,
            'ctl00$CPHBody$ME_txt_FechaDesde_ClientState': '',
            'ctl00$CPHBody$txt_FechaHasta': end,
            'ctl00$CPHBody$ME_txt_FechaHasta_ClientState': '',
            'ctl00$CPHBody$txt_Titulo': '',
            'ctl00$CPHBody$lovLegisladorId': '-1',
            'ctl00$CPHBody$lovEvento': '-1',
            'ctl00$CPHBody$lovComision': '-1',
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
        }

        if page_number != 1:
            page_str = str(page_number - 1).rjust(2, '0')
            page_field = 'ctl00$CPHBody$dgResults$ctl54$ctl{}'.format(page_str)
            params['__EVENTTARGET'] = page_field
            params['ctl00$CPHBody$ddlPageSize'] = '50'
            resp = self.asp_post('https://sutra.oslpr.org/osl/esutra/MedidaBus.aspx', params, page)
        else:
            params['ctl00$CPHBody$btnFilter'] = 'Buscar'
            resp = self.asp_post('https://sutra.oslpr.org/osl/esutra/MedidaBus.aspx', params)

        page = lxml.html.fromstring(resp)

        # note there's a typo in a class, one set is DataGridItemSyle (syle) and the other is DataGridAltItemStyle (style)
        # if we're ever suddenly missing half the actions, check this
        for row in page.xpath('//tr[contains(@class,"DataGridItemSyle") or contains(@class,"DataGridAltItemStyle")]/@onclick'):
            bill_rid = self.extract_bill_rid(row)
            # bill_rid = 127866 #132106   -- good test bills
            # bill_rid = '122472'
            bill_url = 'https://sutra.oslpr.org/osl/esutra/MedidaReg.aspx?rid={}'.format(bill_rid)
            yield from self.scrape_bill(chamber, session, bill_url)
        
        result_count = int(page.xpath('//span[@id="ctl00_CPHBody_lblCount"]/text()')[0])
        max_page = math.ceil(result_count / 50)

        if (page_number < max_page):
            print("Scraping page {} of {}".format(page_number, max_page))


            yield from self.scrape_chamber(chamber, session, (page_number + 1), window_start, window_end, page)


    def extract_bill_rid(self, onclick):
        # bill links look like onclick="javascript:location.replace('MedidaReg.aspx?rid=125217');"
        before = re.escape('javascript:location.replace(\'MedidaReg.aspx?rid=')
        after = re.escape('\');')
        token_re = '{}(.*){}'.format(before, after)
        result = re.search(token_re, onclick)
        return result.group(1)

    def extract_version_url(self, onclick):
        before = re.escape('javascript:OpenDoc(\'')
        after = re.escape('\');')
        token_re = '{}(.*){}'.format(before, after)
        result = re.search(token_re, onclick)
        return result.group(1)

    def parse_action(self, chamber, bill, action, action_url, date):
        # if action.startswith('Referido'):
        # committees = action.split(',',1)
        # multiple committees
        if action.startswith("Ley N"):
            action = action[0:42]
        elif action.startswith("Res. Conj."):
            action = action[0:42]
        action_actor = ""
        atype = None
        # check it has a url and is not just text
        if action_url:
            action_url = action_url[0]
            isVersion = False
            for text_regex in _docVersion:
                if re.match(text_regex, action):
                    isVersion = True
            if isVersion:
                # versions are mentioned several times, lets use original name
                erroneous_filename = False
                action_url = action_url.lower().strip()
                if action_url.endswith((".doc", "dot")):
                    media_type = "application/msword"
                elif action_url.endswith(".rtf"):
                    media_type = "application/rtf"
                elif action_url.endswith(".pdf"):
                    media_type = "application/pdf"
                elif action_url.endswith(("docx", "dotx")):
                    media_type = (
                        "application/vnd.openxmlformats-officedocument"
                        + ".wordprocessingml.document"
                    )
                elif action_url.endswith("docm"):
                    self.warning("Erroneous filename found: {}".format(action_url))
                    erroneous_filename = True
                else:
                    raise Exception("unknown version type: %s" % action_url)
                if not erroneous_filename:
                    bill.add_version_link(
                        note=action,
                        url=action_url,
                        media_type=media_type,
                        on_duplicate="ignore",
                    )
            else:
                bill.add_document_link(action, action_url, on_duplicate="ignore")
            for pattern, action_actor, atype in _classifiers:
                if re.match(pattern, action):
                    break
                else:
                    action_actor = ""
                    atype = None
        if action_actor == "":
            if action.find("SENADO") != -1:
                action_actor = "upper"
            elif action.find("CAMARA") != -1:
                action_actor = "lower"
            else:
                action_actor = chamber

        # manual fix for data error on 2017-2020 P S0623
        if date == datetime.datetime(1826, 8, 1):
            date = date.replace(year=2018)

        bill.add_action(
            description=action.replace(".", ""),
            date=date.strftime("%Y-%m-%d"),
            chamber=action_actor,
            classification=atype,
        )
        return atype, action

    def classify_action(self, action_text):
        for pattern, action_actor, atype in _classifiers:
            if re.match(pattern, action_text):
                return [action_actor, atype]
        return ["", None]

    def classify_bill_type(self, bill_id):
        for abbr, value in self.bill_types.items():
            if bill_id.startswith(abbr):
                return value
        return None

    def classify_media_type(self, url):
        url = url.lower()
        if url.endswith((".doc", "dot")):
            media_type = "application/msword"
        elif url.endswith(".rtf"):
            media_type = "application/rtf"
        elif url.endswith(".pdf"):
            media_type = "application/pdf"
        elif url.endswith(("docx", "dotx")):
            media_type = (
                "application/vnd.openxmlformats-officedocument"
                + ".wordprocessingml.document"
            )
        elif url.endswith("docm"):
            self.warning("Erroneous filename found: {}".format(url))
            return None
        else:
            raise Exception("unknown version type: %s" % url)
        return media_type

    def clean_broken_html(self, html):
        return html.strip().replace('&nbsp', '')

    def parse_vote_chamber(self, bill_chamber, vote_name):
        if u"Confirmado por Senado" in vote_name:
            vote_chamber = 'upper'
        elif u"Votación Final" in vote_name:
            (vote_chamber, vote_name) = re.search(
                r"(?u)^\w+ por (.*?) en (.*)$", vote_name
            ).groups()
            if "Senado" in vote_chamber:
                vote_chamber = "upper"
            else:
                vote_chamber = "lower"

        elif "Cuerpo de Origen" in vote_name:
            vote_name = re.search(
                r"(?u)^Cuerpo de Origen (.*)$", vote_name
            ).group(1)
            vote_chamber = bill_chamber

        elif u"informe de Comisión de Conferencia" in vote_name:
            # (vote_chamber, vote_name) = re.search(
            #     r"(?u)^(\w+) (\w+ informe de Comisi\wn de Conferencia)$",
            #     vote_name,
            # ).groups()
            if "Senado" in vote_name:
                vote_chamber = "upper"
            elif u"Cámara" in vote_name:
                vote_chamber = "lower"
            else:
                raise AssertionError(
                    u"Unable to identify vote chamber: {}".format(vote_name)
                )                
        # TODO replace bill['votes']
        elif u"Se reconsideró" in vote_name:
            vote_chamber = chamber
        elif "por Senado" in vote_name:
            vote_chamber = 'upper'
        else:
            raise AssertionError(
                u"Unknown vote text found: {}".format(vote_name)
            )
        return vote_chamber

    def parse_vote(self, chamber, bill, row, action_text, action_date, url):
        yes = int(row.xpath('.//div[label[contains(text(), "A Favor")]]/span[contains(@class,"smalltxt")]/text()')[0])
        no = int(row.xpath('.//div[label[contains(text(), "En Contra")]]/span[contains(@class,"smalltxt")]/text()')[0])
        abstain = int(row.xpath('.//div[label[contains(text(), "Abstenido")]]/span[contains(@class,"smalltxt")]/text()')[0])
        absent = int(row.xpath('.//div[label[contains(text(), "Ausente")]]/span[contains(@class,"smalltxt")]/text()')[0])

        vote_chamber = self.parse_vote_chamber(chamber, action_text)

        classification = "passage" if u"Votación Final" in action_text else "other"

        vote = Vote(
            chamber=vote_chamber,
            start_date=action_date,
            motion_text=action_text,
            result="pass" if (yes > no) else "fail",
            bill=bill,
            classification=classification,
        )
        vote.add_source(url)
        vote.set_count("yes", yes)
        vote.set_count("no", no)
        vote.set_count("absent", absent)
        vote.set_count("abstain", abstain)

        # we don't want to add the attached vote PDF as a version,
        # so add it as a document
        # TODO: maybe this should be set as the source?
        self.parse_version(bill, row, is_document=True)

        yield vote

    def parse_version(self, bill, row, is_document=False):
        # they have empty links in every action, and icon links preceeding the actual link
        # so only select links with an href set, and skip the icon links
        for version_row in row.xpath('.//a[contains(@class,"gridlinktxt") and contains(@id, "FileLink") and boolean(@href)]'):
            version_url = version_row.xpath('@href')[0]
            # version url is in an onclick handler built into the href
            version_url = self.extract_version_url(version_url)
            if version_url.startswith('../SUTRA'):
                version_url = version_url.replace('../SUTRA/', '')
                version_url = 'https://sutra.oslpr.org/osl/SUTRA/{}'.format(version_url)
            elif not version_url.lower().startwith('http'):
                self.error("Unknown version url in onclick: {}".format(version_url))

            version_title = self.clean_broken_html(version_row.xpath('text()')[0])

            if is_document:
                bill.add_document_link(
                    note=version_title,
                    url=version_url,
                    media_type=self.classify_media_type(version_url),
                    on_duplicate='ignore',
                )            
            else:
                bill.add_version_link(
                    note=version_title,
                    url=version_url,
                    media_type=self.classify_media_type(version_url),
                    on_duplicate='ignore',
                )

    def scrape_author_table(self, year, bill, bill_id):
        report_url = 'https://sutra.oslpr.org/osl/esutra/VerSQLReportingPRM.aspx?rpt=SUTRA-011&Q={}&Medida={}'.format(
            '2017',
            bill_id
        )
        html = self.get(report_url).text
        page = lxml.html.fromstring(html)

        for row in page.xpath('//tr[td/div/div[contains(text(),"Autor")]]')[1:]:
            name = row.xpath('td[2]/div/div/text()')[0].strip()
            # currently not saving sponsor party, but here's the xpath
            # party = row.xpath('td[3]/div/div/text()')[0].strip()

            # sometimes there's an extra dummy row beyond the first
            if name == 'Legislador':
                continue

            bill.add_sponsorship(
                name,
                entity_type="person",
                classification="primary",
                primary=True,
            )

    def scrape_action_table(self, chamber, bill, page, url):
        # NOTE: in theory this paginates, but it defaults to 50 actions per page
        # and I couldn't find examples of bills with > 50

        page.make_links_absolute('https://sutra.oslpr.org/osl/SUTRA/')

        # note there's a typo in a class, one set is DataGridItemSyle (syle) and the other is DataGridAltItemStyle (style)
        # if we're ever suddenly missing half the actions, check this
        for row in page.xpath('//table[@id="ctl00_CPHBody_TabEventos_dgResults"]/tr[contains(@class,"DataGridItemSyle") or contains(@class,"DataGridAltItemStyle")]'):
            action_text = row.xpath('.//label[contains(@class,"DetailFormLbl")]/text()')[0]
            action_text = self.clean_broken_html(action_text)
            # div with a label containing Fecha, following span.smalltxt
            # need to be this specific because votes have the same markup
            raw_date = row.xpath('.//div[label[contains(text(), "Fecha")]]/span[contains(@class,"smalltxt")]/text()')[0]
            raw_date = self.clean_broken_html(raw_date)
            action_date = self._TZ.localize(datetime.datetime.strptime(raw_date, "%m/%d/%Y"))
            parsed_action = self.classify_action(action_text)

            bill.add_action(
                description=action_text,
                date=action_date,
                chamber=parsed_action[0],
                classification=parsed_action[1],               
            )

            # if it's a vote, we don't want to add the document as a bill version
            if row.xpath('.//label[contains(text(), "A Favor")]'):
                yield from self.parse_vote(chamber, bill, row, action_text, action_date, url)
            else:
                self.parse_version(bill, row)

    def scrape_bill(self, chamber, session, url):
        html = self.get(url).text
        page = lxml.html.fromstring(html)
        # search for Titulo, accent over i messes up lxml, so use 'tulo'
        title = page.xpath('//span[@id="ctl00_CPHBody_txtTitulo"]/text()')[0].strip()
        bill_id = page.xpath('//span[@id="ctl00_CPHBody_txt_Medida"]/text()')[0].strip()

        bill_type = self.classify_bill_type(bill_id)

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )

        self.scrape_author_table('2017', bill, bill_id)

        yield from self.scrape_action_table(chamber, bill, page, url)


        # author = doc.xpath(u'//td/b[contains(text(),"Autor")]/../text()')[0]
        # for aname in author.split(","):
        #     aname = self.clean_name(aname).strip()
        #     if aname:
        #         bill.add_sponsorship(
        #             aname, classification="primary", entity_type="person", primary=True
        #         )

        # co_authors = doc.xpath(u'//td/b[contains(text(),"Co-autor")]/../text()')
        # if len(co_authors) != 0:
        #     for co_author in co_authors[1].split(","):
        #         bill.add_sponsorship(
        #             self.clean_name(co_author).strip(),
        #             classification="cosponsor",
        #             entity_type="person",
        #             primary=False,
        #         )

        # action_table = doc.xpath("//table")[-1]
        # bill_vote_chamber = None
        # for row in action_table[1:]:
        #     tds = row.xpath("td")
        #     # ignore row missing date
        #     if len(tds) != 2:
        #         continue
        #     if tds[0].text_content():
        #         date = datetime.datetime.strptime(tds[0].text_content(), "%m/%d/%Y")
        #     action = tds[1].text_content().strip()
        #     # parse the text to see if it's a new version or a unrelated document
        #     # if has a hyphen let's assume it's a vote document

        #     # get url of action
        #     action_url = tds[1].xpath("a/@href")
        #     atype, action = self.parse_action(chamber, bill, action, action_url, date)

        #     # Some lower-house roll calls could be parsed, but finnicky
        #     # Most roll lists are just images embedded within a document,
        #     # and offer no alt text to scrape
        #     # Instead, just scrape the vote counts
        #     regex = r"(?u)^(.*),\s([\s\d]{2})-([\s\d]{2})-([\s\d]{2})-([\s\d]{0,2})$"
        #     vote_info = re.search(regex, action)
        #     if vote_info and re.search(r"\d{1,2}", action):
        #         vote_name = vote_info.group(1)

        #         if u"Votación Final" in vote_name:
        #             (vote_chamber, vote_name) = re.search(
        #                 r"(?u)^\w+ por (.*?) en (.*)$", vote_name
        #             ).groups()
        #             if "Senado" in vote_chamber:
        #                 vote_chamber = "upper"
        #             else:
        #                 vote_chamber = "lower"

        #         elif "Cuerpo de Origen" in vote_name:
        #             vote_name = re.search(
        #                 r"(?u)^Cuerpo de Origen (.*)$", vote_name
        #             ).group(1)
        #             vote_chamber = chamber

        #         elif u"informe de Comisión de Conferencia" in vote_name:
        #             (vote_chamber, vote_name) = re.search(
        #                 r"(?u)^(\w+) (\w+ informe de Comisi\wn de Conferencia)$",
        #                 vote_name,
        #             ).groups()
        #             if vote_chamber == "Senado":
        #                 vote_chamber = "upper"
        #             else:
        #                 vote_chamber = "lower"

        #         # TODO replace bill['votes']
        #         elif u"Se reconsideró" in vote_name:
        #             if bill_vote_chamber:
        #                 vote_chamber = bill_vote_chamber
        #             else:
        #                 vote_chamber = chamber

        #         else:
        #             raise AssertionError(
        #                 u"Unknown vote text found: {}".format(vote_name)
        #             )

        #         vote_name = vote_name.title()

        #         yes = int(vote_info.group(2))
        #         no = int(vote_info.group(3))
        #         other = 0
        #         if vote_info.group(4).strip():
        #             other += int(vote_info.group(4))
        #         if vote_info.group(5).strip():
        #             other += int(vote_info.group(5))

        #         vote = Vote(
        #             chamber=vote_chamber,
        #             start_date=date.strftime("%Y-%m-%d"),
        #             motion_text=vote_name,
        #             result="pass" if (yes > no) else "fail",
        #             bill=bill,
        #             classification="passage",
        #         )
        #         vote.set_count("yes", yes)
        #         vote.set_count("no", no)
        #         vote.set_count("other", other)
        #         vote.add_source(url)
        #         yield vote
        #         bill_vote_chamber = chamber

        bill.add_source(url)
        yield bill
