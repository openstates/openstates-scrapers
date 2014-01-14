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
from clint.textui import puts, indent
from clint.textui.colored import red, green, cyan, magenta, yellow

from pymongo import Connection

from categories import categories
from billy.models import db

import batshell
from batshell import command, xsel_enabled

logger = logbook.Logger('bathawk.batshell')
HERE = dirname(abspath(__file__))


class BathawkShell(batshell.Shell):
    '''Beware!
    '''
    ps1 = '(batshell) '
    banner = yellow('''
      _==/           i     i           \==_
     /XX/            |\___/|            \XX\\
   /XXXX\            |XXXXX|            /XXXX\\
  |XXXXXX\_         _XXXXXXX_         _/XXXXXX|
 XXXXXXXXXXXxxxxxxxXXXXXXXXXXXxxxxxxxXXXXXXXXXXX
|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|
 XXXXXX/^^^^"\XXXXXXXXXXXXXXXXXXXXX/^^^^^\XXXXXX
  |XXX|       \XXX/^^\XXXXX/^^\XXX/       |XXX|
    \XX\       \X/    \XXX/    \X/       /XX/
       "\       "      \X/      "       /"
''')
    banner += cyan('\n\nWelcome to bashell. '
                       'Type h for a list of commands.')

    def __init__(self, actions_object, abbr, *args, **kwargs):

        # Initialize a batshell with our bat commands.
        batshell.Shell.__init__(self, commands=BatCommands(actions_object))

        # The stuff below might be better placed on the commands object.
        # Store abbreviations and this state's actions helper object in the shell.
        self.abbr = abbr
        self.actions = actions_object

        # Store the state's categorizer in the shell.
        try:
            actions_module = importlib.import_module('openstates.%s.actions' % abbr)
            categorizer = getattr(actions_module, 'Categorizer', None)
            if categorizer is not None:
                self.locals['categorizer'] = categorizer()
        except ImportError:
            pass


class GameState(dict):
    '''Keep track of the state of the matching game. This is only in its
    own class for organizational reasons.
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

        # My 2.6 linter doesn't doesn't like dict comprehensions...
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


class BatCommands(batshell.ShellCommands):
    '''The commands accessible from the Bathawk shell.
    '''

    def __init__(self, actions):
        batshell.ShellCommands.__init__(self)
        self.actions = actions
        self._test_list = actions.unmatched

        # How many lines to show.
        self.show = 30
        self.matched = []
        self.show_matches_start = 0
        self.show_actions_start = 0

        self.game_state = GameState(actions.unmatched)

    @command('r', lex_args=False)
    def test_regex(self, argtext):
        '''Test a regex to see how many actions match.
        '''
        try:
            rgx = re.compile(argtext)
        except sre_constants.error as e:
            msg = red('Bad regex: ') + green(repr(argtext)) + ' You have failed the bat-test.'
            puts(msg)
            print e
            return

        puts('Testing ' + green(argtext))
        matched = []
        for action in self._test_list:
            m = re.search(argtext, action)
            if m:
                matched.append([action, m])
        if not matched:
            with indent(4, quote=' >'):
                puts(red('Aw, snap!') + ' ' + cyan('No matches found!'))
                return
        self.show_matches_start = 0

        total_matches = len(filter(rgx.search, self.actions.list))

        # Update game state.
        self.game_state['current_rgx'] = argtext
        self.game_state['tested_regexes'].add(argtext)
        self.game_state['match_counts'][argtext] = total_matches

        with indent(4, quote=' >'):
            puts('Found ' + red(total_matches) + ' matches:')
        self._print_matches(matched[:self.show])
        self.matched = matched

        # Copy the pattern to the clipboard.
        if xsel_enabled:
            p = subprocess.Popen(['xsel', '-bi'], stdin=subprocess.PIPE)
            p.communicate(input=argtext)

    @command('sw')
    def switch_test_list(self, target):
        '''Switch the regex tester to test against matched,
        unmatched, or all ('list') actions.
        '''
        if not hasattr(self.actions, target):
            logger.warning("Failure! The argument should be 'matched', "
                           "'unmatched', or 'list' for all actions.")
            return
        self._test_list = getattr(self.actions, target)
        logger.info('Switched regex tester over to %r.' % target)

    def _print_matches(self, matched):
        actions = map(itemgetter(0), matched)
        padding = max(map(len, actions))
        self.printed_matched = matched
        for i, (action, match) in enumerate(matched):
            group = match.group()
            colored_action = action.replace(group, str(green(group)))

            groupdict = match.groupdict()
            vals = [str(cyan(i)).ljust(5),
                    '[%s]' % magenta(self.actions.action_ids[action][-1]),
                    colored_action.ljust(padding),
                    repr(groupdict)]
            puts(' '.join(vals))

    @command('m')
    def show_20_matches(self, line):
        '''Show first 20 matches.
        '''
        search = functools.partial(re.search, self.game_state['current_rgx'])
        text = '\n'.join(filter(search, self.actions.list))
        self.pager(text.encode('utf-8'))

    @command('#')
    def show(self, line):
        '''How many matches or actions to show at a time.
        '''
        number = int(line)
        self.show = number

    @command('a')
    def show_actions(self, line=None):
        '''List the first 10 actions.
        '''
        text = '\n'.join(self.actions.unmatched)
        self.pager(text.encode('utf-8'))

    @command('as')
    def show_actions_sorted(self, line=None):
        '''Show actions in alphabetical order.
        '''
        self.show_actions_start = 0
        text = '\n'.join(sorted(list(self.actions.unmatched)))
        self.pager(text.encode('utf-8'))

    @command('c')
    def categories(self):
        '''Print available openstates action categories.
        '''
        padding = max(map(len, map(itemgetter(0), categories)))
        with indent(4, quote=' >'):
            for i, (category, description) in enumerate(categories):
                i = str(yellow(i)).rjust(5)
                category = green(category.ljust(padding))
                puts('(%s) %s %s' % (i, category, description))

    @command('o')
    def hyperlink(self, index):
        '''Given a number representing an index in the
        most recent display of matches, print a hyperlink
        to the bill on localhost.
        '''
        index = int(index)
        action, groupdict = self.printed_matched[index]
        _id = self.actions.action_ids[action][-1]
        bill = db.bills.find_one({'_all_ids': _id})
        url = 'http:localhost:8000/{state}/bills/{session}/{bill_id}/'.format(**bill)
        colored_url = cyan(url)
        puts('View this bill: ' + colored_url)
        webbrowser.open(url)

    @command('j')
    def bill_json(self, index):
        '''Pretty print the bill's actions json.
        '''
        index = int(index)
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
    def start_game(self):
        '''Resume a saved game.'''
        games = list(self.game_state.db.games.find())
        if games:
            tmpl = '%s: created %s, # regexes: %s'
            with indent(4):
                for i, game in enumerate(games):
                    created = game['created'].strftime('%m/%d/%Y')
                    puts(tmpl % (str(yellow(i)).rjust(5),
                                  green(created),
                                  cyan(str(len(game['regexes'])))
                                  ))
            msg = 'Enter the game number to resume (empty for new game): '
            index = raw_input(msg)
            if not index:
                self.game_state = self.game_state.reset()
                puts(yellow('New game.'))
            else:
                game = games[int(index)]
                self.game_state.load(game)
                msg = 'Resumed saved game %r!'
                puts(yellow(msg % game['created'].strftime('%m/%d/%Y')))
        else:
            puts(yellow('No saved games found. New game.'))

    @command('pg')
    def purge_games(self):
        '''Purge one or more saved games.'''
        games = list(self.game_state.db.games.find())
        if games:
            tmpl = '%s: created %s, # regexes: %s'
            with indent(4):
                for i, game in enumerate(games):
                    created = game['created'].strftime('%m/%d/%Y')
                    puts(tmpl % (str(yellow(i)).rjust(5),
                                  green(created),
                                  cyan(str(len(game['regexes'])))
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
    def show_tested_regexes(self):
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
            puts(tmpl % (str(cyan(i)).rjust(5),
                         str(red(match_count)).rjust(5),
                         green(rgx)))

    @command()
    def save(self):
        '''Manually save the game state'''
        self.game_state.save()

    @command('rs')
    def show_added_regexes(self):
        '''Show added patterns.
        '''
        matched_count = sum(self.game_state['match_counts'].values())
        percent = matched_count / float(len(self.game_state._actions))
        puts(red(percent) + '% matched')
        game_state = self.game_state
        tmpl = '%s: (%s) %s'
        regexes = sorted(game_state['regexes'], key=hash)
        sre_type = type(re.compile(r''))
        for i, rgx in enumerate(regexes):
            if isinstance(rgx, sre_type):
                rgx = '%s  ... flags=%d' % (rgx.pattern, rgx.flags)
            match_count = game_state['match_counts'].get(rgx, '?')
            puts(tmpl % (str(cyan(i)).rjust(5),
                         str(red(match_count)).rjust(5),
                         green(rgx)))

    @command('rp')
    def purge_patterns(self):
        '''Purge regexes from the collections.
        '''
        game_state = self.game_state
        regexes = sorted(game_state['regexes'], key=hash)
        self.show_added_regexes()
        indexes = raw_input('Enter numbers of regexes to purge: ')
        indexes = map(int, indexes.split())
        regexes = map(regexes.__getitem__, indexes)
        for rgx in regexes:
            self.game_state['regexes'] -= set([rgx])
            logger.info('removed regex: %r' % rgx)

    @command('ra')
    def add_regex(self):
        '''Add a regex to the stored regexes.
        '''
        rgx = self.game_state['current_rgx']
        self.game_state['regexes'].add(rgx)
        puts(cyan('Added ') + green(rgx))
        self.game_state.save()

    @command('assoc')
    def assoc_rgx_with_types(self, index=None):
        '''Associate a rgx with action categories.
        '''
        if index is not None:
            index = int(index)
            regex = sorted(self.game_state['regexes'], key=hash)[index]
        else:
            regex = self.game_state['current_rgx']
        self.categories()
        types = raw_input('Type numbers of categories to apply: ')
        types = map(categories.__getitem__, map(int, types.split()))
        types = set(map(itemgetter(0), types))
        self.game_state['types'][regex] |= types
        types = ', '.join(types)
        puts(green(regex) + ' --> ' + yellow(types))

    @command('s')
    def print_summary(self):
        '''Display how many actions are currently matched or not.
        '''
        pprint.pprint(self.game_state)
        # unmatched_len = len(self.actions.unmatched)
        # unmatched = red('%d' % unmatched_len)
        # total_len = len(self.actions.list)
        # total = cyan('%d' % total_len)
        # message = 'There are %s unmatched actions out of %s total actions (%s).'
        # percentage = 1.0 * unmatched_len / total_len
        # percentage = green(percentage)
        # puts(message % (unmatched, total, percentage))

    @command('uu')
    def show_unmatched_actions_unsorted(self):
        '''List the first 10 actions.
        '''
        text = '\n'.join(self.game_state.unmatched_actions())
        self.pager(text.encode('utf-8'))

    @command('u')
    def show_unmatched_actions_sorted(self):
        '''Show actions in alphabetical order.

        To eliminate actions with types from the view, pass a flag (any text).
        '''
        self.show_actions_start = 0
        text = '\n'.join(sorted(list(self.game_state.unmatched_actions())))
        self.pager(text.encode('utf-8'))

    @command('im')
    def import_state_action_rules(self):
        '''Load the rule defs from a state and add them to this
        game's regexes.
        '''
        import importlib
        abbr = self.shell.abbr
        actions = importlib.import_module('openstates.%s.actions' % abbr)
        for rule in actions.Categorizer.rules:
            for rgx in rule.regexes:
                if hasattr(rgx, 'pattern'):
                    rgx = FlagDecompiler.add_flags_to_regex(rgx)
                self.game_state['regexes'].add(rgx)
                self.game_state['types'][rgx] |= rule.types
        rule_count = len(actions.Categorizer.rules)
        puts(yellow('Imported %d rule(s).' % rule_count))

    @command('dump')
    def dump_patterns(self):
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
    def show_breakdown_all(self):
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
        self.pager('\n'.join(actions).encode('utf8'))

    @command('bu')
    def show_breakdown_unmatched(self):
        '''List unmatched actions and show the count for each.
        '''
        counts = collections.Counter(self.game_state.unmatched_actions())
        items = sorted(counts.items(), key=itemgetter(1))
        self.pager('\n'.join(str(count).ljust(5) + action for (action, count) in items).encode('utf8'))

    @command('md')
    def metadata(self):
        pprint.pprint(db.metadata.find_one(self.shell.abbr))

    @command()
    def allcategorized(self, line):
        ret = []
        for action in self.game_state._actions:
            ret.append(self.shell.locals['categorizer'].categorize(action))
        import pdb;pdb.set_trace()


class FlagDecompiler(object):
    '''A helper class to convert compile regexes into strings with
    inline flags. Helpful for editing, dumping regexes as text.
    '''
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

