# -*- coding: utf-8 -*-
import re
import lxml.html
import datetime
import requests
import pytz
from openstates.scrape import Scraper, Bill, VoteEvent as Vote


class NoSuchBill(Exception):
    pass


_classifiers = (
    ("Radicado", "", "introduction"),
    ("Aprobado por Cámara en Votación Final", "lower", "passage"),
    ("Aprobado por el Senado en Votación", "upper", "passage"),
    ("Aparece en Primera Lectura del", "upper", "reading-1"),
    ("Aparece en Primera Lectura de la", "lower", "reading-1"),
    ("Enviado al Gobernador", "executive", "executive-receipt"),
    ("Veto", "executive", "executive-veto"),
    ("Veto de Bolsillo", "executive", "executive-veto"),
    # commissions give a report but sometimes they dont do any amendments and
    # leave them as they are.
    # i am not checking if they did or not. but it be easy just read the end and
    # if it doesn't have amendments it should say 'sin enmiendas'
    ("1er Informe", "", "amendment-amendment"),
    ("2do Informe", "", "amendment-amendment"),
    ("Aprobado con enmiendas", "", "amendment-passage"),
    ("Remitido a Comisión", "", "referral-committee"),
    ("Referido a Comisión", "", "referral-committee"),
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

    # keep a reference to the last search results page
    # so we can scrape the right event validation code
    # for paginating
    last_page = None

    bill_types = {
        "P": "bill",
        "R": "resolution",
        "RK": "concurrent resolution",
        "RC": "joint resolution",
        "NM": "appointment",
        # 'PR': 'plan de reorganizacion',
    }

    def clean_name(self, name):
        for ch in ["Sr,", "Sr.", "Sra.", "Rep.", "Sen."]:
            if ch in name:
                name = name.replace(ch, "")
        return name

    # Additional options:
    # window_start / window_end - Show bills updated between start and end. Format Y-m-d
    # window_end is optional, defaults to today if window_start is set
    # tipo is leg type: PC, PS, etc. See "Tipo de Medida" on the search form
    def scrape(self, session=None, chamber=None, page=None):
        self.seen_votes = set()
        self.seen_bills = set()
        self.seen_bill_identifiers = set()
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_search_results(
                chamber,
                session,
                page,
            )

    def scrape_search_results(self, chamber, session, page=None):
        cuatrienio_id = session[0:4]
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }
        resp = self.s.get(
            "https://sutra.oslpr.org/medidas?cuatrienio_id={}&autores=&comision_id=&page=1".format(
                cuatrienio_id
            ),
            headers=headers,
            verify=False,
        )
        page = lxml.html.fromstring(resp.text)
        pagelist = page.xpath(
            '//span[contains(@class,"items-baseline")]/a/@aria-label'
        )[-1]
        pages = re.findall(r"\d+", pagelist)[0]
        for number in range(1, int(pages) + 1):
            resps = self.s.get(
                "https://sutra.oslpr.org/medidas?cuatrienio_id={}&autores=&comision_id=&page={}".format(
                    cuatrienio_id, number
                ),
                headers=headers,
                verify=False,
            )
            pagehtml = lxml.html.fromstring(resps.text)

            # note there's a typo in a css class, one set is DataGridItemSyle (syle)
            # and the other is DataGridAltItemStyle (style)
            # if we're ever suddenly missing half the bills, check this
            for row in pagehtml.xpath('//ul[@class="list-none"]/a/@href'):
                # Good test bills: 127866 132106 122472
                # bill_rid = '122472'
                bill_url = "https://sutra.oslpr.org{}".format(row)
                if bill_url not in self.seen_bills:
                    yield from self.scrape_bill(chamber, session, bill_url)
                    self.seen_bills.add(bill_url)

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
            self.warning("unknown version type: %s" % url)
            return None
        return media_type

    def clean_broken_html(self, html):
        return html.strip().replace("&nbsp", "")

    def parse_vote_chamber(self, bill_chamber, vote_name):
        if "Confirmado por Senado" in vote_name:
            vote_chamber = "upper"
        elif "Votación Final" in vote_name:
            (vote_chamber, vote_name) = re.search(
                r"(?u)^\w+ por (.*?) en (.*)$", vote_name
            ).groups()
            if "Senado" in vote_chamber:
                vote_chamber = "upper"
            else:
                vote_chamber = "lower"

        elif "Cuerpo de Origen" in vote_name:
            vote_name = re.search(r"(?u)^Cuerpo de Origen (.*)$", vote_name).group(1)
            vote_chamber = bill_chamber

        elif "informe de Comisión de Conferencia" in vote_name:
            # (vote_chamber, vote_name) = re.search(
            #     r"(?u)^(\w+) (\w+ informe de Comisi\wn de Conferencia)$",
            #     vote_name,
            # ).groups()
            if "Senado" in vote_name:
                vote_chamber = "upper"
            elif "Cámara" in vote_name:
                vote_chamber = "lower"
            else:
                raise AssertionError(
                    "Unable to identify vote chamber: {}".format(vote_name)
                )
        # TODO replace bill['votes']
        elif "Se reconsideró" in vote_name:
            vote_chamber = bill_chamber
        elif "por Senado" in vote_name:
            vote_chamber = "upper"
        elif "Cámara aprueba" in vote_name:
            vote_chamber = "lower"
        elif "Senado aprueba" in vote_name:
            vote_chamber = "upper"
        elif "Aprobado mediante votación por lista":
            vote_chamber = bill_chamber
        else:
            raise AssertionError("Unknown vote text found: {}".format(vote_name))
        return vote_chamber

    def parse_vote(self, chamber, bill, row, action_text, action_date, url):
        vote_chamber = self.parse_vote_chamber(chamber, action_text)
        classification = "passage" if "Votación Final" in action_text else []

        vote = Vote(
            chamber=vote_chamber,
            start_date=action_date,
            motion_text=action_text,
            result="pass",
            bill=bill,
            classification=classification,
        )
        vote.add_source(url)
        vote.set_count("yes", 0)
        vote.set_count("no", 0)
        vote.set_count("absent", 0)
        vote.set_count("abstain", 0)

        # we don't want to add the attached vote PDF as a version,
        # so add it as a document
        # TODO: maybe this should be set as the source?
        self.parse_version(bill, row, is_document=True)

        yield vote

    def parse_version(self, bill, row, is_document=False):
        # they have empty links in every action, and icon links preceeding the actual link
        # so only select links with an href set, and skip the icon links
        links = row.xpath("./following-sibling::a")
        for version_row in links:
            version_url = version_row.xpath("@href")[0]
            # version url is in an onclick handler built into the href
            version_url = "https://sutra.oslpr.org{}".format(version_url)

            version_title = self.clean_broken_html(row.text_content())

            possible_date_elems = row.xpath("./following-sibling::p/span/text()")
            version_date = ""
            for version_date_text in possible_date_elems:
                try:
                    date = datetime.datetime.strptime(
                        version_date_text, "%m/%d/%Y"
                    ).date()
                    version_date = date.strftime("%Y-%m-%d")
                except ValueError:
                    # could not parse that text to a date, so skip it
                    continue
            if version_date == "":
                self.warning(
                    f"Unable to parse date on version of {bill}, possible dates: {possible_date_elems}"
                )

            media_type = self.classify_media_type(version_url)
            if not media_type:
                continue
            if is_document:
                bill.add_document_link(
                    note=version_title,
                    url=version_url,
                    media_type=media_type,
                    on_duplicate="ignore",
                    date=version_date,
                )
            else:
                bill.add_version_link(
                    note=version_title,
                    url=version_url,
                    media_type=media_type,
                    on_duplicate="ignore",
                    date=version_date,
                )

    def scrape_author_table(self, authurl, url, bill):
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "referer": url,
            "cookie": "_ga=GA1.2.2038047349.1736526892; _ga_VQ7KX9LLCG=GS1.1.1736526892.1.1.1736526940.0.0.0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }
        html = self.s.get(authurl, headers=headers, verify=False).text
        page = lxml.html.fromstring(html)
        name = page.xpath("//title/text()")[0].strip().replace(" - Sutra", "")
        # currently not saving sponsor party, but here's the xpath
        # sometimes there's an extra dummy row beyond the first
        if name != "Legislador":
            bill.add_sponsorship(
                name, entity_type="person", classification="primary", primary=True
            )

    def scrape_action_table(self, chamber, bill, page, url):
        # NOTE: in theory this paginates, but it defaults to 50 actions per page
        # and I couldn't find examples of bills with > 50
        # note there's a typo in a class, one set is
        # DataGridItemSyle (syle) and the other is DataGridAltItemStyle (style)
        # if we're ever suddenly missing half the actions, check this
        rows = page.xpath('//ul[@role="list"]/li//h2')
        for row in rows:
            action_text_elements = row.xpath(
                './span[@class="text-sutra-primary"]//text()'
            )
            if len(action_text_elements) == 0:
                # Found at least one action that has different structure
                # see Ley 1-2025 on https://sutra.oslpr.org/medidas/153232
                action_text_elements = row.xpath(".//text()")
            action_text = action_text_elements[0]
            action_text = self.clean_broken_html(action_text)
            raw_date = row.xpath(
                './following-sibling::p//span[contains(text(), "Fecha")]/../text()'
            )[0]
            raw_date = self.clean_broken_html(raw_date)
            if raw_date == "":
                self.warning("No date available for {}, skipping".format(action_text))
                continue

            action_date = self._TZ.localize(
                datetime.datetime.strptime(raw_date, "%m/%d/%Y")
            )
            parsed_action = self.classify_action(action_text)

            # manual fix for data error on 2017-2020 P S0623
            if action_date == datetime.datetime(1826, 8, 1):
                action_date = action_date.replace(year=2018)

            bill.add_action(
                description=action_text,
                date=action_date,
                chamber=parsed_action[0],
                classification=parsed_action[1],
            )

            # as of 2025-01-13 there are no votes and unsure how they will appear
            # so for now this is commented out, as it fails to accurately distinguish
            # a vote from a bill version.
            # A yield statement will needed in calling function if this is returned
            #
            # if it's a vote, we don't want to add the document as a bill version
            # if row.xpath('./following-sibling::p//span/a[contains(@href, "doc")]'):
            #     if url not in self.seen_votes:
            #         yield from self.parse_vote(
            #             chamber, bill, row, action_text, action_date, url
            #         )
            #         self.seen_votes.add(url)
            # else:
            self.parse_version(bill, row)

    def scrape_bill(self, chamber, session, url):
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }
        html = self.s.get(url, headers=headers, verify=False).text
        page = lxml.html.fromstring(html)

        page_header_elems = page.xpath(
            '//main//div[contains(@class, "items-center")]/h1/text()'
        )
        if len(page_header_elems) > 0:
            page_header_text = page_header_elems[0].strip()
            bill_id = re.findall(r"[A-Z]{2,3}\d{4}", page_header_text)[0]
        else:
            self.logger.error(f"Bill found with no bill identifier at {url}")

        bill_title_elems = page.xpath(
            '//span/strong[text()="Título:"]/../following-sibling::span'
        )
        if len(bill_title_elems) > 0:
            title = bill_title_elems[0].text_content().strip()
        else:
            self.logger.error(f"Bill found with no title at {url}")

        # PR occasionally repeats a bill at different URLs (????)
        # example:
        # PC0205 https://sutra.oslpr.org/medidas/152982
        # PC0205 https://sutra.oslpr.org/medidas/152909
        if bill_id in self.seen_bill_identifiers:
            return
        else:
            self.seen_bill_identifiers.add(bill_id)

        bill_type = self.classify_bill_type(bill_id)

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=bill_type,
        )
        try:
            urlkey = re.findall(r"legisladores\/M\-[0-9]+\-[0-9]+", html)
        except KeyError:
            urlkey = []

        if len(urlkey) > 0:
            for aurl in list(set(urlkey)):
                authurl = "https://sutra.oslpr.org/" + aurl
                self.scrape_author_table(authurl, url, bill)

        # action table MAY contains votes
        # however as of 2025-01-13 I can't find any examples
        # see commented-out code in this method
        self.scrape_action_table(chamber, bill, page, url)

        bill.add_source(url)
        yield bill
