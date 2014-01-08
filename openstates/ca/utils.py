import collections

import lxml.html


class memoize(dict):
    def __init__(self, func):
        self.func = func
    def __call__(self, *args):
        return self[args]
    def __missing__(self, key):
        result = self[key] = self.func(*key)
        return result


class UrlData(object):
    '''Given a url, its nickname, and a scraper instance,
    provide the parsed lxml doc, the raw html, and the url
    '''
    def __init__(self, name, url, scraper, urls_object):
        '''urls_object is a reference back to the Urls container.
        '''
        self.url = url
        self.name = name
        self.scraper = scraper
        self.urls_object = urls_object

    def __repr__(self):
        return 'UrlData(url=%r)' % self.url

    @memoize
    def text(self):
        text = self.scraper.urlopen(self.url)
        self.urls_object.validate(self.name, self.url, text)
        return text

    @memoize
    def resp(self):
        '''Return the decoded html or xml or whatever. sometimes
        necessary for a quick "if 'page not found' in html:..."
        '''
        return self.text.response

    @memoize
    def doc(self):
        '''Return the page's lxml doc.
        '''
        doc = lxml.html.fromstring(self.text)
        doc.make_links_absolute(self.url)
        return doc

    @memoize
    def xpath(self):
        return self.doc.xpath

    @memoize
    def pdf_to_lxml(self):
        filename, resp = self.scraper.urlretrieve(self.url)
        text = convert_pdf(filename, 'html')
        return lxml.html.fromstring(text)

    @memoize
    def etree(self):
        '''Return the documents element tree.
        '''
        return lxml.etree.fromstring(self.text)


class UrlsMeta(type):
    '''This metaclass aggregates the validator functions marked
    using the Urls.validate decorator.
    '''
    def __new__(meta, name, bases, attrs):
        '''Just aggregates the validator methods into a defaultdict
        and stores them on cls._validators.
        '''
        validators = collections.defaultdict(set)
        for attr in attrs.values():
            if hasattr(attr, 'validates'):
                validators[attr.validates].add(attr)
        attrs['_validators'] = validators
        cls = type.__new__(meta, name, bases, attrs)
        return cls


class Urls(object):
    '''Contains urls we need to fetch during this scrape.
    '''
    __metaclass__ = UrlsMeta

    def __init__(self, scraper, urls):
        '''Sets a UrlData object on the instance for each named url given.
        '''
        self.urls = urls
        self.scraper = scraper
        for name, url in urls.items():
            url = UrlData(name, url, scraper, urls_object=self)
            setattr(self, name, url)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.urls)

    def __iter__(self):
        '''A generator of this object's UrlData members.
        '''
        for name in self.urls:
            yield getattr(self, name)

    def add(self, **name_to_url_map):
        for name, url in name_to_url_map.items():
            url_data = UrlData(name, url, self.scraper, urls_object=self)
            self.urls[name] = url
            setattr(self, name, url_data)

    @staticmethod
    def validates(name, retry=False):
        '''A decorator to mark validator functions for use on a particular
        named url. Use like so:

        @Urls.validates('history')
        def must_have_actions(self, url, text):
            'Skip bill that hasn't been introduced yet.'
            if 'no actions yet' in text:
                raise Skip('Bill had no actions yet.')
        '''
        def decorator(method):
            method.validates = name
            method.retry = retry
            return method
        return decorator

    def validate(self, name, url, text):
        '''Run each validator function for the named url and its text.
        '''
        for validator in self._validators[name]:
            try:
                validator(self, url, text)
            except Exception as e:
                if validator.retry:
                    validator(self, url, text)
                else:
                    raise e
