import glob
import json
import os.path
import datetime

import dateutil.parser

from . import settings


def get_json(state, dtype):
    return [json.load(open(f))
            for f in glob.glob(os.path.join(settings.PUPA_DATA_DIR,
                                            state, dtype + '*'))]


def parse_psuedo_id(pid):
    if pid and pid.startswith('~'):
        return json.loads(pid[1:])


def parse_date(date):
    if not date:
        return None
    parsed = dateutil.parser.parse(date)
    if (parsed.tzinfo is None and
            parsed == datetime.datetime(parsed.year, parsed.month, parsed.day)):
        return parsed.date()
    return parsed
