import dateutil
import lxml.html
import pytz
import re
import tempfile

from openstates.scrape import Scraper, Bill
from openstates.utils import convert_pdf


class GUBillScraper(Scraper):
    _tz = pytz.timezone("Pacific/Guam")
    # non-greedy match on bills in the "list" page
    bill_match_re = re.compile("(<p>.*?<br>)", re.DOTALL)
    sponsors_match_re = re.compile(r"Sponsor\(s\) -(.*)<p>", re.DOTALL)
    desc_match_re = re.compile(r"^\s?<p>(.*?)<li>", re.DOTALL)
    filtered_details = ["BILL HISTORY", "Bill HISTORY", "CLERKS OFFICE", "Page 1"]
    date_re = re.compile("([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})")
    date_time_re = re.compile(
        r"([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}\s?\n?[0-9]{1,2}:[0-9]{2} [apAP]\.?[mM]\.?)",
    )
    committee_re = re.compile("([cC]ommittee on [a-zA-Z, \n]+)")

    def _download_pdf(self, url: str):
        res = self.get(url)
        fd = tempfile.NamedTemporaryFile()
        fd.write(res.content)
        text = convert_pdf(fd.name, type="xml")
        return text

    def _get_details(self, url: str):
        data = lxml.html.fromstring(self._download_pdf(url)).xpath("//text")
        """
        Ends up with something like:
        <text top="23" left="6" width="88" height="5" font="0">I Mina’trentai Siette Na Liheslaturan Guåhan</text>
        <text top="29" left="6" width="84" height="5" font="0">THE THIRTY-SEVENTH GUAM LEGISLATURE</text>
        <text top="36" left="6" width="25" height="5" font="0">Bill HISTORY </text>
        <text top="42" left="6" width="39" height="5" font="0">8/21/2023 2:56 PM</text>
        <text top="24" left="510" width="158" height="7" font="1"><i><b>I Mina'trentai Siette Na Liheslaturan Guåhan</b></i></text>
        <text top="33" left="563" width="54" height="9" font="2"><b>BILL STATUS</b></text>
        <text top="84" left="59" width="24" height="7" font="3"><b>BILL NO.</b></text>
        <text top="84" left="151" width="28" height="7" font="3"><b>SPONSOR</b></text>
        <text top="84" left="341" width="15" height="7" font="3"><b>TITLE</b></text>
        <text top="79" left="511" width="15" height="7" font="3"><b>DATE</b></text>
        <text top="88" left="500" width="38" height="7" font="3"><b>INTRODUCED</b></text>
        <text top="79" left="594" width="15" height="7" font="3"><b>DATE</b></text>
        <text top="88" left="587" width="29" height="7" font="3"><b>REFERRED</b></text>
        <text top="79" left="696" width="16" height="7" font="3"><b>CMTE</b></text>
        <text top="88" left="690" width="29" height="7" font="3"><b>REFERRED</b></text>
        <text top="84" left="791" width="39" height="7" font="3"><b>FISCAL NOTES</b></text>
        <text top="75" left="886" width="20" height="7" font="3"><b>PUBLIC</b></text>
        <text top="84" left="883" width="26" height="7" font="3"><b>HEARING</b></text>
        <text top="92" left="889" width="15" height="7" font="3"><b>DATE</b></text>
        <text top="75" left="987" width="15" height="7" font="3"><b>DATE</b></text>
        <text top="84" left="977" width="35" height="7" font="3"><b>COMMITTEE</b></text>
        <text top="92" left="975" width="40" height="7" font="3"><b>REPORT FILED</b></text>
        <text top="84" left="1089" width="19" height="7" font="3"><b>NOTES</b></text>
        <text top="142" left="53" width="35" height="8" font="4"><b>163-37 (LS)</b></text>
        <text top="105" left="109" width="36" height="7" font="5">Chris Barnett</text>
        <text top="114" left="109" width="54" height="7" font="5">Sabina Flores Perez</text>
        <text top="123" left="109" width="64" height="7" font="5">Christopher M. Dueñas</text>
        <text top="132" left="109" width="68" height="7" font="5">Dwayne T.D. San Nicolas</text>
        <text top="140" left="109" width="44" height="7" font="5">Telo T. Taitague</text>
        <text top="149" left="109" width="46" height="7" font="5">Thomas J. Fisher</text>
        <text top="158" left="109" width="39" height="7" font="5">Joanne Brown</text>
        <text top="167" left="109" width="38" height="7" font="5">Frank Blas, Jr.</text>
        <text top="176" left="109" width="65" height="7" font="5">Tina Rose Muña Barnes</text>
        <text top="105" left="223" width="32" height="7" font="5">AN ACT TO</text>
        <text top="105" left="257" width="12" height="7" font="6"><i>ADD</i></text>
        <text top="105" left="273" width="201" height="7" font="5">A NEW ITEM (K) TO § 77112.2 OF CHAPTER 77, TITLE 21 GUAM CODE</text>
        <text top="114" left="223" width="251" height="7" font="5">ANNOTATED RELATIVE TO BANNING THE USE OF THE PASEO STADIUM FOR CONCERTS</text>
        <text top="123" left="223" width="186" height="7" font="5">OR ANY OTHER ACTIVITY THAT CAN DAMAGE THE BASEBALL FIELD.</text>
        <text top="105" left="506" width="25" height="8" font="7">8/16/23</text>
        <text top="115" left="504" width="29" height="8" font="7">1:56 p.m.</text>
        <text top="105" left="589" width="25" height="8" font="7">8/21/23</text>
        <text top="105" left="643" width="125" height="8" font="7">Committee on Maritime Transportation, </text>
        <text top="115" left="651" width="109" height="8" font="7">Air Transportation, Parks, Tourism, </text>
        <text top="125" left="643" width="124" height="8" font="7">Higher Education and the Advancement </text>
        <text top="135" left="647" width="116" height="8" font="7">of Women, Youth, and Senior Citizens</text>
        <text top="105" left="784" width="54" height="8" font="7">Request: 8/21/23</text>
        <text top="897" left="7" width="46" height="8" font="7">CLERKS OFFICE</text>
        <text top="897" left="580" width="20" height="8" font="7">Page 1</text>
        """
        # filter out empty and obvious text we don't need
        text_only = "\n".join(
            [
                d.text
                for d in data
                if d.text
                and d.text.strip()
                and d.text.strip() not in self.filtered_details
            ]
        )
        details = {"IntroducedDate": None, "ReferredDate": None, "Committee": None}
        full_dates = self.date_time_re.findall(text_only)
        days = self.date_re.findall(text_only)
        if full_dates:
            details["IntroducedDate"] = self._tz.localize(
                dateutil.parser.parse(full_dates[1])
            )
        if days:
            details["ReferredDate"] = self._tz.localize(dateutil.parser.parse(days[2]))
        committee = self.committee_re.search(text_only)
        if committee:
            details["Committee"] = " ".join(
                committee.group(1).replace("\n", " ").split()
            )
        return details

    def _process_bill(self, session: str, bill: str, root_url: str):
        xml = lxml.html.fromstring(bill)
        xml.make_links_absolute(root_url)
        # Bill No. 163-37 (LS) or Bill No. 160-37 (LS) - WITHDRAWN match
        name_parts = (
            xml.xpath("//strong")[0].text.strip().removeprefix("Bill No. ").split()
        )
        name = name_parts[0].strip().removeprefix("Bill No. ")
        # bill_type = name_parts[1].strip("(").strip(")")
        bill_link = xml.xpath("//a/@href")[0]
        bill_obj = Bill(
            name,
            legislative_session=session,
            chamber="unicameral",
            title="See Introduced Link",
            classification="bill",
        )
        bill_obj.add_source(root_url, note="Bill Index")
        bill_obj.add_source(bill_link, note="Bill Introduced")
        if "WITHDRAWN" in "".join(name_parts):
            details = self._get_details(bill_link)
            if details["IntroducedDate"]:
                bill_obj.add_action("Introduced", details["IntroducedDate"])
            if details["ReferredDate"]:
                if details["Committee"]:
                    bill_obj.add_action(
                        "Referred To Committee",
                        details["ReferredDate"],
                        organization=details["Committee"],
                    )
                else:
                    bill_obj.add_action(
                        "Referred To Committee", details["ReferredDate"]
                    )

            yield bill_obj
        else:
            status = xml.xpath("//li")[0].xpath("a/@href")[0]
            bill_obj.add_document_link(url=status, note="Bill Status")
            description = (
                self.desc_match_re.search(bill).group(1).strip().split("<p>")[-1]
            )
            bill_obj.title = description.title()
            # sponsors are deliniated by / and \n, so we need to strip many characters
            sponsors = [
                s.strip("/").strip()
                for s in self.sponsors_match_re.search(bill).group(1).split("\n")
                if s.strip()
            ]
            bill_obj.add_sponsorship(
                name=sponsors[0],
                entity_type="person",
                classification="primary",
                primary=True,
            )
            for sponsor in sponsors[1:]:
                bill_obj.add_sponsorship(
                    name=sponsor,
                    entity_type="person",
                    classification="cosponsor",
                    primary=False,
                )

            for link in xml.xpath("//li")[1:]:
                url = link.xpath("a/@href")[0]
                title = link.xpath("a")[0].text
                bill_obj.add_document_link(url=url, note=title)

            # status PDF has introduced/passed/etc. dates
            details = self._get_details(status)
            if details["IntroducedDate"]:
                bill_obj.add_action("Introduced", details["IntroducedDate"])
            if details["ReferredDate"]:
                if details["Committee"]:
                    bill_obj.add_action(
                        "Referred To Committee",
                        details["ReferredDate"],
                        organization=details["Committee"],
                    )
                else:
                    bill_obj.add_action(
                        "Referred To Committee", details["ReferredDate"]
                    )
            yield bill_obj

    def _process_resolution(self, session: str, bill: str, root_url: str):
        xml = lxml.html.fromstring(bill)
        xml.make_links_absolute(root_url)
        # Bill No. 163-37 (LS) or Bill No. 160-37 (LS) - WITHDRAWN match
        res_parts = xml.xpath("//a")[0].text.removeprefix("Res. No. ").split()
        name = res_parts[0].strip()
        # res_type = res_parts[1].strip(")").strip("(")
        bill_link = xml.xpath("//a/@href")[0]
        bill_obj = Bill(
            name,
            legislative_session=session,
            chamber="unicameral",
            title="See Introduced Link",
            classification="resolution",
        )
        bill_obj.add_source(root_url, note="Bill Index")
        bill_obj.add_source(bill_link, note="Bill Introduced")
        description = self.desc_match_re.search(bill).group(1).strip().split("<p>")[-1]
        bill_obj.title = description.title()
        # sponsors are deliniated by / and \n, so we need to strip many characters
        sponsors = [
            s.strip("/").strip()
            for s in self.sponsors_match_re.search(bill).group(1).split("\n")
            if s.strip()
        ]
        result = None
        result_date = None
        if "-" in sponsors[-1]:
            name, result_data = sponsors[-1].split("-")
            sponsors[-1] = name
            result, result_date = result_data.split()
        if result and result_date:
            bill_obj.add_action(result, result_date)

        bill_obj.add_sponsorship(
            name=sponsors[0],
            entity_type="person",
            classification="primary",
            primary=True,
        )
        for sponsor in sponsors[1:]:
            bill_obj.add_sponsorship(
                name=sponsor,
                entity_type="person",
                classification="cosponsor",
                primary=False,
            )

        # status PDF has introduced/passed/etc. dates
        details = self._get_details(bill_link)
        if details["IntroducedDate"]:
            bill_obj.add_action("Introduced", details["IntroducedDate"])
        if details["ReferredDate"]:
            if details["Committee"]:
                bill_obj.add_action(
                    "Referred To Committee",
                    details["ReferredDate"],
                    organization=details["Committee"],
                )
            else:
                bill_obj.add_action("Referred To Committee", details["ReferredDate"])
        yield bill_obj

    def scrape(self, session):
        bills_url = f"https://guamlegislature.com/{session}_Guam_Legislature/{session}_bills_intro_content.htm"
        doc = self.get(bills_url).text.split("-->")[-1]
        for bill in self.bill_match_re.findall(doc):
            yield self._process_bill(session, bill, bills_url)

        # resolutions are at a separate address
        res_url = f"https://guamlegislature.com/{session}_Guam_Legislature/{session}_res_content.htm"
        doc = self.get(res_url).text.split("-->")[-2]
        for resolution in self.bill_match_re.findall(doc):
            yield self._process_resolution(session, resolution, res_url)
