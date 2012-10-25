# -*- coding: utf-8 -*-
import re
import pydoc
import types
import copy
import pprint
import itertools
import sre_constants
import webbrowser
import subprocess
import functools
import collections
import pprint
import datetime
import importlib
from code import InteractiveConsole
from operator import itemgetter
from os.path import abspath, dirname, join

import logbook
from clint.textui import puts, indent, colored
from clint.textui.colored import red, green, cyan, magenta, yellow

from pymongo import Connection

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


class GameState(dict):
    '''Keep track of the state of the matching game.
    '''

    def __init__(self, actions_unmatched):

        self.db = Connection().bathawk

        self['created'] = datetime.datetime.now()

        self['current_rgx'] = None

        # All the regexes added during this game.
        self['regexes'] = set()

        # Mapping of regexes to matching types.
        self['types'] = collections.defaultdict(set)

        # Keep track of pattens tested so far.
        self['tested_regexes'] = set()

        # Keep track of how many actions each regex matched.
        self['match_counts'] = {}

        # The master actions list for this state.
        self._actions = actions_unmatched

    def save(self):
        data = copy.copy(self)
        data['tested_regexes'] = list(self['tested_regexes'])
        data['regexes'] = list(self['regexes'])
        data['types'] = [(k, list(v)) for (k, v) in self['types'].items()]
        data['match_counts'] = self['match_counts'].items()
        self.db.games.save(data)

    def load(self, game):
        self['_id'] = game['_id']
        self['current_rgx'] = game['current_rgx']
        self['tested_regexes'] = set(game['tested_regexes'])
        self['regexes'] = set(game['regexes'])
        self['match_counts'] = {
            rgx: len(filter(re.compile(rgx).search, self._actions))
            for rgx in self['regexes']
            }
        types = collections.defaultdict(set)
        for k, v in game['types']:
            types[k] = set(v)
        self['types'] = types

    def reset(self):
        return GameState(self._actions)

    def matched_actions(self):
        sre_type = type(re.compile(r''))
        ret = collections.defaultdict(list)
        for action in self._actions:
            for rgx in self['regexes']:
                if isinstance(rgx, sre_type):
                    m = rgx.search(action)
                else:
                    m = re.search(rgx, action)
                if m:
                    ret[rgx].append((action, m))
        return ret

    def unmatched_actions(self):
        sre_type = type(re.compile(r''))
        ret = []
        rgxs = self['regexes']
        for action in self._actions:
            matches = []
            for rgx in self['regexes']:
                if isinstance(rgx, sre_type):
                    m = rgx.search(action)
                else:
                    m = re.search(rgx, action)
                if m:
                    matches.append(m)
            if not matches:
                ret.append(action)
        return ret


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

        self.game_state = GameState(actions.unmatched)

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
        self.show_matches_start = 0

        total_matches = len(filter(rgx.search, self.actions.list))

        # Update game state.
        self.game_state['current_rgx'] = line
        self.game_state['tested_regexes'].add(line)
        self.game_state['match_counts'][line] = total_matches

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
        search = functools.partial(re.search, self.game_state['current_rgx'])
        text = '\n'.join(filter(search, self.actions.list))
        pager(text)

    @command('#')
    def show(self, line):
        '''How many matches or actions to show at a time.
        '''
        number = int(line)
        self.show = number

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
        text = '\n'.join(self.actions.unmatched)
        pager(text)

    @command('as')
    def show_actions_sorted(self, line):
        '''Show actions in alphabetical order.
        '''
        self.show_actions_start = 0
        text = '\n'.join(sorted(list(self.actions.unmatched)))
        pager(text)

    @command('q')
    def quit(self, line):
        '''Quit the batshell. You have failed!
        '''
        import sys
        sys.exit(1)

    @command('c')
    def categories(self, line=None):
        '''Print available openstates action categories.
        '''
        padding = max(map(len, map(itemgetter(0), categories)))
        with indent(4, quote=' >'):
            for i, (category, description) in enumerate(categories):
                i = str(colored.yellow(i)).rjust(5)
                category = colored.green(category.ljust(padding))
                puts('(%s) %s %s' % (i, category, description))

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

    # -----------------------------------------------------------------------
    # Game commands.
    @command('g')
    def start_mode(self, line):
        '''Resume a saved game.'''
        games = list(self.game_state.db.games.find())
        if games:
            tmpl = '%s: created %s, # regexes: %s'
            with indent(4):
                for i, game in enumerate(games):
                    created = game['created'].strftime('%m/%d/%Y')
                    puts(tmpl % (str(colored.yellow(i)).rjust(5),
                                  colored.green(created),
                                  colored.cyan(str(len(game['regexes'])))
                                  ))
            msg = 'Enter the game number to resume (empty for new game): '
            index = raw_input(msg)
            if not index:
                self.game_state = self.game_state.reset()
                puts(colored.yellow('New game.'))
            else:
                game = games[int(index)]
                self.game_state.load(game)
                msg = 'Resumed saved game %r!'
                puts(colored.yellow(msg % game['created'].strftime('%m/%d/%Y')))
        else:
            puts(colored.yellow('No saved games found. New game.'))

    @command('pg')
    def purge_games(self, line):
        '''Purge one or more saved games.'''
        games = list(self.game_state.db.games.find())
        if games:
            tmpl = '%s: created %s, # regexes: %s'
            with indent(4):
                for i, game in enumerate(games):
                    created = game['created'].strftime('%m/%d/%Y')
                    puts(tmpl % (str(colored.yellow(i)).rjust(5),
                                  colored.green(created),
                                  colored.cyan(str(len(game['regexes'])))
                                  ))
            msg = 'Enter the game number to resume (empty for new game): '
            indexes = map(int, raw_input(msg).split())
            for i in indexes:
                game = games[i]
                self.game_state.db.games.remove(game)
                created = game['created'].strftime('%m/%d/%Y')
                logger.info('removed game %s' % created)
        else:
            puts(colore.red('No games to purge.'))

    @command('rt')
    def show_tested_regexes(self, line):
        '''Show tested patterns.
        '''
        game_state = self.game_state
        tmpl = '%s: (%s) %s'
        regexes = sorted(game_state['tested_regexes'], key=hash)
        sre_type = type(re.compile(r''))
        for i, rgx in enumerate(regexes):
            if isinstance(rgx, sre_type):
                rgx = '%s  ... flags=%d' % (rgx.pattern, rgx.flags)
            match_count = game_state['match_counts'].get(rgx, '?')
            puts(tmpl % (str(colored.cyan(i)).rjust(5),
                         str(colored.red(match_count)).rjust(5),
                         colored.green(rgx)))

    @command()
    def save(self, line):
        '''Manually save the game state'''
        self.game_state.save()

    @command('rs')
    def show_added_regexes(self, line):
        '''Show added patterns.
        '''
        matched_count = sum(self.game_state['match_counts'].values())
        percent = matched_count / float(len(self.game_state._actions))
        puts(colored.red(percent) + '% matched')
        game_state = self.game_state
        tmpl = '%s: (%s) %s'
        regexes = sorted(game_state['regexes'], key=hash)
        sre_type = type(re.compile(r''))
        for i, rgx in enumerate(regexes):
            if isinstance(rgx, sre_type):
                rgx = '%s  ... flags=%d' % (rgx.pattern, rgx.flags)
            match_count = game_state['match_counts'].get(rgx, '?')
            puts(tmpl % (str(colored.cyan(i)).rjust(5),
                         str(colored.red(match_count)).rjust(5),
                         colored.green(rgx)))

    @command('rp')
    def purge_patterns(self, line):
        '''Purge regexes from the collections.
        '''
        game_state = self.game_state
        regexes = sorted(game_state['regexes'], key=hash)
        self.show_added_regexes(line)
        indexes = raw_input('Enter numbers of regexes to purge: ')
        indexes = map(int, indexes.split())
        regexes = map(regexes.__getitem__, indexes)
        for rgx in regexes:
            self.game_state['regexes'] -= set([rgx])
            logger.info('removed regex: %r' % rgx)

    @command('ra')
    def add_regex(self, line):
        '''Add a regex to the stored regexes.
        '''
        rgx = self.game_state['current_rgx']
        self.game_state['regexes'].add(rgx)
        puts(colored.cyan('Added ') + colored.green(rgx))
        self.game_state.save()

    @command('assoc')
    def assoc_rgx_with_types(self, line):
        '''Associate a rgx with action categories.
        '''
        if line:
            index = int(line)
            regex = sorted(self.game_state['regexes'], key=hash)[index]
        else:
            regex = self.game_state['current_rgx']
        self.categories()
        types = raw_input('Type numbers of categories to apply: ')
        types = map(categories.__getitem__, map(int, types.split()))
        types = set(map(itemgetter(0), types))
        self.game_state['types'][regex] |= types
        types = ', '.join(types)
        puts(colored.green(regex) + ' --> ' + colored.yellow(types))

    @command('s')
    def print_summary(self, line):
        '''Display how many actions are currently matched or not.
        '''
        pprint.pprint(self.game_state)
        # unmatched_len = len(self.actions.unmatched)
        # unmatched = colored.red('%d' % unmatched_len)
        # total_len = len(self.actions.list)
        # total = colored.cyan('%d' % total_len)
        # message = 'There are %s unmatched actions out of %s total actions (%s).'
        # percentage = 1.0 * unmatched_len / total_len
        # percentage = colored.green(percentage)
        # puts(message % (unmatched, total, percentage))

    @command('uu')
    def show_unmatched_actions_unsorted(self, line):
        '''List the first 10 actions.
        '''
        text = '\n'.join(self.game_state.unmatched_actions())
        pager(text)

    @command('u')
    def show_unmatched_actions_sorted(self, line):
        '''Show actions in alphabetical order.
        '''
        self.show_actions_start = 0
        text = '\n'.join(sorted(list(self.game_state.unmatched_actions())))
        pager(text)

    @command('im')
    def import_state_action_rules(self, line):
        '''Load the rule defs from a state and add them to this
        game's regexes.
        '''
        import importlib
        actions = importlib.import_module('openstates.%s.actions' % line)
        for rule in actions.Categorizer.rules:
            for rgx in rule.regexes:
                if hasattr(rgx, 'pattern'):
                    rgx = FlagDecompiler.add_flags_to_regex(rgx)
                self.game_state['regexes'].add(rgx)
                self.game_state['types'][rgx] |= rule.types
        rule_count = len(actions.Categorizer.rules)
        puts(colored.yellow('Imported %d rule(s).' % rule_count))

    @command('dump')
    def dump_patterns(self, line):
        '''Dump the accumulated regexs into acopy/pasteable snippet.
        '''
        from billy.scrape.actions import Rule
        rules = []
        regexes = self.game_state['regexes']
        grouper = self.game_state['types'].get
        for types, regexes in itertools.groupby(regexes, grouper):
            rules.append((list(regexes), list(types or [])))

        pprint.pprint(rules)

    @command('b')
    def show_breakdown_all(self, line):
        '''List unmatched actions and show the count for each.
        '''
        unmatched = self.game_state.unmatched_actions()
        counts = collections.Counter(self.game_state._actions)
        items = sorted(counts.items(), key=itemgetter(1))
        actions = []
        for action, count in items:
            if action in unmatched:
                action = '[%s]' % action
            action = str(count).ljust(5) + action
            actions.append(action)
        pager('\n'.join(actions))

    @command('bu')
    def show_breakdown_unmatched(self, line):
        '''List unmatched actions and show the count for each.
        '''
        counts = collections.Counter(self.game_state.unmatched_actions())
        items = sorted(counts.items(), key=itemgetter(1))
        pager('\n'.join(str(count).ljust(5) + action for (action, count) in items))

    @command('md')
    def metadata(self, line):
        return db.metadata.find_one(self.shell.abbr)

    @command()
    def allcategorized(self, line):
        ret = []
        for action in self.game_state._actions:
            ret.append(self.shell.locals['categorizer'].categorize(action))
        import pdb;pdb.set_trace()


class Shell(InteractiveConsole):

    def __init__(self, actions_object, abbr, *args, **kwargs):
        InteractiveConsole.__init__(self, *args, **kwargs)
        self.abbr = abbr
        try:
            actions = importlib.import_module('openstates.%s.actions' % abbr)
            self.locals['categorizer'] = actions.Categorizer()
        except ImportError:
            pass
        self.last_line = None
        self.actions = actions_object
        commands = ShellCommands(actions_object)
        commands.shell = self
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


class FlagDecompiler(object):
    flag_letters = 'IULMXS'
    flag_vals = [getattr(re, flag) for flag in flag_letters]
    letter_to_int = dict(zip(flag_letters, flag_vals))
    int_to_letter = dict(zip(flag_vals, flag_letters.lower()))
    int_to_letters = {}
    for r in range(7):
        for combo in itertools.combinations(flag_vals, r=r):
            letters = frozenset(map(int_to_letter.get, combo))
            int_to_letters[sum(combo)] = letters

    @classmethod
    def add_flags_to_regex(cls, compiled_rgx):
        # Get existing inline flags.
        rgx = compiled_rgx.pattern
        inline_flags = re.search(r'\(\?([iulmxs])\)', rgx)
        if inline_flags:
            inline_flags = set(inline_flags.group(1))

        if compiled_rgx.flags:
            letters = cls.int_to_letters[compiled_rgx.flags]
            if inline_flags:
                letters = set(letters) - inline_flags
                if letters:
                    return '(?%s)%s' % (''.join(letters), rgx)
        return rgx

