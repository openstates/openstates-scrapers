import sys

from clint.textui import puts, colored

from batshell import Shell
from actions import Actions


def main(_, abbr):
    try:
        patterns_module = __import__(abbr)
    except:
        patterns_module = None
    actions = Actions(abbr, patterns_module)
    sys.ps1 = '(batshell) '
    banner = colored.yellow('''
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
    banner += colored.cyan('\n\nWelcome to bashell. '
                           'Type h for a list of commands.')
    shell = Shell(actions)
    import readline
    puts(banner)
    shell.interact(banner='')

if __name__ == '__main__':
    import sys
    main(*sys.argv)
