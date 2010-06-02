from fiftystates.scrape.committees import CommitteeScraper, Committee

class MDCommitteeScraper(CommitteeScraper):

    state = 'md'

    def scrape_committees(self, chamber, year):
        # TODO: scrape senate committees
        house_url = 'http://www.msa.md.gov/msa/mdmanual/06hse/html/hsecom.html'

        with self.lxml(house_url) as (resp, doc):
            # distinct URLs containing /com/
            committees = set([l.get('href') for l in doc.cssselect('li a')
                              if l.get('href', '').find('/com/') != -1])

        for com in committees:
            com_url = 'http://www.msa.md.gov'+com
            with self.lxml(com_url) as (resp, cdoc):
                for h in cdoc.cssselect('h2, h3'):
                    if h.text:
                        committee_name = h.text
                        break
                cur_com = Committee('lower', committee_name)
                cur_com.add_source(com_url)
                for l in cdoc.cssselect('a[href]'):
                    if ' SUBCOMMITTEE' in (l.text or ''):
                        self.save_committee(cur_com)
                        cur_com = Committee('lower', l.text, committee_name)
                        cur_com.add_source(com_url)
                    elif 'html/msa' in l.get('href'):
                        cur_com.add_member(l.text)
                self.save_committee(cur_com)
