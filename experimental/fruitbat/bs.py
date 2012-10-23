import json
import re

from clint.textui import colored
from batshell import Shell, ShellCommands, command

from billy.core import mdb


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


def main():
    shell = BillyShell(commands=BillyCommands())
    shell.interact(banner='')

if __name__ == '__main__':
    main()
