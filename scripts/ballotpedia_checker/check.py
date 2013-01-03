'''
pip install google-api-python-client
'''
import StringIO
import unicodecsv
import unicodedata
#import logging

import logbook
import lxml.html
import scrapelib
import name_tools

import drive_api

#logger = logging.getLogger('billy.ballotpedia-check')
logger = logbook.Logger('ballotpedia-check')

request_defaults = {
    'timeout': 5.0,
    'headers': {
        'Accept': ('text/html,application/xhtml+xml,application/'
                   'xml;q=0.9,*/*;q=0.8'),
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-us,en;q=0.5',
        'Connection': 'keep-alive',
        },
    'follow_robots': False,
    }

session = scrapelib.Scraper(**request_defaults)


def strip_accents(s):
   return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))


def fetch(url):
    logger.info('session.get %r' % url)
    resp = session.get(url)
    html = strip_accents(resp.text).encode('utf-8')
    doc = lxml.html.fromstring(html)
    doc.make_links_absolute(url)
    return html, doc


def main():
    import sys

    try:
        with open('status.csv') as f:
            doc = f.read()
    except IOError:
        service = drive_api.get_service()
        files = drive_api.retrieve_all_files(service)
        for file_obj in files:
            if file_obj['title'] == u'open states internal status':
                doc = drive_api.download_csv(service, file_obj)
                with open('status.csv', 'w') as f:
                    f.write(doc)
                break

    data = unicodecsv.DictReader(StringIO.StringIO(doc))

    LOWER_LIST = 'lower members list'
    LOWER_BP = 'lower ballotpedia 2012 results'
    UPPER_BP = 'upper ballotpedia 2012 results'
    UPPER_LIST = 'upper members list'

    for row in data:

        if sys.argv[1:] and not set([row['maintainer'], row['abbr']]) & set(sys.argv[1:]):
            continue

        state_passed = True

        if row['scraping again?'] == 'yes':
            pass

        logger.info('')
        logger.info('')
        logger.info('Starting %r - lower' % row['state'])
        lower = row[LOWER_LIST]
        lower_bp = row[LOWER_BP]
        if lower and lower_bp:

            # Get retiring and newly elected names.
            html, doc = fetch(lower_bp)
            elected = doc.xpath(
                '//a[@title="Won"]/preceding-sibling::a/text()')
            retiring = doc.xpath(
                '//*[@id="bodyContent"]/div[4]/table[3]/tr/td[1]/a/text()')

            # Get the actual legislature's page.
            html, doc = fetch(lower)
            html_lower = html.lower()

            logger.info('')
            logger.info('  Testing newly elected legislator names:')
            failed = False
            failcount = 0
            for name in elected:
                name = strip_accents(unicode(name)).encode('utf-8')
                try:
                    forms = name_tools.name_forms(name)
                except:
                    logger.warning("Couldn't get name forms for %r" % name)
                    continue
                for form in forms:
                    if form in html_lower:
                        # logger.info('    -PASS: elected %r found' % name)
                        break
                else:
                    logger.info('    -FAIL: elected %r not found' % name)
                    failed = True
                    failcount += 1
            if failed:
                state_passed = False
                logger.info('')
                msg = '%r lower FAILED: %d elected not found'
                logger.info(msg % (row['state'], failcount))

            logger.info('  Testing retired incumbent names:')
            failed = False
            failcount = True
            for name in retiring:
                name = strip_accents(unicode(name)).encode('utf-8')
                try:
                    forms = name_tools.name_forms(name)
                except:
                    logger.warning("Couldn't get name forms for %r" % name)
                    continue
                for form in forms:
                    if form in html_lower:
                        logger.info('    -FAIL: retiree %r found' % name)
                        failed = True
                        failcount += 1
                else:
                    pass
                    # logger.info('    -PASS: retiree %r not found' % name)
            if failed:
                state_passed = False
                logger.info('')
                msg = '%r lower FAILED: %d retirees found'
                logger.info(msg % (row['state'], failcount))

        logger.info('Starting %r - upper' % row['state'])
        upper = row[UPPER_LIST]
        upper_bp = row[UPPER_BP]
        if upper and upper_bp:

            # Get retiring and newly elected names.
            html, doc = fetch(upper_bp)
            elected = doc.xpath(
                '//a[@title="Won"]/preceding-sibling::a/text()')
            retiring = doc.xpath(
                '//*[@id="bodyContent"]/div[4]/table[3]/tr/td[1]/a/text()')

            # Get the actual legislature's page.
            html, doc = fetch(upper)
            html_lower = html.lower()

            logger.info('')
            logger.info('  Testing newly elected legislator names:')
            failed = False
            failcount = True
            for name in elected:
                name = strip_accents(unicode(name)).encode('utf-8')
                try:
                    forms = name_tools.name_forms(name)
                except:
                    logger.warning("Couldn't get name forms for %r" % name)
                    continue
                for form in forms:
                    if form in html_lower:
                        # logger.info('    -PASS: elected %r found' % name)
                        break
                else:
                    logger.info('    -FAIL: elected %r not found' % name)
                    failed = True
                    failcount += 1

            logger.info('')
            if failed:
                state_passed = False
                msg = '%r upper FAILED: %d elected not found'
                logger.info(msg % (row['state'], failcount))

            logger.info('  Testing retired incumbent names:')
            failed = False
            for name in retiring:
                name = strip_accents(unicode(name)).encode('utf-8')
                try:
                    forms = name_tools.name_forms(name)
                except:
                    logger.info('    -FAIL: retiree %r found' % name)

                else:
                    pass
                    # logger.info('    -PASS: retiree %r not found' % name)
            if failed:
                state_passed = False
                logger.info('')
                msg = '%r upper FAILED: %d retirees found'
                logger.info(msg % (row['state'], failcount))

        if state_passed:
            logger.critical('%r PASSED. GOOD TO GO.' % row['state'].upper())
        else:
            logger.critical('%r FAILED. No dice.' % row['state'].upper())

        import pdb;pdb.set_trace()









if __name__ == '__main__':
    main()

# scraper = scrapelib.Scraper()

# jxn = collections.namedtuple('Jurisdiction', 'upper lower upper_bp lower_bp')

# states = map(jxn._make, [

#     ('')

#     ])
