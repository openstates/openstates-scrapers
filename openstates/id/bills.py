import re
import datetime

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html


def split_names(text):
    text = text.replace(u'\xa0', ' ')
    for name in text.split(' -- ')[1].split(','):
        name = name.strip()
        if name and name != 'None':
            yield name


class IDBillScraper(BillScraper):
    state = 'id'

    def scrape(self, chamber, session):
        url = ("http://www.legislature.idaho.gov/legislation"
               "/%s/minidata.htm" % session)
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        bill_abbrev = {'lower': 'H', 'upper': 'S'}[chamber]
        for link in page.xpath("//a[contains(@href, 'legislation')]"):
            bill_id = link.text.strip()
            match = re.match(r'%s(CR|JM|P|R)?\d+' % bill_abbrev, bill_id)
            if not match:
                continue

            bill_type = {'CR': 'concurrent resolution',
                         'JM': 'joint memorial',
                         'P': 'proclamation',
                         'R': 'resolution'}.get(match.group(1), 'bill')

            title = link.xpath("string(../../td[2])").strip()
            bill = Bill(session, chamber, bill_id, title,
                        type=bill_type)
            self.scrape_bill(bill, link.attrib['href'])
            self.save_bill(bill)

    def scrape_bill(self, bill, url):
        bill.add_source(url)
        page = lxml.html.fromstring(self.urlopen(url))

        version_link = page.xpath("//a[contains(., 'Bill Text')]")[0]
        bill.add_version('Text', version_link.attrib['href'])

        act_table = page.xpath("//table")[5]
        actor = bill['chamber']
        prev_date = None
        for tr in act_table.xpath("tr"):
            if len(tr.xpath("td")) < 4:
                continue

            date = tr.xpath("string(td[2])").strip()
            if not date:
                date = prev_date
            prev_date = date
            date = datetime.datetime.strptime(date + "/" + bill['session'],
                                              "%m/%d/%Y").date()

            action = tr.xpath("string(td[3])").strip().replace(u'\xa0', ' ')

            if re.match(r"[^-]+\s+-\s+(PASSED|FAILED)\s+-", action):
                self.scrape_vote(bill, actor, date, tr.xpath("td[3]")[0])
                action = tr.xpath("td[3]")[0].text
                action += tr.xpath("string(td[3]/span[1])")
                action += ". " + tr.xpath("td[3]/br")[-1].tail
                action = action.replace(u'\xa0', ' ').strip()

            action = re.sub(r'\s+', ' ', action)

            bill.add_action(actor, action, date)

            if 'to House' in action:
                actor = 'lower'
            elif 'to Senate' in action:
                actor = 'upper'

    def scrape_vote(self, bill, chamber, date, td):
        motion = td.text
        result = td.xpath("string(span[1])").strip()
        passed = result.split()[0] == "PASSED"
        yes, no, other = [
            int(g) for g in re.search(r'(\d+)-(\d+)-(\d+)$', result).groups()]

        vote = Vote(chamber, date, motion, passed, yes, no, other)

        for name in split_names(td.xpath("span[. = 'AYES']")[0].tail):
            vote.yes(name)
        for name in split_names(td.xpath("span[. = 'NAYS']")[0].tail):
            vote.no(name)
        for name in split_names(td.xpath(
            "span[contains(., 'Absent')]")[0].tail):
            vote.other(name)

        assert len(vote['yes_votes']) == vote['yes_count']
        assert len(vote['no_votes']) == vote['no_count']
        assert len(vote['other_votes']) == vote['other_count']

        bill.add_vote(vote)
