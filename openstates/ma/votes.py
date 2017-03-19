# -*- coding: utf-8 -*-
import re
import datetime
import lxml.html

from billy.scrape.utils import convert_pdf
from billy.scrape.votes import VoteScraper, Vote as BillyVote


class MAVoteScraper(VoteScraper):
    jurisdiction = 'ma'

    def scrape(self, chamber, session):

        if chamber == 'upper':
            branch = '53656e617465'
        else:
            branch = '486f757365'

        session4url = {
            '190th': '3139307468202843757272656e7429',
            '189th': '3138397468202832303135202d203230313629',
            '188th': '3138387468202832303133202d203230313429',
            '187th': '3138377468202832303131202d203230313229',
            '186th': '3138367468202832303039202d203230313029'
        }

        url = 'https://malegislature.gov/Bills/Search?Page=1&Refinements%' \
              '5Blawsgeneralcourt%5D={0}&Refinements%5Blawsbranchname%5D=' \
              '{1}&Refinements%5Blawsfilingtype%5D=42696c6c' \
              .format(session4url[session], branch)

        self.scrape_bill(url, chamber, session)

        page = lxml.html.fromstring(self.get(url).text)
        total_pages = page.xpath("//ul[@class='pagination pagination-sm']/" +
                                 "li[@class='']/a/@onclick")

        try:
            # findng maximum number of pages in search results
            max_page = int(re.search(r'\d+', total_pages[1]).group())
        except:
            max_page = 1

        # scraping other pages

        for i in range(2, max_page+1):
            url = 'https://malegislature.gov/Bills/Search?Page={}&Refinements%' \
                  '5Blawsgeneralcourt%5D={}&Refinements%5Blawsbranchname%5D=' \
                  '{}&Refinements%5Blawsfilingtype%5D=42696c6c' \
                  .format(i, session4url[session], branch)
            self.scrape_bill(url, chamber, session)

    def scrape_bill(self, url, chamber, session):
        page = lxml.html.fromstring(self.get(url).text)
        bill_urls = list(set(page.xpath("//tbody[@class='customFade in']/tr/td/a/@href")))
        for bill_no in bill_urls:
            # url for a bill page
            bill_url = 'https://malegislature.gov{0}/RollCall'.format(bill_no)
            bill_page = lxml.html.fromstring(self.get(bill_url).text)
            # dates will be empty if there is no Roll Call for a particular bill.
            dates = bill_page.xpath("//div[@class='table-responsive']/table/caption/span/text()")
            if len(dates) > 0:
                motions = bill_page.xpath("//div[@class='table-responsive']/table/tbody/tr/td" +
                                          "[@class='titleCol']/text()")
                # data for yes and no counts
                first = bill_page.xpath("//div[@class='table-responsive']/table/tbody/tr/td" +
                                        "[@class='statusCol']/div/text()")
                # data for other counts
                second = bill_page.xpath("//div[@class='table-responsive']/table/tbody/tr/td" +
                                         "[@class='statusCol']/text()")
                # urls for downloading pdfs
                third = bill_page.xpath("//div[@class='table-responsive']/table/tbody/tr/td" +
                                        "[@class='downloadCol']/a/@href")

                y_n_counts = []
                other_counts = []
                pdf_urls = []

                for i in range(0, len(dates)):
                    dates[i] = datetime.datetime.strptime(dates[i], '%B %d, %Y')
                    for c in first:
                        y_n_counts.append(map(int, re.findall(r'\d+', c)))

                    pdf_urls.append("https://malegislature.gov{}".format(third[i]))

                for i in xrange(1, len(second), 2):
                    other_counts.append(map(int, re.findall(r'\d+', "".join((second[i].
                                                            replace('\r\n', '').split())))))

                for i in range(0, len(dates)):
                    vote = BillyVote(chamber, dates[i], motions[i],
                                     y_n_counts[i][0] > y_n_counts[i][1],
                                     y_n_counts[i][0], y_n_counts[i][1], other_counts[i][0])
                    vote.add_source(url)
                    vote.add_source(bill_url)
                    url4pdf = pdf_urls[i]
                    # downloading pdf
                    vote_file, resp = self.urlretrieve(url4pdf)
                    text = convert_pdf(vote_file, type='text')
                    text = text.decode('utf8')
                    wordList = filter(None, text.split(' '*5))
                    # calculating names of legislators voted for yes and no respectively.
                    yes_members, no_members = self.members(wordList)

                    for i in range(0, len(yes_members)):
                        vote.yes(yes_members[i])
                    for i in range(0, len(no_members)):
                        vote.yes(no_members[i])

                    vote['session'] = session
                    vote['bill_chamber'] = chamber
                    vote['bill_id'] = str(bill_no[11:])
                    self.save_vote(vote)

    # To extract data from pdf text downloaded
    def members(self, wordList):
        final = []
        yes = []
        no = []
        for i in wordList:
            for j in i.split("\n"):
                final.append(j)
        c = 0
        for i in final:
            if c == 1 and i != '  NAYS.' and i != '':
                yes.append(i)
            if c == 2 and i != final[-1] and i != '':
                no.append(i)
            if i == '  YEAS.':
                c = 1
            if i == '  NAYS.':
                c = 2
        yes = [x.strip(' ') for x in yes]
        no = [x.strip(' ') for x in no]
        return yes, no
