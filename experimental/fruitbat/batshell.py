# -*- coding: utf-8 -*-
import re
import sys
import pdb
import pydoc
import copy
import shlex
import types
import pprint
import itertools
import sre_constants
import webbrowser
import subprocess
import traceback
from code import InteractiveConsole
from operator import itemgetter
from os.path import abspath, dirname, join

import logbook
from clint.textui import puts, indent, colored
from clint.textui.colored import red, green, cyan, magenta, yellow

logger = logbook.Logger('batshell')
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


def command(*aliases, **kwargs):
    def decorator(f):
        f.is_command = True
        f.aliases = aliases or kwargs.get('aliases', [])
        f.lex_args = kwargs.get('lex_args', True)
        return f
    return decorator


class ShellCommands(object):

    def __init__(self):
        self.command_map = self.as_map()

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

    @command('h')
    def help(self, command_name=None):
        '''Show help on the specified commands, otherwise a list of commands.
        '''
        if command_name:
            command = self.command_map[command_name]
            help(command)
        else:
            command_map = self.command_map

            def fmt(cmd):
                command_name = green(cmd.__name__)
                aliases = yellow(', '.join(cmd.aliases))
                return str('(%s) %s:' % (aliases, command_name))
            commands = {cmd: fmt(cmd) for cmd in command_map.values()}
            shame = red('[No docstring found. For shame!]')
            for cmd in commands:
                puts(commands[cmd])
                with indent(4):
                    docstring = cmd.__doc__ or shame
                    puts(docstring)

    @command('i')
    def inspect(self):
        '''In case you want to look inside the shell's guts.
        '''
        pdb.set_trace()

    @command('q')
    def quit(self):
        '''Quit the batshell. You have failed!
        '''
        import sys
        sys.exit(1)

    @command(aliases=['pp'], lex_args=False)
    def prettyprint(self, expression):
        '''Pretty print something--can handle expressions:
        >>> pp 1 + 3, "cow"
        '''
        mylocals = copy.copy(self.shell.locals)
        exec 'print_val = ' + expression in mylocals
        pprint.pprint(mylocals['print_val'])

    def inject(self, **kwargs):
        '''Inject vars into the shell's local scope.
        '''
        self.shell.locals.update(**kwargs)


class Shell(InteractiveConsole):

    ps1 = None

    def __init__(self, commands=None, *args, **kwargs):
        InteractiveConsole.__init__(self, *args, **kwargs)
        self.last_line = None
        if commands is None:
            commands = ShellCommands()

        # Keep a references to the shell on the commands.
        commands.shell = self
        command_map = commands.as_map()
        keys = sorted(command_map, key=len, reverse=True)
        self.command_regex = '^(?P<cmd>%s)(\s+(?P<args>.*))?$' % '|'.join(keys)
        self.commands = commands
        self.command_map = command_map
        self.logger = logbook.Logger(self.ps1 or 'logger')

    def push(self, line):

        if not line:
            if not self.last_line:
                return
            line = self.last_line
        self.last_line = line

        # Call the custom command if given.
        m = re.search(self.command_regex, line)
        if m:
            command_name = m.group('cmd')
            command = self.command_map[command_name]
            args = []
            if m.group('args') is not None:
                argtext = str(m.group('args'))
                if command.lex_args:
                    # Lex the args text.
                    args += shlex.split(argtext)
                else:
                    # Pass the raw text.
                    args.append(argtext)

            if command_name in ('q', 'quit'):
                return command(*args)

            try:
                ret = command(*args)
            except:
                # The command encountered an error.
                traceback.print_exc(file=sys.stdout)
                return
            else:
                # Command succeeded; inject the result back into the shell.
                if ret:
                    self.locals['ret'] = ret
                    msg = 'Result of function has been assigned to name "ret"'
                    self.logger.info(msg)
            return

        if xsel_enabled:
            p = subprocess.Popen(['xsel', '-bi'], stdin=subprocess.PIPE)
            p.communicate(input=line)

        InteractiveConsole.push(self, line)

    def interact(self, *args, **kwargs):
        sys.ps1 = self.ps1
        puts(self.banner)

        try:
            import readline
        except ImportError:
            pass
        InteractiveConsole.interact(self, *args, **kwargs)
