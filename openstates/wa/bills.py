import datetime

from billy.scrape.bills import BillScraper, Bill

import lxml.etree


class WABillScraper(BillScraper):
    state = 'wa'

    _base_url = 'http://wslwebservices.leg.wa.gov/legislationservice.asmx'
    _ns = {'wa': "http://WSLWebServices.leg.wa.gov/"}

    def scrape(self, chamber, session):
        url = "%s/GetLegislationByYear?year=%s" % (self._base_url,
                                                   session[0:4])

        prev_bill = None
        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page)

            for leg_info in page.xpath(
                "//wa:LegislationInfo", namespaces=self._ns):

                bill_id = leg_info.xpath("string(wa:BillId)",
                                         namespaces=self._ns)
                bill_num = int(bill_id.split()[1])

                # Senate bills are numbered starting at 5000,
                # House at 1000
                if bill_num > 5000:
                    bill_chamber = 'upper'
                else:
                    bill_chamber = 'lower'

                if bill_chamber != chamber:
                    continue

                if bill_id[0:3] in ('SSB', 'SHB'):
                    # Merge committee substitutes with original bills.
                    # All the actions for the substitute should have been
                    # grabbed when we got the original, so just make
                    # note that there is an alternate ID. We may
                    # want to add the committee as a sponsor at some
                    # point too.
                    self.log("Merging %s with %s" % (
                        bill_id, prev_bill['bill_id']))
                    prev_bill['alternate_bill_ids'].append(bill_id)
                    self.save_bill(prev_bill)
                    continue

                bill = self.scrape_bill(chamber, session, bill_id)
                bill['alternate_bill_ids'] = []
                self.save_bill(bill)

                prev_bill = bill

    def scrape_bill(self, chamber, session, bill_id):
        biennium = "%s-%s" % (session[0:4], session[7:9])
        bill_num = bill_id.split()[1]

        url = ("%s/GetLegislation?biennium=%s&billNumber"
               "=%s" % (self._base_url, biennium, bill_num))

        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page).xpath("//wa:Legislation",
                                                     namespaces=self._ns)[0]

            title = page.xpath("string(wa:LongDescription)",
                               namespaces=self._ns)

            bill_type = page.xpath(
                "string(wa:ShortLegislationType/wa:LongLegislationType)",
                namespaces=self._ns).lower()

            if bill_type == 'gubernatorial appointment':
                return

            bill = Bill(session, chamber, bill_id, title,
                        type=[bill_type])

            chamber_name = {'lower': 'House', 'upper': 'Senate'}[chamber]
            version_url = ("http://www.leg.wa.gov/pub/billinfo/2011-12/"
                           "Htm/Bills/%s %ss/%s.htm" % (chamber_name,
                                                        bill_type.title(),
                                                        bill_num))
            bill.add_version(bill_id, version_url)

            fake_source = ("http://apps.leg.wa.gov/billinfo/"
                           "summary.aspx?bill=%s&year=%s" % (
                               bill_num, session[0:4]))
            bill.add_source(fake_source)

            self.scrape_sponsors(bill)
            self.scrape_actions(bill)

            return bill

    def scrape_sponsors(self, bill):
        bill_id = bill['bill_id'].replace(' ', '%20')
        session = bill['session']
        biennium = "%s-%s" % (session[0:4], session[7:9])

        url = "%s/GetSponsors?biennium=%s&billId=%s" % (
            self._base_url, biennium, bill_id)

        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page)

            for sponsor in page.xpath("//wa:Sponsor/wa:Name",
                                      namespaces=self._ns):
                bill.add_sponsor('sponsor', sponsor.text)

    def scrape_actions(self, bill):
        bill_id = bill['bill_id'].replace(' ', '%20')
        session = bill['session']
        biennium = "%s-%s" % (session[0:4], session[7:9])
        begin_date = "%s-01-10T00:00:00" % session[0:4]
        end_date = "%d-01-10T00:00:00" % (int(session[5:9]) + 1)

        chamber = bill['chamber']

        url = ("%s/GetLegislativeStatusChangesByBillId?billId=%s&"
               "biennium=%s&beginDate=%s&endDate=%s" % (self._base_url,
                                                        bill_id,
                                                        biennium,
                                                        begin_date,
                                                        end_date))
        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page)

            for status in page.xpath("//wa:LegislativeStatus",
                                     namespaces=self._ns):

                action = status.xpath("string(wa:HistoryLine)",
                                      namespaces=self._ns).strip()

                date = status.xpath("string(wa:ActionDate)",
                                    namespaces=self._ns).split("T")[0]
                date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

                atype = []

                if (action.startswith('Third reading, passed') or
                    action.startswith('Third reading, adopted')):

                    chamber = {'upper': 'lower', 'lower': 'upper'}[chamber]
                    atype.append('bill:passed')
                    atype.append('bill:reading:3')

                actor = chamber

                if (action.startswith('First reading') or
                    action.startswith('Read first time')):

                    atype.append('bill:introduced')
                    atype.append('bill:reading:1')
                elif action.startswith('Introduced'):
                    atype.append('bill:introduced')
                elif action.startswith('Governor signed'):
                    actor = 'executive'
                    atype.append('governor:signed')
                elif action == 'Adopted.':
                    atype.append('bill:passed')

                if 'Floor amendment(s) adopted' in action:
                    atype.append('amendment:passed')

                if 'referred' in action.lower():
                    atype.append('committee:referred')

                bill.add_action(actor, action, date, type=atype)
