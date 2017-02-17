import glob
import json
import os.path
from . import settings


def get_json(state, dtype):
    return [json.load(open(f))
            for f in glob.glob(os.path.join(settings.PUPA_DATA_DIR,
                                            state, dtype+'*'))]


def parse_psuedo_id(pid):
    if pid and pid.startswith('~'):
        return json.loads(pid[1:])
