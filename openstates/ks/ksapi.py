ksleg = 'http://www.kslegislature.org/li'
url = '%s/api/v11/rev-1/' % ksleg

# These actions are from the KLISS API documentation,
# and are in the same order as that table
# The PDF is linked from this webpage, and changes name
# based on the most recent API version:
# http://www.kslegislature.org/klois/Pages/RESTianAPI.html
action_codes = {
    # motion to acede; appointed
    'ccac_om_370': None,
    'efa_fabc_343': 'passage',
    'efa_fabc_342': 'passage',
    'cref_cref_500': 'referral-committee',
    'gov_avm_336': 'veto-override-passage',
    # change sequence
    'mot_cgo_200': None, 'mot_cgo_201': None, 'mot_cgo_202': None,
    'gov_mg_378': 'executive-veto-line-item',
    'fa_fabc_115': 'failure',
    'cr_rsc_292': 'committee-passage-favorable',
    'cr_rsc_276': 'committee-passage',
    'cr_rsc_274': 'committee-passage-unfavorable',
    'cr_rsc_275': 'committee-passage-unfavorable',
    'cr_rsc_273': 'committee-passage-unfavorable',
    'cr_rsc_270': 'substitution',
    # untabled/reconsiderations
    'mot_tab_402': None, 'mot_tab_403': None, 'mot_tab_401': None,
    'mot_tab_404': None, 'mot_rcon_303': None, 'mot_rcon_302': None,
    'ee_enrb_149': 'executive-receipt',
    'cow_jcow_197': ['passage', 'substitution'],
    'mot_pspn_405': None,  # postpone - failed
    # other COW actions
    'cow_jcow_211': None, 'cow_jcow_210': None, 'cow_jcow_214': None,
    'cow_jcow_695': None, 'cow_jcow_694': None, 'cow_jcow_693': None,
    'cow_jcow_692': None, 'cow_jcow_690': None,
    # withdrawn from consent cal.'
    'ccal_rcc_233': None,
    'efa_fabc_933': 'passage',  # these 3 are 2/3 emergency clause votes...
    'efa_fabc_936': 'failure',
    'efa_fabc_934': 'passage',
    'cref_cref_316': ['withdrawal', 'referral-committee'],
    'cref_cref_315': ['withdrawal', 'referral-committee'],
    'cur_con_374': None,  # non-concur, conf. com. requested
    'cr_rsc_801': 'committee-passage-unfavorable',  # these 3 are appointments..
    'cr_rsc_800': 'committee-passage-favorable',
    'cr_rsc_802': 'committee-passage',
    'gov_mg_150': 'executive-signature',
    'gov_mg_151': None,  # law w/o signature
    'gov_mg_154': 'executive-veto',
    'cow_jcow_180': 'passage',  # COW
    'ar_adj_605': None,  # adjourn
    'ee_enrb_888': None,   # enrolled and presented to Sec. of State
    'cow_jcow_239': 'passage',  # adopted
    'cur_con_875': None,  # nonconcurrences
    'cur_con_876': None,
    'cur_con_873': None,
    'fa_fabc_341': 'passage',
    'fa_fabc_340': 'passage',
    'ccac_ccr_860': None,
    'efa_fabc_115': 'failure',
    'intro_iopbc_158': 'introduction',
    'cr_rsc_291': 'committee-passage',
    'fa_fabc_116': 'failure',
    'cow_jcow_728': 'amendment-withdrawal',
    'cow_jcow_727': 'amendment-failure',
    'cow_jcow_726': 'amendment-passage',
    'cow_jcow_725': ['substitution', 'passage'],
    # motions to postpone
    'mot_pspn_404': None, 'mot_pspn_403': None, 'mot_pspn_402': None,
    'fa_fabc_910': 'failure',
    # suspend rules
    'mot_susp_216': None, 'mot_susp_214': None, 'mot_susp_215': None,
    'cr_rsc_289': 'committee-passage',
    # conference committee
    'ccac_ccr_375': None, 'cur_con_337': None,
    'cur_con_336': None, 'cur_con_335': None,
    'ref_rbc_308': 'referral-committee',
    'ref_rbc_307': 'referral-committee',
    'efa_fabc_352': 'passage',
    'efa_fabc_351': 'passage',
    'intro_ibc_251': 'passage',
    # COW recommendations
    'cow_jcow_705': ['substitution', 'passage'],
    'cow_jcow_704': ['substitution', 'passage'],
    'cow_jcow_707': 'amendment-introduction',
    'cow_jcow_709': 'passage',
    'cow_jcow_708': 'passage',
    # adjourn/recess
    'ar_adj_625': None, 'ar_adj_626': None,
    'intro_ires_251': 'passage',
    # engrossed/rengrossed
    'ee_eng_225': None, 'ee_eng_227': None,
    # referred to COW
    'ref_rbc_235': None,
    'cur_iopbc_141': 'referral-committee',
    'mot_wd_126': None,  # 'committee:withdrawn',
    'mot_wd_127': None,  # withdraw from com- failed
    'mot_wd_125': None,  # withdraw from com- pending
    # strike from calendar
    'mot_strk_505': None, 'mot_strk_504': None, 'mot_strk_501': None,
    # conf. com report adopted
    'ccac_om_832': 'passage',
    'ccac_ccr_862': None,  # motion to not adopt conf.com report failed
    'ccac_ccr_863': 'failure',  # failed in conf.com, report not adopted
    'ccac_ccr_865': None,  # motion to not adopt conf.com report failed
    'ccac_ccr_867': None,  # agree to disagree on conf. com report
    # passed over
    'cow_jcow_201': None, 'cow_jcow_202': None, 'cow_jcow_203': None,
    'ccac_cc_377': None,  # conf committee changed member
    'ee_enrb_226': None,  # Enrolled
    # more COW actions
    'cow_jcow_681': None,
    'cow_jcow_682': None,
    'cow_jcow_683': None,
    'cow_jcow_688': None,
    'cow_jcow_689': None,
    # veto overrides
    'gov_avm_885': 'veto-override-failure',
    'gov_avm_887': 'veto-override-passage',
    'ref_rsc_312': 'referral-committee',
    # more COW actions
    'cow_jcow_903': None, 'cow_jcow_902': None, 'cow_jcow_901': None,
    'cow_jcow_905': None,
    # no motion to veto override (count as failure?)
    'gov_avm_128': 'veto-override-failure',
    'gov_avm_129': 'veto-override-failure',
    'cow_jcow_191': 'passage',
    'cow_jcow_192': 'passage',
    'cow_jcow_195': None,  # com. report adopted
    'cow_jcow_196': ['passage', 'substitution'],
    'gov_avm_125': 'veto-override-failure',
    'mot_ref_102': 'referral-committee',
    'mot_ref_105': None,  # not referred to committee
    'cref_cref_551': 'referral-committee',
    'cref_cref_552': 'referral-committee',
    'mot_apt_301': None,  # 20 days in committee, returned to senate
    'ccac_om_878': None,  # Motion to accede failed
    'efa_fabc_925': ['passage', 'substitution'],
    'efa_fabc_926': ['passage', 'substitution'],
    'efa_fabc_923': ['passage', 'substitution'],
    'efa_fabc_922': ['passage', 'substitution'],
    'fa_fabc_105': ['failure', 'substitution'],
    'fa_fabc_104': 'failure',
    'intro_ibc_157': 'introduction',
    'intro_ibc_156': 'filing',
    'fa_fabc_905': 'passage',
    'intro_ires_681': 'introduction',
    'cref_cref_290': 'referral-committee',
    'fa_fabc_352': 'passage',
    'ccac_ccr_145': 'failure',
    'fa_fabc_351': 'passage',
    # motion to move to general orders
    'mot_adv_303': None, 'mot_adv_302': None, 'mot_adv_301': None,
    'efa_fabc_106': ['failure', 'substitution'],
    'efa_fabc_105': ['failure', 'substitution'],
    'efa_fabc_104': 'failure',
    'ccac_ccr_833': 'failure',
    'ref_rbc_310': 'referral-committee',
    'cr_rsc_283': 'committee-passage-favorable',
    'cr_rsc_282': 'committee-passage-favorable',
    'cr_rsc_281': 'committee-passage-favorable',
    'cr_rsc_287': 'committee-passage-favorable',
    'cr_rsc_286': 'committee-passage-favorable',
    'cr_rsc_285': 'committee-passage-favorable',
    'ref_rbc_500': 'referral-committee',
    'cr_rsc_288': 'committee-passage',
    # Conf. Com. reports
    'ccac_ccr_883': None, 'ccac_ccr_880': None, 'ccac_ccr_881': None,
    'cow_jcow_712': ['passage', 'substitution'],
    'cow_jcow_710': ['passage', 'substitution'],
    'cow_jcow_711': ['passage', 'substitution'],
    'cow_jcow_716': None,
    'fa_fabc_925': 'passage',
    'fa_fabc_924': 'passage',
    'fa_fabc_926': 'failure',
    'fa_fabc_921': ['passage', 'substitution'],
    'fa_fabc_920': ['passage', 'substitution'],
    'fa_fabc_923': ['passage', 'substitution'],
    'fa_fabc_922': ['passage', 'substitution'],
    'cr_rsc_821': 'committee-passage-unfavorable',
    'cow_jcow_305': 'referral-committee',
    'cow_jcow_304': 'referral-committee',
    'gov_avm_349': 'veto-override-failure',
    'intro_ibc_681': 'introduction',
    'dss_627': None,
    'mot_susp_203': None,
    'mot_susp_202': None,
    'mot_susp_206': None,
    'cur_con_101': None,  # concur. failed
    'cur_om_141': 'referral-committee',
    'misc_he_200': None,
}
