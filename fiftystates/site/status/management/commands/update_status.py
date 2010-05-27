import os
import datetime
import ConfigParser

from fiftystates.site.status.models import StateStatus

from django.core.management.base import NoArgsCommand
from django.conf import settings

from git import Repo
from ostracker.models import Project, Contributor

attributes = {
    'bills': 'getboolean',
    'bill_versions': 'getboolean',
    'sponsors': 'getboolean',
    'legislators': 'getboolean',
    'committees': 'getboolean',
    'actions': 'getboolean',
    'votes': 'getboolean',
    'contact': 'get',
    'executable': 'get',
}

state_abbrevs = ('al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'dc', 'fl',
          'ga', 'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me',
          'md', 'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh',
          'nj', 'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri',
          'sc', 'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy')


def update_status_from_proj(state, proj):
    fname = os.path.join(proj.get_local_repo_dir(), 'scripts',
                         state.state.lower(), 'STATUS')
    if os.path.exists(fname):
        state_name = state.state.lower()
        config = ConfigParser.ConfigParser()
        config.read(fname)
        section = config.sections()[0]
        for key, func in attributes.iteritems():
            if config.has_option(section, key):
                val = getattr(config, func)(section, key)
                setattr(state, key, val)

        # commits
        repo = Repo(proj.get_local_repo_dir())
        commits = list(repo.iter_commits(paths='scripts/' + state_name))
        if commits:
            state.num_commits = len(commits)
            state.latest_commit = datetime.datetime.fromtimestamp(
                commits[0].committed_date)

            for c in commits:
                author = Contributor.objects.lookup(c.author.name,
                                                    c.author.email)
                state.contributors.add(author)

    return state


class Command(NoArgsCommand):
    help = 'Updates project information'

    def handle_noargs(self, **options):
        main_proj = Project.objects.get(host_username='sunlightlabs',
                                        name='fiftystates')

        state_objs = StateStatus.objects.all()

        # create states if they don't exist
        if not state_objs:
            for s in state_abbrevs:
                StateStatus.objects.create(state=s)
            state_objs = StateStatus.objects.all()

        for state in state_objs:
            repos = state.repositories.all()
            if repos:
                state = update_status_from_proj(state, repos[0])
                state.save()
            else:
                state = update_status_from_proj(state, main_proj)
                state.save()
