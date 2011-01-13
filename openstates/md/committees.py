import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee

class MDCommitteeScraper(CommitteeScraper):

    state = 'md'

    def scrape(self, chamber, term):
        com_url = {'lower': 'http://www.msa.md.gov/msa/mdmanual/06hse/html/hsecom.html',
                   'upper': 'http://www.msa.md.gov/msa/mdmanual/05sen/html/sencom.html'}
        # joint: http://www.msa.md.gov/msa/mdmanual/07leg/html/ga.html

        with self.urlopen(com_url[chamber]) as html:
            doc = lxml.html.fromstring(html)
            # distinct URLs containing /com/
            committees = set([l.get('href') for l in doc.cssselect('li a')
                              if l.get('href', '').find('/com/') != -1])

        for com in committees:
            com_url = 'http://www.msa.md.gov'+com
            with self.urlopen(com_url) as chtml:
                cdoc = lxml.html.fromstring(chtml)
                for h in cdoc.cssselect('h2, h3'):
                    if h.text:
                        committee_name = h.text
                        break
                cur_com = Committee(chamber, committee_name)
                cur_com.add_source(com_url)
                for l in cdoc.cssselect('a[href]'):
                    if ' SUBCOMMITTEE' in (l.text or ''):
                        self.save_committee(cur_com)
                        cur_com = Committee(chamber, committee_name, l.text)
                        cur_com.add_source(com_url)
                    elif 'html/msa' in l.get('href'):
                        prev = l.getprevious()
                        name = l.text
                        if name.endswith(','):
                            name = name[:-1]
                        if prev is not None and prev.tag == 'i':
                            cur_com.add_member(name, 'ex-officio')
                        else:
                            cur_com.add_member(name)
                self.save_committee(cur_com)
