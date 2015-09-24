from billy.core import db


STATES_TO_PURGE = ['in', 'nm', 'oh', 'or']

for state in STATES_TO_PURGE:
    state = state.lower()

    empty_comms = db.committees.find({
        'state': state,
        'members': {'$size': 0}
    }).count()

    if empty_comms == 0:
        print("No empty committees found in {}".format(state.upper()))

    elif empty_comms > 0:
        raw_input("Found {} empty committees in {}!\n".format(empty_comms, state.upper()) +
                  "  These will be deleted\n" +
                  "  Cancel the script now if you don't want this to happen!\n" +
                  "  Otherwise, hit enter to continue")

        db.committees.remove({
            'state': state,
            'members': {'$size': 0}
        })
