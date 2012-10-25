import sys

from bathawk import BathawkShell
from actions import Actions


def main(_, abbr):
    actions = Actions(abbr)
    shell = BathawkShell(actions, abbr)
    shell.interact(banner='')

if __name__ == '__main__':
    main(*sys.argv)
