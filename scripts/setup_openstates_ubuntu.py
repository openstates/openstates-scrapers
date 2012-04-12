'''
This script sets up a virtualenv with openstates on ubunt.

usage: python setup_openstates_ubuntu.py myvirtualenv [whenIputmycode]

If you don't specify a second argument, the code goes in the virtualenv.
'''
import sys
import os
from os import chdir as cd
from os.path import join, abspath
import subprocess
import logging

# Logging config
logger = logging.getLogger('[openstates-installer]')
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
formatter = logging.Formatter('%(name)s %(asctime)s - %(message)s',
                              datefmt='%H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)


packages = {

    # The packages are required for use of lxml and git.
    'core': '''
        libxml2-dev
        python-dev
        libxslt1-dev
        git'''.split(),
        
    }

# ---------------------------------------------------------------------------
# Utility functions

def run(command, check=False):
    logger.info('running "%s"' % command)
    if check:
        return subprocess.check_output(command, shell=True)
    else:
        subprocess.call(command, shell=True)


def run_each(*commands):
    for c in commands:
        run(c)


def package_install(package, update=False):
    """Installs the given package/list of package, optionnaly updating
    the package database."""
    if update:
        run("sudo apt-get --yes update")
    if type(package) in (list, tuple):
        package = " ".join(package)
    run("sudo apt-get --yes install %s" % (package))


def package_ensure(package):
    """Tests if the given package is installed, and installes it in
    case it's not already there. Loosely stolen from cuisine."""
    cmd = "dpkg-query -W -f='${Status}' %s ; true"
    status = run(cmd % package, check=True)
    if status.find("not-installed") != -1 or status.find("installed") == -1:
        package_install(package)
        return False
    else:
        return True


def create_virtualenv(ENV):
    'Create the virtualenv.'

    run_each(
        ('wget -nc http://pypi.python.org/packages/source/v/virtualenv'
         '/virtualenv-1.7.tar.gz#md5=dcc105e5a3907a9dcaa978f813a4f526'),
        'tar -zxvf virtualenv-1.7.tar.gz ',
        'python virtualenv-1.7/virtualenv.py %s' % ENV,
        )


def gitclone(repo, setup_arg='install'):

    cd(CODE)

    # Clone the code.
    run('git clone %s' % repo)

    # Install requirements.
    _, folder = os.path.split(repo)
    folder, _ = os.path.splitext(folder)
    requirements = join(CODE, folder, 'requirements.txt')
    try:
        with open(requirements):
            pass
    except IOError:
        pass
    else:
        run('%s install -r %s' % (pip, requirements))

    # Setup.
    cd(folder)
    run('%s setup.py %s' % (python, setup_arg))


def setup_openstates():

    for package in packages['core']:
        package_ensure(package)

    create_virtualenv(ENV)

    # Get openstates.
    gitclone('git://github.com/sunlightlabs/openstates.git')

    # Uninstall billy.
    run('%s uninstall billy' % pip)

    # Clone billy, get requirements, and run setup.py develop
    gitclone('git://github.com/sunlightlabs/billy.git', 'develop')


def setup_mysql():
    package_ensure('mysql-server')
    run("sudo apt-get build-dep python-mysqldb")
    run("pip install MySQL-python")
        

if __name__ == "__main__":

    try:
        ENV, CODE = map(abspath, sys.argv[1:3])
    except ValueError:
        ENV = CODE = abspath(sys.argv[1])

    for path in [ENV, CODE]:
        try:
            os.makedirs(ENV)
            os.makedirs(CODE)
        except OSError:
            pass

    pip = join(ENV, 'bin', 'pip')
    python = join(ENV, 'bin', 'python')

    setup_openstates()


