import os

MONGO_HOST = os.environ.get('OPENSTATES_MONGO_HOST', 'localhost')
MONGO_PORT = os.environ.get('OPENSTATES_MONGO_PORT', 27017)
MONGO_DATABASE = os.environ.get('OPENSTATES_MONGO_DATABASE', 'fiftystates')

BILLY_DATA_DIR = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '../../data'))

# Set to None to disable caching
BILLY_CACHE_DIR = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '../../cache'))

BILLY_ERROR_DIR = os.path.abspath(os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '../../errors'))

BILLY_SUBJECTS = [
    'Agriculture and Food',
    'Animal Rights and Wildlife Issues',
    'Arts and Humanities',
    'Budget, Spending, and Taxes',
    'Business and Consumers',
    'Campaign Finance and Election Issues',
    'Civil Liberties and Civil Rights',
    'Commerce',
    'Crime',
    'Drugs',
    'Education',
    'Energy',
    'Environmental',
    'Executive Branch',
    'Family and Children Issues',
    'Federal, State, and Local Relations',
    'Gambling and Gaming',
    'Government Reform',
    'Guns',
    'Health',
    'Housing and Property',
    'Immigration',
    'Indigenous Peoples',
    'Insurance',
    'Judiciary',
    'Labor and Employment',
    'Legal Issues',
    'Legislative Affairs',
    'Military',
    'Municipal and County Issues',
    'Nominations',
    'Other',
    'Public Services',
    'Recreation',
    'Reproductive Issues',
    'Resolutions',
    'Science and Medical Research',
    'Senior Issues',
    'Sexual Orientation and Gender Issues',
    'Social Issues',
    'State Agencies',
    'Technology and Communication',
    'Trade',
    'Transportation',
    'Welfare and Poverty']

SCRAPELIB_TIMEOUT = 600
SCRAPELIB_RETRY_ATTEMPTS = 3
SCRAPELIB_RETRY_WAIT_SECONDS = 20
