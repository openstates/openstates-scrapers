from fabric.api import run, env, cd, sudo, get

def staging():
    env.hosts = ['ubuntu@greenbelt.sunlightlabs.net']

def production():
    env.hosts = ['ubuntu@columbia.sunlightlabs.net']

def update():
    sudo('cd ~openstates/src/openstates && git pull', user='openstates')

def restart_uwsgi():
    sudo('restart uwsgi')

def restart_nginx():
    sudo('/etc/init.d/nginx restart')

def _venv(cmd):
    sudo('source ~openstates/site-venv/bin/activate && ' + cmd)

def get_legislator_csv(state):
    with cd('/tmp/'):
        _venv('~openstates/src/openstates/billy/bin/dump_legislator_csv.py ' +
              state)
        get('/tmp/%s_legislators.csv' % state, '%s_legislators.csv' % state)

def get_leg_ids_csv(state):
    with cd('/tmp/'):
        _venv('~openstates/src/openstates/billy/bin/dump_missing_leg_ids.py ' +
              state)
        get('/tmp/%s_missing_leg_ids.csv' % state,
            '%s_missing_leg_ids.csv' % state)

def dump_json(state):
    with cd('/tmp/'):
        _venv('~openstates/src/openstates/billy/bin/dump_json.py --upload ' +
              state)
