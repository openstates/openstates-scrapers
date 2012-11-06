import json
import re

from clint.textui import colored
from selenium import webdriver
from batshell import Shell, ShellCommands, command
import logbook

from billy.core import mdb, db


def nth(n, iterable):
    it = iter(iterable)
    for i in xrange(n):
        res = next(it)
    return res


class BillyShell(Shell):
    ps1 = '(billy) '
    banner = colored.yellow('''
_|        _|  _|  _|
_|_|_|        _|  _|  _|    _|
_|    _|  _|  _|  _|  _|    _|
_|    _|  _|  _|  _|  _|    _|
_|_|_|    _|  _|  _|    _|_|_|
                            _|
                        _|_|''')
    banner += colored.cyan('\n\nWelcome to billy shell. '
                           'Type h for a list of commands.')


class BillyCommands(ShellCommands):

    @command()
    def sessions(self):
        '''List sessions for this state.
        '''
        for session in self.metadata['session_details']:
            print session

    @command(aliases=['b'], lex_args=False)
    def bills(self, line):
        '''Search bills in mongo.
        * If the first argument is a mongo spec, return a mongo cursor.
          e.g. `b {"state": "ny"}`
        * If the argument is a mongo id, fetch that bill.
          e.g. `b NYL012345`
        '''
        # Is the first arg a spec? If so, query mongo with it.
        if line.startswith('{') and line.endswith('}'):
            line = json.loads(line)
            return mdb.bills.find(line)

        if re.match(r'[A-Z]{2}B\d+', line):
            return mdb.bills.find_one(line)

    @command(aliases=['l'], lex_args=False)
    def legislators(self, line):
        '''`l {"state": "ny"}`
        * If the first argument is a mongo spec, return a mongo cursor.
        * If the argument is a mongo id, fetch that object.
        '''
        # Is the first arg a spec? If so, query mongo with it.
        if line.startswith('{') and line.endswith('}'):
            line = json.loads(line)
            return mdb.legislators.find(line)

        if re.match(r'[A-Z]{2}L\d+', line):
            return mdb.legislators.find_one(line)

    @command(aliases=['c'], lex_args=False)
    def committees(self, line):
        '''
        * If the first argument is a mongo spec, return a mongo cursor.
        * If the argument is a mongo id, fetch that object.
        '''
        # Is the first arg a spec? If so, query mongo with it.
        if line.startswith('{') and line.endswith('}'):
            line = json.loads(line)
            return mdb.committees.find(line)

        if re.match(r'[A-Z]{2}C\d+', line):
            return mdb.committees.find_one(line)

    @command('pb', lex_args=False)
    def random_bill_public_local(self, argtext=None, cache={}):
        '''Page through bills one at a time.
        '''
        do_query = False
        if argtext is not None:
            do_query = True
            if argtext.startswith('{') and argtext.endswith('}'):
                spec = json.loads(argtext)

        elif not hasattr(self, 'bills_cursor'):
            do_query = True
            spec = {}
        else:
            spec = {}

        if do_query:
            if 'state' not in spec:
                spec['state'] = self.abbr
                cache['state'] = self.abbr

            self.logger.info('Mongo query: %r' % spec)
            self.bills_cursor = mdb.bills.find(spec)

        bill = self.bills_cursor.next()
        self.logger.info(bill['_id'])
        url = 'http://localhost:8000/{abbr}/bills/{session}/{bill_id}/'
        url = url.format(abbr=spec.get('state', cache['state']), **bill)

        # Let user reference with the bill in the shell.
        self.inject(x=bill)

        if not hasattr(self, 'browser'):
            self.browser = webdriver.Firefox()
        self.browser.get(url)


def main():
    import sys
    commands = BillyCommands()
    commands.logger = logbook.Logger('fruitbat')
    metadata = None
    if 1 < len(sys.argv):
        abbr = sys.argv[1]
        commands.abbr = abbr
        metadata = mdb.metadata.find_one(abbr)
        commands.metadata = metadata

    shell = BillyShell(commands=commands)
    if metadata is not None:
        shell.metadata = metadata
    commands.inject(mdb=mdb, db=db)
    shell.interact(banner='')


if __name__ == '__main__':
    main()
