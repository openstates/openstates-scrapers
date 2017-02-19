import os
import subprocess
import lxml.html


class Spatula:
    """ mixin for scrapelib.Scraper """
    def scrape_page_items(self, page_type, url=None, **kwargs):
        yield from page_type(self, url=url, **kwargs).handle_page()

    def scrape_page(self, page_type, url=None, obj=None, **kwargs):
        return page_type(self, url=url, obj=obj, **kwargs).handle_page()


class NoListItems(Exception):
    pass


class AbstractPage:
    def __init__(self, scraper, url=None, *, obj=None, **kwargs):
        self.scraper = scraper
        if url:
            self.url = url
        self.obj = obj
        self.kwargs = kwargs


class Page(AbstractPage):
    def __init__(self, scraper, url=None, *, obj=None, **kwargs):
        super().__init__(scraper, url=url, obj=obj, **kwargs)
        resp = self.do_request()
        self.doc = lxml.html.fromstring(resp.text)
        self.doc.make_links_absolute(self.url)

    def do_request(self):
        return self.scraper.get(self.url)

    def scrape_page_items(self, page_type, url=None, **kwargs):
        """
            creates an instance of ``page_type`` and returns an iterable of
            scraped items
        """
        yield from page_type(self.scraper, url=url, **kwargs).handle_page()

    def scrape_page(self, page_type, url=None, obj=None, **kwargs):
        """
            creates an instance of ``page_type`` that knows about an object
            being built (``obj``)
        """
        return page_type(self.scraper, url=url, obj=obj, **kwargs).handle_page()

    def handle_list_item(self, item):
        """
            override handle_list_item for scrapers that iterate over

            return values
        """
        raise NotImplementedError()

    def handle_page(self):
        n = 0
        for item in self.doc.xpath(self.list_xpath):
            n += 1
            processed = self.handle_list_item(item)
            if processed:
                if hasattr(processed, '__iter__'):
                    yield from processed
                else:
                    yield processed
        # if not n:
        #    raise NoListItems('no matches for {} on {}'.format(self.list_xpath, self.url))


class PDF(AbstractPage):
    pdftotext_type = 'text'

    def __init__(self, scraper, url=None, *, obj=None, **kwargs):
        super().__init__(scraper, url=url, obj=obj, **kwargs)

        # open PDF as text
        (path, resp) = self.scraper.urlretrieve(url)
        self.text = self.convert_pdf(path, self.pdftotext_type).decode('utf8')
        self.lines = self.text.split('\n')
        os.remove(path)

    def convert_pdf(self, filename, type):
        commands = {'text': ['pdftotext', '-layout', filename, '-'],
                    'text-nolayout': ['pdftotext', filename, '-'],
                    'xml': ['pdftohtml', '-xml', '-stdout', filename],
                    'html': ['pdftohtml', '-stdout', filename]}
        try:
            pipe = subprocess.Popen(commands[type], stdout=subprocess.PIPE, close_fds=True).stdout
        except OSError as e:
            raise EnvironmentError("error running {}, missing executable? [{}]"
                                   .format(' '.join(commands[type]), e))
        data = pipe.read()
        pipe.close()
        return data
