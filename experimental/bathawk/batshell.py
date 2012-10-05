# -*- coding: utf-8 -*-
import re
import pydoc
import types
import pprint
import itertools
import sre_constants
import webbrowser
import subprocess
import functools
from code import InteractiveConsole
from operator import itemgetter
from os.path import abspath, dirname, join

import logbook
from clint.textui import puts, indent, colored
from clint.textui.colored import red, green, cyan, magenta, yellow

from categories import categories
from billy.models import db


logger = logbook.Logger('bathawk.batshell')
HERE = dirname(abspath(__file__))
pager = pydoc.getpager()

try:
    subprocess.check_call("echo 'test' | xsel -pi", shell=True)
except subprocess.CalledProcessError:
    xsel_enabled = False
    logger.warning(u'✄ Proceeding without xsel ☹')
    logger.info('Please install xsel to automatically '
                'copy tested regexes to the clipboard.')
else:
    xsel_enabled = True
    logger.info(u'✄ xsel is enabled! ☺')


def command(*aliases):
    def decorator(f):
        f.is_command = True
        f.aliases = aliases
        return f
    return decorator


class ShellCommands(object):

    def __init__(self, actions):
        self.actions = actions
        self._test_list = actions.unmatched
        self.command_map = self.as_map()

        # How many lines to show.
        self.show = 30
        self.matched = []
        self.show_matches_start = 0
        self.show_actions_start = 0

    def as_map(self):
        commands = {}
        for name in dir(self):
            attr = getattr(self, name)
            if getattr(attr, 'is_command', False):
                commands[name] = attr
                if isinstance(attr, types.MethodType):
                    for alias in getattr(attr, 'aliases', []):
                        commands[alias] = attr
        return commands

    @command('w')
    def write_regex(self, line):
        '''Save the specified (or last used) regex to the state's
        flat file.
        '''
        # Which regex to save.
        if line:
            rgx = line
        else:
            rgx = self.current_rgx

        # Where to save it.
        filename = '%s.rgx.txt' % self.actions.abbr
        filename = join(HERE, filename)

        with open(filename, 'a') as f:
            f.write('\r' + rgx)
        msg = 'Wrote %s to file: %s'
        puts(msg % (colored.green(rgx), colored.cyan(filename)))

        # Now filter the existing unmatched actions by this pattern.

    @command('r')
    def test_regex(self, line):
        '''Test a regex to see how many actions match.
        '''
        try:
            rgx = re.compile(line)
        except sre_constants.error as e:
            msg = red('Bad regex: ') + green(repr(line)) + ' You have failed the bat-test.'
            puts(msg)
            print e
            return
        self.current_rgx = rgx
        puts('Testing ' + colored.green(line))
        matched = []
        for action in self._test_list:
            m = re.search(line, action)
            if m:
                matched.append([action, m.groupdict()])
        if not matched:
            with indent(4, quote=' >'):
                puts(red('Aw, snap!') + ' ' + cyan('No matches found!'))
                return
        self.current_rgx = line
        self.show_matches_start = 0

        total_matches = len(filter(rgx.search, self.actions.list))

        with indent(4, quote=' >'):
            puts('Found ' + colored.red(total_matches) + ' matches:')
        self._print_matches(matched[:self.show])
        self.matched = matched

        # Copy the pattern to the clipboard.
        if xsel_enabled:
            p = subprocess.Popen(['xsel', '-bi'], stdin=subprocess.PIPE)
            p.communicate(input=line)

    @command('i')
    def inspect(self, line):
        '''In case you want to look inside the shell's guts.
        '''
        import pdb;pdb.set_trace()

    @command('sw')
    def swtich_test_list(self, line):
        '''Switch the regex tester to test against matched,
        unmatched, or all ('list') actions.
        '''
        if not hasattr(self.actions, line):
            logger.warning("Failure! The argument should be 'matched', "
                           "'unmatched', or 'list' for all actions.")
            return
        self._test_list = getattr(self.actions, line)
        logger.info('Switched regex tester over to %r.' % line)

    def _print_matches(self, matched):
        actions = map(itemgetter(0), matched)
        padding = max(map(len, actions))
        self.printed_matched = matched
        for i, action_groupdict in enumerate(matched):
            action, groupdict = action_groupdict
            vals = [str(cyan(i)).ljust(5),
                    '[%s]' % magenta(self.actions.action_ids[action][-1]),
                    action.ljust(padding),
                    repr(groupdict)]
            puts(' '.join(vals))

    @command('m')
    def show_20_matches(self, line):
        '''Show first 20 matches.
        '''
        search = functools.partial(re.search, self.current_rgx)
        text = '\n'.join(filter(search, self.actions.list))
        pager(text)

    @command('s')
    def show(self, line):
        '''How many matches or actions to show at a time.
        '''
        number = int(line)
        self.show_matches_start = number

    @command('h')
    def help(self, line=None):
        '''Show help on the specified commands, otherwise a list of commands.
        '''
        if line:
            command = self.command_map[line]
            help(command)
        else:
            command_map = self.command_map

            def fmt(cmd):
                command_name = green(cmd.__name__)
                aliases = yellow(', '.join(cmd.aliases))
                return str('(%s) %s:' % (aliases, command_name))
            commands = {cmd: fmt(cmd) for cmd in command_map.values()}
            for cmd in commands:
                puts(commands[cmd])
                with indent(4):
                    puts(cmd.__doc__)

    @command('a')
    def show_actions(self, line):
        '''List the first 10 actions.
        '''
        self.show_actions_start = 0
        pprint.pprint(list(self.actions.unmatched)[:self.show])

    @command('aa')
    def show_more_actions(self, line):
        '''Show more actions.
        '''
        start = self.show_actions_start
        end = start + self.show * 5
        pprint.pprint(list(self.actions.unmatched)[start:end])
        self.show_actions_start = end

    @command('as')
    def show_actions_sorted(self, line):
        '''Show actions in alphabetical order.
        '''
        self.show_actions_start = 0
        actions = sorted(list(self.actions.unmatched))
        pprint.pprint(actions[:self.show])

    @command('aas')
    def show_more_actions(self, line, cache={}):
        '''Show more sorted actions.
        '''
        try:
            actions = itertools.islice(cache['actions'], 50)
            actions = list(actions)
            if not actions:
                actions = iter(self._test_list)
                cache['actions'] = actions
                actions = itertools.islice(actions, 50)
                actions = list(actions)
        except KeyError, StopIteration:
            actions = iter(self._test_list)
            cache['actions'] = actions
            actions = itertools.islice(actions, 50)
            actions = list(actions)
        actions = sorted(list(actions))
        pprint.pprint(actions)

    @command('q')
    def quit(self, line):
        '''Quit the batshell. You have failed!
        '''
        import sys
        sys.exit(1)

    @command('c')
    def categories(self, line):
        '''Print available openstates action categories.
        '''
        padding = max(map(len, map(itemgetter(0), categories)))
        with indent(4, quote=' >'):
            for category, description in categories:
                category = colored.green(category.ljust(padding))
                puts(category + ' %s' % description)

    @command('pt')
    def show_patterns(self, line):
        '''Display the regex patterns found in the patterns module.
        '''
        # if line:
        #     offset = int(line)
        #     self.test_regex(self.actions.patterns[offset].pattern)
        #     puts(colore.cyan("Enter 'p 3' to test the third pattern, e.g."))

        for i, rgx in enumerate(self.actions.patterns):
            tmpl = '%s: %s'
            puts(tmpl % (str(colored.cyan(i)).rjust(5), colored.green(rgx.pattern)))

    @command('s')
    def print_summary(self, line):
        '''Display how many actions are currently matched or not.
        '''
        unmatched_len = len(self.actions.unmatched)
        unmatched = colored.red('%d' % unmatched_len)
        total_len = len(self.actions.list)
        total = colored.cyan('%d' % total_len)
        message = 'There are %s unmatched actions out of %s total actions (%s).'
        percentage = 1.0 * unmatched_len / total_len
        percentage = colored.green(percentage)
        puts(message % (unmatched, total, percentage))

    @command('o')
    def hyperlink(self, line):
        '''Given a number representing an index in the
        most recent display of matches, print a hyperlink
        to the bill on localhost.
        '''
        index = int(line)
        action, groupdict = self.printed_matched[index]
        _id = self.actions.action_ids[action][-1]
        bill = db.bills.find_one({'_all_ids': _id})
        url = 'http:localhost:8000/{state}/bills/{session}/{bill_id}/'.format(**bill)
        colored_url = cyan(url)
        puts('View this bill: ' + colored_url)
        webbrowser.open(url)

    @command('j')
    def bill_json(self, line):
        '''Pretty print the bill's actions json.
        '''
        index = int(line)
        action, groupdict = self.printed_matched[index]
        _id = self.actions.action_ids[action][-1]
        bill = db.bills.find_one({'_all_ids': _id})
        url = 'http:localhost:8000/{state}/bills/{session}/{bill_id}/'.format(**bill)
        colored_url = cyan(url)
        puts('View this bill: ' + colored_url)
        pprint.pprint(bill['actions'])


class Shell(InteractiveConsole):

    def __init__(self, actions_object, *args, **kwargs):
        InteractiveConsole.__init__(self, *args, **kwargs)
        self.last_line = None
        self.actions = actions_object
        commands = ShellCommands(actions_object)
        command_map = commands.as_map()
        keys = sorted(command_map, key=len, reverse=True)
        self.command_regex = '^(?P<cmd>%s)(\s+(?P<args>.*))?$' % '|'.join(keys)
        self.commands = commands
        self.command_map = command_map

    def push(self, line):

        if not line:
            if not self.last_line:
                return
            line = self.last_line
        self.last_line = line

        # Call the custom command if given.
        m = re.search(self.command_regex, line)
        if m:
            command = m.group('cmd')
            args = m.group('args')
            return self.command_map[m.group(1)](args)

        InteractiveConsole.push(self, line)

    def interact(self, *args, **kwargs):
        try:
            import readline
        except ImportError:
            pass
        InteractiveConsole.interact(self, *args, **kwargs)
