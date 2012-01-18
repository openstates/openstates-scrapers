import re

def get_actor(action_text, chamber, rgxs=(
    (re.compile(r'(in|by) senate', re.I), 'upper'),
    (re.compile(r'(in|by) house', re.I), 'lower'),
    (re.compile(r'by governor', re.I), 'governor'),
    )):
    '''
    Guess the actor for a particular action.
    '''
    for r, actor in rgxs:
        m = r.search(action_text)
        if m:
            return actor
    return chamber

# ----------------------------------------------------------------------------
# Data for action categorization.

_categories = {
    
    # Bill is introduced or prefiled
    "bill:introduced": {
        'rgxs': ['^(?i)introduced'],
        'funcs': {},
        },

    # Bill has passed a chamber
    "bill:passed": {
        'rgxs': ['^(?i)passed'],
        'funcs': {},
        },

    # Bill has failed to pass a chamber
    "bill:failed": {
        'rgxs': ['^(?i)defeated'],
        'funcs': {},
        },

    # ???
    # Bill has been withdrawn from consideration
    "bill:withdrawn": {
        'rgxs': [],
        'funcs': {},
        },

    # ???
    # The chamber attempted a veto override and succeeded
    "bill:veto_override:passed": {
        'rgxs': [],
        'funcs': {},
        },

    # ???
    # The chamber attempted a veto override and failed
    "bill:veto_override:failed": {
        'rgxs': [],
        'funcs': {},
        },

    # ???
    # A bill has undergone its first reading
    "bill:reading:1": {
        'rgxs': [],
        'funcs': {},
        },

    # A bill has undergone its second reading
    "bill:reading:2": {
        'rgxs': [],
        'funcs': {},
        },

    # A bill has undergone its third (or final) reading
    "bill:reading:3": {
        'rgxs': [],
        'funcs': {},
        },

    # A bill has been filed (for states where this is a separate event from bill:introduced)
    "bill:filed": {
        'rgxs': [],
        'funcs': {},
        },

    # A bill has been replaced with a substituted wholesale (called hoghousing in some states)
    "bill:substituted": {
        'rgxs': ['(?i)adopted in lieu of'],
        'funcs': {},
        },

    # The bill has been transmitted to the governor for consideration
    "governor:received": {
        'rgxs': [],
        'funcs': {},
        },

    # The bill has signed into law by the governor
    "governor:signed": {
        'rgxs': ['^(?i)signed'],
        'funcs': {},
        },

    # The bill has been vetoed by the governor
    "governor:vetoed": {
        'rgxs': ['^(?i)vetoed'],
        'funcs': {},
        },

    # The governor has issued a line-item (partial) veto
    "governor:vetoed:line-item": {
        'rgxs': [],
        'funcs': {},
        },

    # An amendment has been offered on the bill
    "amendment:introduced": {
        'rgxs': ['^(?i)amendment.{,200}introduced'],
        'funcs': {},
        },

    # The bill has been amended
    "amendment:passed": {
        'rgxs': ['^(?i)amendment.{,200}passed'],
        'funcs': {},
        },

    # An offered amendment has failed
    "amendment:failed": {
        'rgxs': ['^(?i)amendment.{,200}defeated'],
        'funcs': {},
        },

    # An offered amendment has been amended (seen in Texas)
    "amendment:amended": {
        'rgxs': [],
        'funcs': {},
        },

    # ???
    # An offered amendment has been withdrawn
    "amendment:withdrawn": {
        'rgxs': [],
        'funcs': {},
        },

    # An amendment has been 'laid on the table' (generally
    # preventing further consideration)
    "amendment:tabled": {
        'rgxs': ['^(?i)amendment.{,200}laid on table'],
        'funcs': {},
        },

    # The bill has been referred to a committee
    "committee:referred": {
        'rgxs': ['(?i)assigned'],
        'funcs': {},
        },

    # The bill has been passed out of a committee
    "committee:passed": {
        'rgxs': [r'^(?i)reported out of committee'],
        'funcs': {},
        },

    # ??? Looks like this'd require parsing
    # The bill has been passed out of a committee with a favorable report
    "committee:passed:favorable": {
        'rgxs': [],
        'funcs': {},
        },

    # ??? Looks like this'd require parsing
    # The bill has been passed out of a committee with an unfavorable report
    "committee:passed:unfavorable": {
        'rgxs': [],
        'funcs': {},
        },

    # The bill has failed to make it out of committee
    "committee:failed": {
        'rgxs': [],
        'funcs': {},
        },

    # All other actions will have a type of "other"
    }

_funcs = []
append = _funcs.append
for category, data in _categories.items():
    
    for rgx in data['rgxs']:
        append((category, re.compile(rgx).search))

    for f, args in data['funcs'].items():
        append((category, partial(f, *args)))

def categorize(action, funcs=_funcs):
    '''
    '''
    action = action.strip('" ')
    res = set()
    for category, f in funcs:
        if f(action):
            res.add(category)

    if not res:
        return ('other',)
    
    return tuple(res)
        

actions = [' Necessary rules are suspended in Senate,1',
 '"Adopted in lieu of the original bill HB 101, and assigned to Transportation/Land Use and Infrastructure Committee in House",1',
 '"Adopted in lieu of the original bill HB 143, and assigned to Public Safety & Homeland Security Committee in House",1',
 '"Adopted in lieu of the original bill HB 23, and assigned to Education Committee in House",1',
 '"Adopted in lieu of the original bill HB 33, and assigned to House Administration Committee in House",1',
 '"Adopted in lieu of the original bill HB 4, and assigned to House Administration Committee in House",1',
 '"Adopted in lieu of the original bill HB 57, and assigned to Economic Development/Banking/Insurance/Commerce Committee in House",1',
 '"Adopted in lieu of the original bill HB 58, and assigned to Judiciary Committee in House",1',
 '"Adopted in lieu of the original bill HB 66, and assigned to Public Safety & Homeland Security Committee in House",1',
 '"Adopted in lieu of the original bill HB 88, and assigned to Judiciary Committee in House",1',
 'Amendment HA 1 -  Defeated by House of Representatives. Votes: Defeated   15 YES     23 NO     0 NOT VOTING     3 ABSENT     0 VACANT,1',
 'Amendment HA 1 -  Defeated by House of Representatives. Votes: Defeated   15 YES     23 NO     3 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 1 -  Defeated by House of Representatives. Votes: Defeated   16 YES     24 NO     0 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment HA 1 -  Defeated in House by Voice Vote,1',
 'Amendment HA 1 -  Introduced and Placed With Bill,62',
 'Amendment HA 1 -  Introduced in House,12',
 'Amendment HA 1 -  Laid On Table in House,2',
 'Amendment HA 1 -  Lifted From Table in House,1',
 'Amendment HA 1 -  Passed by House of Representatives. Votes: Passed   21 YES     17 NO     1 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Amendment HA 1 -  Passed in House by Voice Vote,52',
 'Amendment HA 1 -  Stricken,4',
 'Amendment HA 1 Introduced and Placed With Bill,3',
 'Amendment HA 1 Introduced in House,2',
 'Amendment HA 1 Passed in House by Voice Vote,4',
 'Amendment HA 1 defeated,4',
 'Amendment HA 1 to HA 1 -  Introduced and Placed With Bill,4',
 'Amendment HA 1 to HA 1 -  Introduced in House,1',
 'Amendment HA 1 to HA 1 -  Passed in House by Voice Vote,4',
 'Amendment HA 1 to HA 1 -  Stricken,1',
 'Amendment HA 1 to HA 2 -  Introduced and Placed With Bill,1',
 'Amendment HA 1 to HA 2 -  Introduced in House,1',
 'Amendment HA 1 to HA 2 -  Passed in House by Voice Vote,1',
 'Amendment HA 1 to HA 3 -  Introduced in House,1',
 'Amendment HA 1 to HA 3 -  Passed by House of Representatives. Votes: Passed   22 YES     16 NO     1 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Amendment HA 1 to HA 7 -  Introduced in House,1',
 'Amendment HA 1 to HA 7 -  Passed in House by Voice Vote,1',
 'Amendment HA 10 -  Defeated by House of Representatives. Votes: Defeated   1 YES     35 NO     4 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment HA 10 -  Introduced in House,1',
 'Amendment HA 10 defeated,1',
 'Amendment HA 11 -  Defeated by House of Representatives. Votes: Defeated   14 YES     27 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 11 -  Introduced in House,1',
 'Amendment HA 11 defeated,1',
 'Amendment HA 2 -  Defeated by House of Representatives. Votes: Defeated   16 YES     23 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 2 -  Defeated by House of Representatives. Votes: Defeated   17 YES     24 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 2 -  Defeated by House of Representatives. Votes: Defeated   18 YES     20 NO     0 NOT VOTING     3 ABSENT     0 VACANT,1',
 'Amendment HA 2 -  Introduced and Placed With Bill,13',
 'Amendment HA 2 -  Introduced in House,5',
 'Amendment HA 2 -  Laid On Table in House,1',
 'Amendment HA 2 -  Passed by House of Representatives. Votes: Passed   24 YES     17 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 2 -  Passed in House by Voice Vote,7',
 'Amendment HA 2 -  Stricken,2',
 'Amendment HA 2 defeated,3',
 'Amendment HA 2 to HA 1 -  Introduced in House,1',
 'Amendment HA 2 to HA 1 -  Passed in House by Voice Vote,1',
 'Amendment HA 3 -  Defeated by House of Representatives. Votes: Defeated   17 YES     24 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 3 -  Defeated in House by Voice Vote,1',
 'Amendment HA 3 -  Introduced and Placed With Bill,6',
 'Amendment HA 3 -  Introduced in House,3',
 'Amendment HA 3 -  Passed in House by Voice Vote,4',
 'Amendment HA 3 -  Stricken,1',
 'Amendment HA 3 defeated,2',
 'Amendment HA 3 to HA 1 -  Defeated in House by Voice Vote,1',
 'Amendment HA 3 to HA 1 -  Introduced in House,1',
 'Amendment HA 3 to HA 1 defeated,1',
 'Amendment HA 4 -  Defeated by House of Representatives. Votes: Defeated   17 YES     24 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 4 -  Defeated by House of Representatives. Votes: Defeated   18 YES     22 NO     0 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment HA 4 -  Introduced and Placed With Bill,3',
 'Amendment HA 4 -  Introduced in House,1',
 'Amendment HA 4 -  Stricken,2',
 'Amendment HA 4 defeated,2',
 'Amendment HA 5 -  Defeated by House of Representatives. Votes: Defeated   17 YES     24 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 5 -  Defeated in House by Voice Vote,1',
 'Amendment HA 5 -  Introduced and Placed With Bill,2',
 'Amendment HA 5 -  Introduced in House,2',
 'Amendment HA 5 -  Laid On Table in House,1',
 'Amendment HA 5 -  Passed in House by Voice Vote,1',
 'Amendment HA 5 -  Stricken,1',
 'Amendment HA 5 defeated,2',
 'Amendment HA 6 -  Defeated in House by Voice Vote,1',
 'Amendment HA 6 -  Introduced and Placed With Bill,2',
 'Amendment HA 6 -  Passed by House of Representatives. Votes: Passed   23 YES     17 NO     0 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment HA 6 defeated,1',
 'Amendment HA 7 -  Defeated by House of Representatives. Votes: Defeated   15 YES     24 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 7 -  Introduced and Placed With Bill,2',
 'Amendment HA 7 -  Passed by House of Representatives. Votes: Passed   23 YES     17 NO     0 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment HA 7 defeated,1',
 'Amendment HA 8 -  Defeated by House of Representatives. Votes: Defeated   3 YES     25 NO     13 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 8 -  Introduced and Placed With Bill,1',
 'Amendment HA 8 -  Introduced in House,1',
 'Amendment HA 8 -  Stricken,1',
 'Amendment HA 8 defeated,1',
 'Amendment HA 9 -  Defeated by House of Representatives. Votes: Defeated   16 YES     24 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment HA 9 -  Defeated in House by Voice Vote,1',
 'Amendment HA 9 -  Introduced in House,2',
 'Amendment HA 9 defeated,2',
 'Amendment SA 1  Introduced in Senate,1',
 'Amendment SA 1 -   Introduced in Senate,41',
 'Amendment SA 1 -   Laid On Table in Senate,1',
 'Amendment SA 1 -  Defeated by Senate. Votes: Defeated   1 YES     14 NO     5 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Defeated by Senate. Votes: Defeated   2 YES     12 NO     5 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Defeated by Senate. Votes: Defeated   3 YES     17 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Defeated by Senate. Votes: Defeated   9 YES     12 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Introduced and Placed With the Bill in Senate,34',
 'Amendment SA 1 -  Laid On Table in Senate,2',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   13 YES     5 NO     2 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   15 YES     0 NO     0 NOT VOTING     6 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   17 YES     0 NO     0 NOT VOTING     4 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   18 YES     0 NO     0 NOT VOTING     3 ABSENT     0 VACANT,3',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   18 YES     0 NO     3 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   18 YES     2 NO     0 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   18 YES     3 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   19 YES     0 NO     0 NOT VOTING     2 ABSENT     0 VACANT,7',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   19 YES     0 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   20 YES     0 NO     0 NOT VOTING     1 ABSENT     0 VACANT,13',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   20 YES     0 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   20 YES     1 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 1 -  Passed by Senate. Votes: Passed   21 YES     0 NO     0 NOT VOTING     0 ABSENT     0 VACANT,21',
 'Amendment SA 1 -  Stricken,12',
 'Amendment SA 1 Introduced and Placed With the Bill in Senate,1',
 'Amendment SA 1 Passed by Senate. Votes: Passed   21 YES     0 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 1 defeated,4',
 'Amendment SA 2 -   Introduced in Senate,11',
 'Amendment SA 2 -  Defeated by Senate. Votes: Defeated   6 YES     12 NO     1 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Amendment SA 2 -  Defeated by Senate. Votes: Defeated   8 YES     12 NO     0 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment SA 2 -  Introduced and Placed With the Bill in Senate,7',
 'Amendment SA 2 -  Passed by Senate. Votes: Passed   19 YES     0 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Amendment SA 2 -  Passed by Senate. Votes: Passed   20 YES     0 NO     0 NOT VOTING     1 ABSENT     0 VACANT,6',
 'Amendment SA 2 -  Passed by Senate. Votes: Passed   20 YES     1 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 2 -  Passed by Senate. Votes: Passed   21 YES     0 NO     0 NOT VOTING     0 ABSENT     0 VACANT,4',
 'Amendment SA 2 -  Stricken,3',
 'Amendment SA 2 Introduced and Placed With the Bill in Senate,1',
 'Amendment SA 2 Stricken,2',
 'Amendment SA 2 defeated,2',
 'Amendment SA 3  Introduced in Senate,1',
 'Amendment SA 3 -   Introduced in Senate,3',
 'Amendment SA 3 -  Defeated by Senate. Votes: Defeated   10 YES     9 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 3 -  Passed by Senate. Votes: Passed   19 YES     2 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 3 -  Stricken,1',
 'Amendment SA 3 Passed by Senate. Votes: Passed   20 YES     0 NO     0 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Amendment SA 3 defeated,1',
 'Amendment SA 4 -   Introduced in Senate,3',
 'Amendment SA 4 -  Passed by Senate. Votes: Passed   13 YES     8 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 4 -  Passed by Senate. Votes: Passed   19 YES     0 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Amendment SA 4 -  Passed by Senate. Votes: Passed   19 YES     0 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Amendment SA 5 -  Introduced and Placed With the Bill in Senate,1',
 'Amendment SA 5 -  Stricken,1',
 'Assigned to  Committee in Senate,5',
 'Assigned to Administrative Services/Elections Committee in Senate,16',
 'Assigned to Adult & Juvenile Corrections Committee in Senate,1',
 'Assigned to Agriculture Committee in House,2',
 'Assigned to Agriculture Committee in Senate,5',
 'Assigned to Appropriations Committee in House,9',
 'Assigned to Banking Committee in Senate,10',
 'Assigned to Bond Committee in Senate,1',
 'Assigned to Children; Youth & Families Committee in Senate,1',
 'Assigned to Community/County Affairs Committee in Senate,29',
 'Assigned to Education Committee in House,1',
 'Assigned to Education Committee in Senate,12',
 'Assigned to Energy & Transit Committee in Senate,1',
 'Assigned to Energy Committee in House,1',
 'Assigned to Executive Committee in Senate,17',
 'Assigned to Finance Committee in Senate,35',
 'Assigned to Health & Social Services Committee in Senate,22',
 'Assigned to Highways & Transportation Committee in Senate,6',
 'Assigned to House Administration Committee in House,8',
 'Assigned to Housing & Community Affairs Committee in House,1',
 'Assigned to Insurance Committee in Senate,17',
 'Assigned to Judiciary Committee in House,2',
 'Assigned to Judiciary Committee in Senate,51',
 'Assigned to Labor & Industrial Relations Committee in Senate,2',
 'Assigned to Labor Committee in House,2',
 'Assigned to Manufactured Housing Committee in House,1',
 'Assigned to Natural Resources & Environmental Control Committee in Senate,19',
 'Assigned to Natural Resources Committee in House,1',
 'Assigned to Public Safety Committee in Senate,14',
 'Assigned to Revenue & Finance Committee in House,2',
 'Assigned to Revenue & Taxation Committee in Senate,6',
 'Assigned to Small Business Committee in Senate,7',
 'Assigned to Sunset Committee (Policy Analysis & Government Accountability) Committee in House,1',
 'Assigned to Sunset Committee in Senate,16',
 'Assigned to Transportation/Land Use and Infrastructure Committee in House,1',
 'Defeated by House of Representatives. Votes: Defeated   15 YES     15 NO     7 NOT VOTING     4 ABSENT     0 VACANT,1',
 'Defeated by Senate. Votes: Defeated   10 YES     5 NO     5 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Defeated by Senate. Votes: Defeated   10 YES     7 NO     4 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Defeated by Senate. Votes: Defeated   12 YES     7 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Defeated by Senate. Votes: Defeated   5 YES     16 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Defeated by Senate. Votes: Defeated   9 YES     10 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Defeated by Senate. Votes: Defeated   9 YES     9 NO     2 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Enact w/o Sign by Governor,4',
 'Introduced and Assigned to Agriculture Committee in House,2',
 'Introduced and Assigned to Appropriations Committee in House,3',
 'Introduced and Assigned to Corrections Committee in House,2',
 'Introduced and Assigned to Economic Development/Banking/Insurance/Commerce Committee in House,41',
 'Introduced and Assigned to Education Committee in House,18',
 'Introduced and Assigned to Energy Committee in House,2',
 'Introduced and Assigned to Gaming & Parimutuels Committee in House,2',
 'Introduced and Assigned to Health & Human Development Committee in House,20',
 'Introduced and Assigned to House Administration Committee in House,71',
 'Introduced and Assigned to Housing & Community Affairs Committee in House,16',
 'Introduced and Assigned to Judiciary Committee in House,38',
 'Introduced and Assigned to Labor Committee in House,4',
 'Introduced and Assigned to Manufactured Housing Committee in House,3',
 'Introduced and Assigned to Natural Resources Committee in House,19',
 'Introduced and Assigned to Public Safety & Homeland Security Committee in House,29',
 'Introduced and Assigned to Revenue & Finance Committee in House,17',
 'Introduced and Assigned to Sunset Committee (Policy Analysis & Government Accountability) Committee in House,25',
 'Introduced and Assigned to Telecommunication Internet & Technology Committee in House,2',
 'Introduced and Assigned to Transportation/Land Use and Infrastructure Committee in House,9',
 'Introduced in House,47',
 'Introduced in House and assigned to Agriculture Committee,2',
 'Introduced in House and assigned to Appropriations Committee,2',
 'Introduced in House and assigned to Education Committee,1',
 'Introduced in House and assigned to Energy Committee,1',
 'Introduced in House and assigned to House Administration Committee,8',
 'Introduced in House and assigned to Housing & Community Affairs Committee,1',
 'Introduced in House and assigned to Judiciary Committee,2',
 'Introduced in House and assigned to Labor Committee,2',
 'Introduced in House and assigned to Manufactured Housing Committee,1',
 'Introduced in House and assigned to Natural Resources Committee,1',
 'Introduced in House and assigned to Revenue & Finance Committee,2',
 'Introduced in House and assigned to Sunset Committee (Policy Analysis & Government Accountability) Committee,1',
 'Introduced in House and assigned to Transportation/Land Use and Infrastructure Committee,1',
 'Introduced in Senate,45',
 'Laid On Table in House,9',
 'Laid On Table in Senate,10',
 'Lifted From Table in House,8',
 'Lifted From Table in Senate,10',
 'Necessary rules are suspended in ,1',
 'Necessary rules are suspended in House,57',
 'Necessary rules are suspended in Senate,41',
 'Passed by House of Representatives. Votes: Passed   21 YES     19 NO     0 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   21 YES     19 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   22 YES     16 NO     1 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   23 YES     13 NO     3 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   26 YES     10 NO     5 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   26 YES     11 NO     4 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   26 YES     15 NO     0 NOT VOTING     0 ABSENT     0 VACANT,2',
 'Passed by House of Representatives. Votes: Passed   27 YES     12 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   27 YES     12 NO     1 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   27 YES     14 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   28 YES     11 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   28 YES     11 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   28 YES     13 NO     0 NOT VOTING     0 ABSENT     0 VACANT,2',
 'Passed by House of Representatives. Votes: Passed   29 YES     12 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   29 YES     9 NO     1 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   30 YES     7 NO     0 NOT VOTING     4 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   30 YES     8 NO     2 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   31 YES     8 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   32 YES     0 NO     0 NOT VOTING     9 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   32 YES     2 NO     5 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   33 YES     0 NO     7 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   33 YES     6 NO     1 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   33 YES     8 NO     0 NOT VOTING     0 ABSENT     0 VACANT,2',
 'Passed by House of Representatives. Votes: Passed   34 YES     0 NO     0 NOT VOTING     7 ABSENT     0 VACANT,3',
 'Passed by House of Representatives. Votes: Passed   34 YES     4 NO     0 NOT VOTING     3 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   34 YES     5 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   35 YES     0 NO     1 NOT VOTING     5 ABSENT     0 VACANT,2',
 'Passed by House of Representatives. Votes: Passed   35 YES     0 NO     2 NOT VOTING     4 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   35 YES     1 NO     5 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   35 YES     4 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   35 YES     5 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   35 YES     6 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   36 YES     0 NO     0 NOT VOTING     5 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   36 YES     0 NO     2 NOT VOTING     3 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   36 YES     1 NO     0 NOT VOTING     4 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   36 YES     3 NO     1 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   36 YES     5 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   37 YES     0 NO     0 NOT VOTING     4 ABSENT     0 VACANT,12',
 'Passed by House of Representatives. Votes: Passed   37 YES     0 NO     1 NOT VOTING     3 ABSENT     0 VACANT,3',
 'Passed by House of Representatives. Votes: Passed   37 YES     1 NO     0 NOT VOTING     3 ABSENT     0 VACANT,3',
 'Passed by House of Representatives. Votes: Passed   37 YES     2 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   37 YES     3 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   38 YES     0 NO     0 NOT VOTING     3 ABSENT     0 VACANT,30',
 'Passed by House of Representatives. Votes: Passed   38 YES     0 NO     1 NOT VOTING     2 ABSENT     0 VACANT,3',
 'Passed by House of Representatives. Votes: Passed   38 YES     1 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   38 YES     3 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   39 YES     0 NO     0 NOT VOTING     2 ABSENT     0 VACANT,18',
 'Passed by House of Representatives. Votes: Passed   39 YES     0 NO     2 NOT VOTING     0 ABSENT     0 VACANT,4',
 'Passed by House of Representatives. Votes: Passed   39 YES     1 NO     0 NOT VOTING     1 ABSENT     0 VACANT,3',
 'Passed by House of Representatives. Votes: Passed   39 YES     1 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by House of Representatives. Votes: Passed   40 YES     0 NO     0 NOT VOTING     1 ABSENT     0 VACANT,35',
 'Passed by House of Representatives. Votes: Passed   40 YES     0 NO     1 NOT VOTING     0 ABSENT     0 VACANT,6',
 'Passed by House of Representatives. Votes: Passed   40 YES     1 NO     0 NOT VOTING     0 ABSENT     0 VACANT,3',
 'Passed by House of Representatives. Votes: Passed   41 YES     0 NO     0 NOT VOTING     0 ABSENT     0 VACANT,87',
 'Passed by Senate. Votes: Passed   11 YES     5 NO     4 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   11 YES     8 NO     1 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   11 YES     9 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   12 YES     8 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   13 YES     0 NO     0 NOT VOTING     8 ABSENT     0 VACANT,6',
 'Passed by Senate. Votes: Passed   13 YES     4 NO     3 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   13 YES     6 NO     0 NOT VOTING     2 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   13 YES     7 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   14 YES     5 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   14 YES     7 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   15 YES     2 NO     2 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   15 YES     4 NO     1 NOT VOTING     1 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   15 YES     4 NO     2 NOT VOTING     0 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   15 YES     5 NO     0 NOT VOTING     1 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   15 YES     5 NO     1 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   15 YES     6 NO     0 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   16 YES     0 NO     0 NOT VOTING     5 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   16 YES     2 NO     0 NOT VOTING     3 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   16 YES     3 NO     0 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   16 YES     3 NO     1 NOT VOTING     1 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   16 YES     3 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   16 YES     4 NO     0 NOT VOTING     1 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   16 YES     4 NO     1 NOT VOTING     0 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   17 YES     0 NO     2 NOT VOTING     2 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   17 YES     1 NO     1 NOT VOTING     2 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   17 YES     2 NO     1 NOT VOTING     1 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   17 YES     2 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   17 YES     3 NO     0 NOT VOTING     1 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   17 YES     4 NO     0 NOT VOTING     0 ABSENT     0 VACANT,6',
 'Passed by Senate. Votes: Passed   18 YES     0 NO     0 NOT VOTING     3 ABSENT     0 VACANT,13',
 'Passed by Senate. Votes: Passed   18 YES     1 NO     0 NOT VOTING     2 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   18 YES     1 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   18 YES     2 NO     0 NOT VOTING     1 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   18 YES     2 NO     1 NOT VOTING     0 ABSENT     0 VACANT,3',
 'Passed by Senate. Votes: Passed   18 YES     3 NO     0 NOT VOTING     0 ABSENT     0 VACANT,5',
 'Passed by Senate. Votes: Passed   19 YES     0 NO     0 NOT VOTING     2 ABSENT     0 VACANT,21',
 'Passed by Senate. Votes: Passed   19 YES     0 NO     1 NOT VOTING     1 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   19 YES     0 NO     2 NOT VOTING     0 ABSENT     0 VACANT,1',
 'Passed by Senate. Votes: Passed   19 YES     1 NO     0 NOT VOTING     1 ABSENT     0 VACANT,4',
 'Passed by Senate. Votes: Passed   19 YES     1 NO     1 NOT VOTING     0 ABSENT     0 VACANT,2',
 'Passed by Senate. Votes: Passed   19 YES     2 NO     0 NOT VOTING     0 ABSENT     0 VACANT,6',
 'Passed by Senate. Votes: Passed   20 YES     0 NO     0 NOT VOTING     1 ABSENT     0 VACANT,79',
 'Passed by Senate. Votes: Passed   20 YES     0 NO     1 NOT VOTING     0 ABSENT     0 VACANT,3',
 'Passed by Senate. Votes: Passed   20 YES     1 NO     0 NOT VOTING     0 ABSENT     0 VACANT,8',
 'Passed by Senate. Votes: Passed   21 YES     0 NO     0 NOT VOTING     0 ABSENT     0 VACANT,101',
 'Passed in House by Voice Vote,68',
 'Re-Assigned to Agriculture Committee in House,3',
 'Re-Assigned to Economic Development/Banking/Insurance/Commerce Committee in House,1',
 'Re-Assigned to House Administration Committee in House,3',
 'Re-Assigned to Insurance committee in Senate,1',
 'Re-Assigned to Judiciary committee in Senate,1',
 'Re-Assigned to Veterans Affairs Committee in House,1',
 '"Reported Out of Committee (ADMINISTRATIVE SERVICES/ELECTIONS) in Senate with 3 Favorable, 1 On Its Merits",1',
 'Reported Out of Committee (ADMINISTRATIVE SERVICES/ELECTIONS) in Senate with 4 On Its Merits,7',
 'Reported Out of Committee (ADMINISTRATIVE SERVICES/ELECTIONS) in Senate with 5 On Its Merits,6',
 '"Reported Out of Committee (ADULT & JUVENILE CORRECTIONS) in Senate with 4 On Its Merits, 2 Unfavorable",1',
 '"Reported Out of Committee (AGRICULTURE) in House with 4 Favorable, 4 On Its Merits",1',
 'Reported Out of Committee (AGRICULTURE) in House with 5 On Its Merits,3',
 'Reported Out of Committee (AGRICULTURE) in House with 7 Favorable,1',
 'Reported Out of Committee (AGRICULTURE) in House with 7 On Its Merits,1',
 '"Reported Out of Committee (AGRICULTURE) in Senate with 1 Favorable, 1 On Its Merits, 1 Unfavorable",1',
 '"Reported Out of Committee (AGRICULTURE) in Senate with 1 Favorable, 4 On Its Merits",1',
 '"Reported Out of Committee (AGRICULTURE) in Senate with 3 Favorable, 1 On Its Merits",1',
 'Reported Out of Committee (AGRICULTURE) in Senate with 5 Favorable,1',
 'Reported Out of Committee (APPROPRIATIONS) in House with 5 On Its Merits,1',
 'Reported Out of Committee (APPROPRIATIONS) in House with 6 Favorable,1',
 'Reported Out of Committee (APPROPRIATIONS) in House with 6 On Its Merits,1',
 'Reported Out of Committee (BANKING) in Senate with 4 On Its Merits,6',
 'Reported Out of Committee (BANKING) in Senate with 5 On Its Merits,2',
 'Reported Out of Committee (CHILDREN; YOUTH & FAMILIES) in Senate with 5 On Its Merits,1',
 'Reported Out of Committee (COMMUNITY/COUNTY AFFAIRS) in Senate with 1 Favorable 4 On Its Merits,1',
 '"Reported Out of Committee (COMMUNITY/COUNTY AFFAIRS) in Senate with 1 Favorable, 3 On Its Merits",3',
 'Reported Out of Committee (COMMUNITY/COUNTY AFFAIRS) in Senate with 4 On Its Merits,19',
 'Reported Out of Committee (COMMUNITY/COUNTY AFFAIRS) in Senate with 5 On Its Merits,3',
 'Reported Out of Committee (CORRECTIONS) in House with 5 On Its Merits,1',
 'Reported Out of Committee (CORRECTIONS) in House with 6 Favorable,1',
 '"Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 1 Favorable, 10 On Its Merits",1',
 '"Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 1 Favorable, 6 On Its Merits",2',
 '"Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 1 Favorable, 8 On Its Merits",1',
 'Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 10 On Its Merits,2',
 'Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 11 On Its Merits,1',
 '"Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 2 Favorable, 9 On Its Merits",2',
 '"Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 3 Favorable, 4 On Its Merits",2',
 '"Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 3 Favorable, 6 On Its Merits",1',
 '"Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 4 Favorable, 7 On Its Merits",1',
 '"Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 5 Favorable, 3 On Its Merits",1',
 '"Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 6 Favorable, 1 On Its Merits",1',
 'Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 7 On Its Merits,6',
 'Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 8 On Its Merits,3',
 'Reported Out of Committee (ECONOMIC DEVELOPMENT/BANKING/INSURANCE/COMMERCE) in House with 9 On Its Merits,3',
 '"Reported Out of Committee (EDUCATION) in House with 1 Favorable, 10 On Its Merits",2',
 '"Reported Out of Committee (EDUCATION) in House with 1 Favorable, 7 On Its Merits",2',
 'Reported Out of Committee (EDUCATION) in House with 10 On Its Merits,1',
 'Reported Out of Committee (EDUCATION) in House with 14 Favorable,1',
 '"Reported Out of Committee (EDUCATION) in House with 2 Favorable, 9 On Its Merits",1',
 '"Reported Out of Committee (EDUCATION) in House with 3 Favorable, 6 On Its Merits",1',
 '"Reported Out of Committee (EDUCATION) in House with 3 Favorable, 7 On Its Merits",1',
 '"Reported Out of Committee (EDUCATION) in House with 4 Favorable, 5 On Its Merits",1',
 '"Reported Out of Committee (EDUCATION) in House with 5 Favorable, 6 On Its Merits",1',
 '"Reported Out of Committee (EDUCATION) in House with 7 Favorable, 3 On Its Merits",1',
 'Reported Out of Committee (EDUCATION) in House with 8 Favorable,1',
 'Reported Out of Committee (EDUCATION) in House with 9 On Its Merits,2',
 'Reported Out of Committee (EDUCATION) in Senate with 4 On Its Merits,3',
 'Reported Out of Committee (EDUCATION) in Senate with 5 On Its Merits,4',
 'Reported Out of Committee (EDUCATION) in Senate with 6 Favorable,1',
 'Reported Out of Committee (EDUCATION) in Senate with 6 On Its Merits,2',
 'Reported Out of Committee (ENERGY & TRANSIT) in Senate with 5 On Its Merits,1',
 '"Reported Out of Committee (ENERGY) in House with 5 Favorable, 2 On Its Merits",1',
 'Reported Out of Committee (EXECUTIVE) in Senate with 4 On Its Merits,1',
 'Reported Out of Committee (EXECUTIVE) in Senate with 5 On Its Merits,2',
 'Reported Out of Committee (EXECUTIVE) in Senate with 6 On Its Merits,3',
 '"Reported Out of Committee (FINANCE) in Senate with 1 Favorable, 4 On Its Merits",2',
 '"Reported Out of Committee (FINANCE) in Senate with 1 Favorable, 5 On Its Merits",1',
 '"Reported Out of Committee (FINANCE) in Senate with 2 Favorable, 3 On Its Merits",1',
 'Reported Out of Committee (FINANCE) in Senate with 4 On Its Merits,2',
 'Reported Out of Committee (FINANCE) in Senate with 5 On Its Merits,4',
 'Reported Out of Committee (FINANCE) in Senate with 6 On Its Merits,2',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 1 Favorable, 10 On Its Merits",1',
 'Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 10 On Its Merits,1',
 'Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 11 On Its Merits,1',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 2 Favorable, 10 On Its Merits",1',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 2 Favorable, 9 On Its Merits",1',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 4 Favorable, 6 On Its Merits",1',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 5 Favorable, 3 On Its Merits, 1 Unfavorable",1',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 5 Favorable, 4 On Its Merits",1',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 5 Favorable, 5 On Its Merits",1',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 6 Favorable, 5 On Its Merits",1',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 8 Favorable, 1 On Its Merits",1',
 '"Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 8 Favorable, 3 On Its Merits",2',
 'Reported Out of Committee (HEALTH & HUMAN DEVELOPMENT) in House with 8 On Its Merits,2',
 'Reported Out of Committee (HEALTH & SOCIAL SERVICES) in Senate with 4 On Its Merits,1',
 'Reported Out of Committee (HEALTH & SOCIAL SERVICES) in Senate with 5 On Its Merits,8',
 'Reported Out of Committee (HEALTH & SOCIAL SERVICES) in Senate with 6 On Its Merits,7',
 'Reported Out of Committee (HEALTH & SOCIAL SERVICES) in Senate with 7 On Its Merits,1',
 'Reported Out of Committee (HIGHWAYS & TRANSPORTATION) in Senate with 4 On Its Merits,3',
 'Reported Out of Committee (HIGHWAYS & TRANSPORTATION) in Senate with 5 On Its Merits,1',
 '"Reported Out of Committee (HOUSE ADMINISTRATION) in House with 1 Favorable, 3 On Its Merits",2',
 '"Reported Out of Committee (HOUSE ADMINISTRATION) in House with 1 Favorable, 4 On Its Merits",2',
 '"Reported Out of Committee (HOUSE ADMINISTRATION) in House with 2 Favorable, 2 On Its Merits",1',
 'Reported Out of Committee (HOUSE ADMINISTRATION) in House with 3 Favorable,2',
 '"Reported Out of Committee (HOUSE ADMINISTRATION) in House with 3 Favorable, 1 Unfavorable",1',
 '"Reported Out of Committee (HOUSE ADMINISTRATION) in House with 3 Favorable, 2 On Its Merits",3',
 'Reported Out of Committee (HOUSE ADMINISTRATION) in House with 3 On Its Merits,4',
 '"Reported Out of Committee (HOUSE ADMINISTRATION) in House with 4 Favorable, 1 On Its Merits",1',
 '"Reported Out of Committee (HOUSE ADMINISTRATION) in House with 4 Favorable, 1 Unfavorable",1',
 'Reported Out of Committee (HOUSE ADMINISTRATION) in House with 4 On Its Merits,1',
 'Reported Out of Committee (HOUSE ADMINISTRATION) in House with 5 Favorable,3',
 'Reported Out of Committee (HOUSE ADMINISTRATION) in House with 5 On Its Merits,17',
 '"Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 1 Favorable, 6 On Its Merits",1',
 '"Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 1 Favorable, 8 On Its Merits",1',
 '"Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 2 Favorable, 6 On Its Merits",1',
 '"Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 3 Favorable, 4 On Its Merits",1',
 '"Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 3 Favorable, 5 On Its Merits",1',
 '"Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 4 Favorable, 3 On Its Merits",1',
 '"Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 4 Favorable, 4 On Its Merits",1',
 '"Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 5 Favorable, 3 On Its Merits",1',
 'Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 7 On Its Merits,2',
 'Reported Out of Committee (HOUSING & COMMUNITY AFFAIRS) in House with 9 On Its Merits,1',
 '"Reported Out of Committee (INSURANCE) in Senate with 1 Favorable, 4 On Its Merits",1',
 '"Reported Out of Committee (INSURANCE) in Senate with 1 Favorable, 4 On Its Merits, 1 Unfavorable",1',
 '"Reported Out of Committee (INSURANCE) in Senate with 1 Favorable, 5 On Its Merits",1',
 'Reported Out of Committee (INSURANCE) in Senate with 4 On Its Merits,3',
 'Reported Out of Committee (INSURANCE) in Senate with 5 On Its Merits,4',
 '"Reported Out of Committee (INSURANCE) in Senate with 5 On Its Merits, 1 Unfavorable",1',
 'Reported Out of Committee (INSURANCE) in Senate with 6 On Its Merits,3',
 '"Reported Out of Committee (JUDICIARY) in House with 1 Favorable, 5 On Its Merits",2',
 '"Reported Out of Committee (JUDICIARY) in House with 1 Favorable, 6 On Its Merits",1',
 '"Reported Out of Committee (JUDICIARY) in House with 2 Favorable, 4 On Its Merits",2',
 '"Reported Out of Committee (JUDICIARY) in House with 3 Favorable, 3 On Its Merits",1',
 '"Reported Out of Committee (JUDICIARY) in House with 5 On Its Merits, 1 Unfavorable",1',
 'Reported Out of Committee (JUDICIARY) in House with 6 On Its Merits,10',
 'Reported Out of Committee (JUDICIARY) in House with 7 On Its Merits,6',
 'Reported Out of Committee (JUDICIARY) in House with 8 On Its Merits,3',
 'Reported Out of Committee (JUDICIARY) in House with 9 On Its Merits,8',
 'Reported Out of Committee (JUDICIARY) in Senate with 4 On Its Merits,29',
 'Reported Out of Committee (JUDICIARY) in Senate with 5 On Its Merits,6',
 'Reported Out of Committee (LABOR & INDUSTRIAL RELATIONS) in Senate with 3 Favorable,1',
 'Reported Out of Committee (LABOR) in House with 12 On Its Merits,1',
 '"Reported Out of Committee (MANUFACTURED HOUSING) in House with 1 Favorable, 3 On Its Merits",1',
 '"Reported Out of Committee (MANUFACTURED HOUSING) in House with 1 Favorable, 5 On Its Merits",1',
 'Reported Out of Committee (MANUFACTURED HOUSING) in House with 4 On Its Merits,1',
 '"Reported Out of Committee (NATURAL RESOURCES & ENVIRONMENTAL CONTROL) in Senate with 1 Favorable, 4 On Its Merits",1',
 'Reported Out of Committee (NATURAL RESOURCES & ENVIRONMENTAL CONTROL) in Senate with 4 On Its Merits,5',
 'Reported Out of Committee (NATURAL RESOURCES & ENVIRONMENTAL CONTROL) in Senate with 5 On Its Merits,2',
 'Reported Out of Committee (NATURAL RESOURCES & ENVIRONMENTAL CONTROL) in Senate with 6 On Its Merits,5',
 '"Reported Out of Committee (NATURAL RESOURCES) in House with 1 Favorable, 6 On Its Merits",3',
 '"Reported Out of Committee (NATURAL RESOURCES) in House with 1 Favorable, 7 On Its Merits",2',
 'Reported Out of Committee (NATURAL RESOURCES) in House with 10 On Its Merits,1',
 '"Reported Out of Committee (NATURAL RESOURCES) in House with 2 Favorable, 5 On Its Merits",5',
 '"Reported Out of Committee (NATURAL RESOURCES) in House with 5 Favorable, 2 On Its Merits",1',
 '"Reported Out of Committee (NATURAL RESOURCES) in House with 6 Favorable, 1 On Its Merits",1',
 'Reported Out of Committee (NATURAL RESOURCES) in House with 7 Favorable,1',
 'Reported Out of Committee (NATURAL RESOURCES) in House with 7 On Its Merits,1',
 'Reported Out of Committee (NATURAL RESOURCES) in House with 9 On Its Merits,1',
 '"Reported Out of Committee (PUBLIC SAFETY & HOMELAND SECURITY) in House with 1 Favorable, 5 On Its Merits",1',
 '"Reported Out of Committee (PUBLIC SAFETY & HOMELAND SECURITY) in House with 1 Favorable, 6 On Its Merits",1',
 '"Reported Out of Committee (PUBLIC SAFETY & HOMELAND SECURITY) in House with 3 Favorable, 3 On Its Merits",1',
 '"Reported Out of Committee (PUBLIC SAFETY & HOMELAND SECURITY) in House with 4 On Its Merits, 4 Unfavorable",1',
 '"Reported Out of Committee (PUBLIC SAFETY & HOMELAND SECURITY) in House with 5 On Its Merits, 1 Unfavorable",1',
 'Reported Out of Committee (PUBLIC SAFETY & HOMELAND SECURITY) in House with 6 On Its Merits,3',
 'Reported Out of Committee (PUBLIC SAFETY & HOMELAND SECURITY) in House with 7 On Its Merits,8',
 'Reported Out of Committee (PUBLIC SAFETY & HOMELAND SECURITY) in House with 8 On Its Merits,6',
 'Reported Out of Committee (PUBLIC SAFETY & HOMELAND SECURITY) in House with 9 On Its Merits,3',
 'Reported Out of Committee (PUBLIC SAFETY) in Senate with 4 On Its Merits,8',
 'Reported Out of Committee (PUBLIC SAFETY) in Senate with 6 Favorable,1',
 'Reported Out of Committee (PUBLIC SAFETY) in Senate with 7 On Its Merits,2',
 '"Reported Out of Committee (REVENUE & FINANCE) in House with 1 Favorable, 9 On Its Merits",1',
 'Reported Out of Committee (REVENUE & FINANCE) in House with 11 On Its Merits,1',
 '"Reported Out of Committee (REVENUE & FINANCE) in House with 2 Favorable, 7 On Its Merits",1',
 '"Reported Out of Committee (REVENUE & FINANCE) in House with 3 Favorable, 5 On Its Merits",1',
 '"Reported Out of Committee (REVENUE & FINANCE) in House with 6 Favorable, 6 On Its Merits",1',
 '"Reported Out of Committee (REVENUE & FINANCE) in House with 7 Favorable, 2 Unfavorable",1',
 '"Reported Out of Committee (REVENUE & FINANCE) in House with 8 Favorable, 2 On Its Merits",1',
 '"Reported Out of Committee (REVENUE & FINANCE) in House with 8 Favorable, 3 On Its Merits",1',
 '"Reported Out of Committee (REVENUE & FINANCE) in House with 9 Favorable, 1 On Its Merits",1',
 'Reported Out of Committee (REVENUE & FINANCE) in House with 9 On Its Merits,2',
 '"Reported Out of Committee (REVENUE & TAXATION) in Senate with 3 Favorable, 1 On Its Merits",1',
 '"Reported Out of Committee (REVENUE & TAXATION) in Senate with 3 On Its Merits, 1 Unfavorable",1',
 'Reported Out of Committee (REVENUE & TAXATION) in Senate with 4 On Its Merits,3',
 '"Reported Out of Committee (SMALL BUSINESS) in Senate with 2 Favorable, 2 On Its Merits, 1 Unfavorable",1',
 'Reported Out of Committee (SMALL BUSINESS) in Senate with 4 On Its Merits,1',
 'Reported Out of Committee (SMALL BUSINESS) in Senate with 4 Unfavorable,1',
 'Reported Out of Committee (SMALL BUSINESS) in Senate with 5 On Its Merits,1',
 '"Reported Out of Committee (SUNSET COMMITTEE (POLICY ANALYSIS & GOVERNMENT ACCOUNTABILITY)) in House with 1 Favorable, 3 On Its Merits",3',
 '"Reported Out of Committee (SUNSET COMMITTEE (POLICY ANALYSIS & GOVERNMENT ACCOUNTABILITY)) in House with 1 Favorable, 4 On Its Merits",5',
 '"Reported Out of Committee (SUNSET COMMITTEE (POLICY ANALYSIS & GOVERNMENT ACCOUNTABILITY)) in House with 2 Favorable, 3 On Its Merits",1',
 'Reported Out of Committee (SUNSET COMMITTEE (POLICY ANALYSIS & GOVERNMENT ACCOUNTABILITY)) in House with 4 On Its Merits,8',
 'Reported Out of Committee (SUNSET COMMITTEE (POLICY ANALYSIS & GOVERNMENT ACCOUNTABILITY)) in House with 5 On Its Merits,2',
 '"Reported Out of Committee (SUNSET) in Senate with 1 Favorable, 3 On Its Merits",5',
 '"Reported Out of Committee (SUNSET) in Senate with 1 Favorable, 4 On Its Merits",5',
 'Reported Out of Committee (SUNSET) in Senate with 4 On Its Merits,3',
 'Reported Out of Committee (SUNSET) in Senate with 5 On Its Merits,1',
 'Reported Out of Committee (TELECOMMUNICATION INTERNET & TECHNOLOGY) in House with 6 Favorable,1',
 'Reported Out of Committee (TELECOMMUNICATION INTERNET & TECHNOLOGY) in House with 6 On Its Merits,1',
 '"Reported Out of Committee (TRANSPORTATION/LAND USE AND INFRASTRUCTURE) in House with 1 On Its Merits, 3 Unfavorable",1',
 'Reported Out of Committee (TRANSPORTATION/LAND USE AND INFRASTRUCTURE) in House with 4 On Its Merits,2',
 '"Reported Out of Committee (TRANSPORTATION/LAND USE AND INFRASTRUCTURE) in House with 4 On Its Merits, 1 Unfavorable",1',
 'Reported Out of Committee (TRANSPORTATION/LAND USE AND INFRASTRUCTURE) in House with 5 Favorable,1',
 '"Reported Out of Committee (VETERANS AFFAIRS) in House with 10 Favorable, 4 On Its Merits",1',
 'Roll Call Rescinded in Senate,3',
 'Signed by Governor,210',
 'Stricken,18',
 'Vetoed by Governor,4',
 'was introduced and adopted in lieu of SB 156,1',
 'was introduced and adopted in lieu of SB 29,1',
 'was introduced and adopted in lieu of SB 56,1']

if __name__ == "__main__":
    import pdb
    from collections import defaultdict
    from operator import itemgetter
    from itertools import groupby, ifilterfalse
    
    _res = map(categorize, actions)
    uu = uncategorized = list(ifilterfalse(itemgetter(1), _res))
    categorized = filter(itemgetter(1), _res)

    res = defaultdict(set)
    grouped = groupby(_res, itemgetter(1))
    for x, y in grouped:
        for cat in y:
            res[x].add(cat)

    res = dict(res) 
    
        
    print 'uncategorized:', len(uncategorized)
    print 'categorized:', len(categorized)
    pdb.set_trace()

