ksleg = 'http://www.kslegislature.org/li'
url = '%s/api/v7/rev-1/' % ksleg

# in order from sec 10.1 of KLISS doc
action_codes = {
     # motion to acede; appointed
    'ccac_om_370': 'other',
    'efa_fabc_343': 'bill:passed',
    'efa_fabc_342': 'bill:passed',
    'cref_cref_500': 'committee:referred',
    'cref_cref_318': 'committee:referred',  # withdrawn and re-referred
    'gov_avm_336': 'bill:veto_override:passed',
    # change sequence
    'mot_cgo_200': 'other', 'mot_cgo_201': 'other', 'mot_cgo_202': 'other',
    'gov_mg_378': 'governor:vetoed:line-item',
    'fa_fabc_115': 'bill:failed',
    'cr_rsc_292': 'committee:passed:favorable',
    'cr_rsc_276': 'committee:passed',
    'cr_rsc_274': 'committee:passed:unfavorable',
    'cr_rsc_275': 'committee:passed:unfavorable',
    'cr_rsc_273': 'committee:passed:unfavorable',
    'cr_rsc_270': 'bill:substituted',
    # untabled/reconsiderations
    'mot_tab_402': 'other', 'mot_tab_403': 'other', 'mot_tab_401': 'other',
    'mot_tab_404': 'other', 'mot_rcon_303': 'other', 'mot_rcon_302': 'other',
    'ee_enrb_149': 'governor:received',
    'cow_jcow_197': ['bill:passed', 'bill:substituted'],
    'mot_pspn_405': 'other', # postpone - failed
     # other COW actions
    'cow_jcow_211': 'other', 'cow_jcow_210': 'other', 'cow_jcow_214': 'other',
    'cow_jcow_695': 'other', 'cow_jcow_694': 'other', 'cow_jcow_693': 'other',
    'cow_jcow_692': 'other', 'cow_jcow_690': 'other', 'cow_jcow_317': 'other',
    'cow_jcow_718': 'other', 'cow_jcow_719': 'other', 'cow_jcow_720': 'other',
    'cow_jcow_681': 'other', 'cow_jcow_682': 'other', 'cow_jcow_683': 'other',
    'cow_jcow_684': 'other', 'cow_jcow_685': 'other', 'cow_jcow_688': 'other',
    'cow_jcow_689': 'other',
     # withdrawn from consent cal.'
    'ccal_rcc_233': 'other',
    'ccal_faccl_900': 'other',   # consent calendar passed
    'efa_fabc_933': 'bill:passed', # these 3 are 2/3 emergency clause votes...
    'efa_fabc_936': 'bill:failed',
    'efa_fabc_934': 'bill:passed',
    'cref_cref_316': ['bill:withdrawn','committee:referred'],
    'cref_cref_315':  ['bill:withdrawn','committee:referred'],
    'cur_con_374': 'other', # non-concur, conf. com. requested
    'cr_rsc_801': 'committee:passed:unfavorable', # these 3 are appointments..
    'cr_rsc_800': 'committee:passed:favorable',
    'cr_rsc_802': 'committee:passed',
    'ccr_rel_100': 'other',  # conference committee report available
    'misc_bs_100': 'other',  # adopting conf committee report
    'gov_mg_150': 'governor:signed',
    'gov_mg_151': 'other', # law w/o signature
    'gov_mg_154': 'governor:vetoed',
    'cow_jcow_180': 'bill:passed', # COW
    'ar_adj_605': 'other',  # adjourn
    'ee_enrb_888': 'other',   # enrolled and presented to Sec. of State
    'cow_jcow_239': 'bill:passed', # adopted
    'cur_con_875': 'other', # nonconcurrences
    'cur_con_876': 'other',
    'cur_con_873': 'other',
    'fa_fabc_341': 'bill:passed',
    'fa_fabc_340': 'bill:passed',
    'ccac_ccr_860': 'other',
    'efa_fabc_115': 'bill:failed',
    'intro_iopbc_158': 'bill:introduced',
    'intro_iopbc_681': 'bill:introduced',
    'intro_iopbc_251': 'bill:passed',
    'cr_rsc_291': 'committee:passed',
    'fa_fabc_116': 'bill:failed',
    'cow_jcow_728': 'amendment:withdrawn',
    'cow_jcow_727': 'amendment:failed',
    'cow_jcow_726': 'amendment:passed',
    'cow_jcow_725': ['bill:substituted', 'bill:passed'],
    # motions to postpone
    'mot_pspn_404': 'other', 'mot_pspn_403': 'other', 'mot_pspn_402': 'other',
    'fa_fabc_910': 'bill:failed',
    # suspend rules
    'mot_susp_216': 'other', 'mot_susp_214': 'other', 'mot_susp_215': 'other',
    'mot_susp_208': 'other', 'mot_susp_209': 'other',
    'cr_rsc_289': 'committee:passed',
    # conference committee
    'ccac_ccr_375': 'other', 'cur_con_337': 'other',
    'cur_con_336': 'other', 'cur_con_335': 'other',
    'ref_rbc_308': 'committee:referred',
    'ref_rbc_307': 'committee:referred',
    'efa_fabc_352': 'bill:passed',
    'efa_fabc_351': 'bill:passed',
    'intro_ibc_251': 'bill:passed',
    # COW recommendations
    'cow_jcow_705': ['bill:substituted', 'bill:passed'],
    'cow_jcow_704': ['bill:substituted', 'bill:passed'],
    'cow_jcow_707': 'amendment:introduced',
    'cow_jcow_709': 'bill:passed',
    'cow_jcow_708': 'bill:passed',
    # adjourn/recess
    'ar_adj_625': 'other', 'ar_adj_626': 'other',
    'intro_ires_251': 'bill:passed',
    'intro_ires_255': 'bill:passed',
    # engrossed/rengrossed
    'ee_eng_225': 'other', 'ee_eng_227': 'other',
    # referred to COW
    'ref_rbc_235': 'other',
    'cur_iopbc_141': 'committee:referred',
    'mot_wd_126': 'other', #'committee:withdrawn',
    'mot_wd_127': 'other', # withdraw from com- failed
    'mot_wd_125': 'other', # withdraw from com- pending
    # strike from calendar
    'mot_strk_505': 'other', 'mot_strk_504': 'other', 'mot_strk_501': 'other',
    # conf. com report adopted
    'ccac_om_832': 'bill:passed',
    'ccac_ccr_862': 'other', # motion to not adopt conf.com report failed
    'ccac_ccr_863': 'bill:failed', # failed in conf.com, report not adopted
    'ccac_ccr_865': 'other', # motion to not adopt conf.com report failed
    'ccac_ccr_867': 'other', # agree to disagree on conf. com report
    # passed over
    'cow_jcow_201': 'other', 'cow_jcow_202': 'other', 'cow_jcow_203': 'other',
    'ccac_cc_377': 'other', # conf committee changed member
    'ee_enrb_226': 'other', # Enrolled
    # veto overrides
    'gov_avm_885': 'bill:veto_override:failed',
    'gov_avm_887': 'bill:veto_override:passed',
    'ref_rsc_312': 'committee:referred',
    # more COW actions
    'cow_jcow_903': 'other', 'cow_jcow_902': 'other', 'cow_jcow_901': 'other',
    'cow_jcow_905': 'other',
    # no motion to veto override (count as failure?)
    'gov_avm_128': 'bill:veto_override:failed',
    'gov_avm_129': 'bill:veto_override:failed',
    'cow_jcow_191': 'bill:passed',
    'cow_jcow_192': 'bill:passed',
    'cow_jcow_195': 'other', # com. report adopted
    'cow_jcow_196': ['bill:passed', 'bill:substituted'],
    'gov_avm_125': 'bill:veto_override:failed',
    'mot_ref_102': 'committee:referred',
    'mot_ref_105': 'other',  # not referred to committee
    'cref_cref_551': 'committee:referred',
    'cref_cref_552': 'committee:referred',
    'mot_apt_301': 'other',  # 20 days in committee, returned to senate
    'ccac_om_878': 'other',  # Motion to accede failed
    'efa_fabc_925': ['bill:passed', 'bill:substituted'],
    'efa_fabc_926': ['bill:passed', 'bill:substituted'],
    'efa_fabc_923': ['bill:passed', 'bill:substituted'],
    'efa_fabc_922': ['bill:passed', 'bill:substituted'],
    'fa_fabc_105': ['bill:failed', 'bill:substituted'],
    'fa_fabc_104': 'bill:failed',
    'intro_ibc_157': 'bill:introduced',
    'intro_ibc_158': 'bill:introduced',
    'intro_ibc_156': 'bill:filed',
    'fa_fabc_905': 'bill:passed',
    'intro_ires_681': 'bill:introduced',
    'cref_cref_290': 'committee:referred',
    'fa_fabc_352': 'bill:passed',
    'ccac_ccr_145': 'bill:failed',
    'fa_fabc_351': 'bill:passed',
    # motion to move to general orders
    'mot_adv_303': 'other', 'mot_adv_302': 'other', 'mot_adv_301': 'other',
    'efa_fabc_106': ['bill:failed', 'bill:substituted'],
    'efa_fabc_105': ['bill:failed', 'bill:substituted'],
    'efa_fabc_104': 'bill:failed',
    'ccac_ccr_833': 'bill:failed',
    'ref_rbc_310': 'committee:referred',
    'cr_rsc_283': 'committee:passed:favorable',
    'cr_rsc_282': 'committee:passed:favorable',
    'cr_rsc_281': 'committee:passed:favorable',
    'cr_rsc_287': 'committee:passed:favorable',
    'cr_rsc_286': 'committee:passed:favorable',
    'cr_rsc_285': 'committee:passed:favorable',
    'ref_rbc_500': 'committee:referred',
    'cr_rsc_288': 'committee:passed',
    # Conf. Com. reports
    'ccac_ccr_883': 'other', 'ccac_ccr_880': 'other', 'ccac_ccr_881': 'other',
    'cow_jcow_712': ['bill:passed', 'bill:substituted'],
    'cow_jcow_710': ['bill:passed', 'bill:substituted'],
    'cow_jcow_711': ['bill:passed', 'bill:substituted'],
    'cow_jcow_716': 'other',
    'fa_fabc_925': 'bill:passed',
    'fa_fabc_924': 'bill:passed',
    'fa_fabc_926': 'bill:failed',
    'fa_fabc_921': ['bill:passed', 'bill:substituted'],
    'fa_fabc_920': ['bill:passed', 'bill:substituted'],
    'fa_fabc_923': ['bill:passed', 'bill:substituted'],
    'fa_fabc_922': ['bill:passed', 'bill:substituted'],
    'cr_rsc_821': 'committee:passed:unfavorable',
    'cow_jcow_305': 'committee:referred',
    'cow_jcow_304': 'committee:referred',
    'gov_avm_349': 'bill:veto_override:failed',
    'intro_ibc_681': 'bill:introduced',
    'dss_627': 'other',
    'mot_susp_203': 'other',
    'mot_susp_202': 'other',
    'mot_susp_206': 'other',
    'cur_con_101': 'other', # concur. failed
    'cur_om_141': 'committee:referred',
    'misc_he_200': 'other', # hearing
    # Died on Calendar
    'dead_conf_101': 'other',  # died in conference
    'dead_cal_201': 'other',
    'dead_cal_202': 'other',
    'dead_cal_203': 'other',
    'dead_com_301': 'committee:failed',
    'dead_com_302': 'committee:failed',
    'dead_com_303': 'committee:failed',
    'dead_go_302': 'other', # died on general order
    'dead_go_401': 'other', # died on general order
    'dead_go_402': 'other', # died on general order
    'kill_reso_100': 'bill:failed',
    'kill_reso_200': 'bill:failed',
    }
