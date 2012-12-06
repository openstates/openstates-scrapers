import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee

class MDCommitteeScraper(CommitteeScraper):

    jurisdiction = 'md'

    def scrape(self, term, chambers):
        lower = 'http://www.msa.md.gov/msa/mdmanual/06hse/html/hsecom.html'
        upper = 'http://www.msa.md.gov/msa/mdmanual/05sen/html/sencom.html'
        joint = 'http://www.msa.md.gov/msa/mdmanual/07leg/html/ga.html'

        if 'lower' in chambers:
            self.scrape_committees('lower', lower)
        if 'upper' in chambers:
            self.scrape_committees('upper', upper)
            self.scrape_committees('joint', joint)

    def scrape_committees(self, chamber, url):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        # distinct URLs containing /com/
        committees = set([l.get('href') for l in doc.xpath('//li/a')
                          if l.get('href', '').find('/com/') != -1])

        for com in committees:
            com_url = 'http://www.msa.md.gov'+com
            chtml = self.urlopen(com_url)
            cdoc = lxml.html.fromstring(chtml)
            for h in cdoc.xpath('//*[self::h2 or self::h3]'):
                if h.text:
                    committee_name = h.text
                    break

            # non committees
            if 'DEFUNCT' in committee_name or 'ORGANIZATION' in committee_name:
                continue

            cur_com = Committee(chamber, committee_name)
            cur_com.add_source(com_url)
            for l in cdoc.xpath('//a[@href]'):
                txt = l.text or ''
                if ' SUBCOMMITTEE' in txt or 'OVERSIGHT COMMITTEE' in txt:
                    self.save_committee(cur_com)
                    cur_com = Committee(chamber, committee_name, l.text)
                    cur_com.add_source(com_url)
                elif 'html/msa' in l.get('href'):
                    prev = l.getprevious()
                    name = l.text
                    if name.endswith(','):
                        name = name[:-1]
                    cur_com.add_member(name)
            self.save_committee(cur_com)
