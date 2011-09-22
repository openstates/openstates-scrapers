#!/usr/bin/env python
from setuptools import setup

long_description = open('README.rst').read()

setup(name='billy',
      version='0.9.0',
      packages=['billy', 'billy.scrape', 'billy.importers',
                'billy.bin', 'billy.misc', 'billy.site',
                'billy.site.browse', 'billy.site.api'],
      author="James Turk",
      author_email="jturk@sunlightfoundation.com",
      license="GPL v3",
      url="http://openstates.org",
      description='Open State Project',
      long_description=long_description,
      platforms=['any'],
      entry_points="""
[console_scripts]
billy-categorize-subjects = billy.bin.categorize_subjects:main
billy-devserver = billy.bin.run_dev_server:main
billy-dump-csv = billy.bin.dump_csv:main
billy-dump-json = billy.bin.dump_json:main
billy-dump-missing-leg-ids = billy.bin.dump_missing_leg_ids:main
billy-generate-stats = billy.bin.generate_statistics:generate_statistics
billy-import = billy.bin.import_state:main
billy-import-districts = billy.bin.import_districts:main
billy-load-legislator-csv = billy.bin.load_legislator_csv:main
billy-oysterize = billy.bin.oyster_versions:main
billy-retire-legislator = billy.bin.retire_legislator:main
billy-scrape = billy.bin.scrape:main
billy-scrape-bill = billy.bin.scrape_bill:main
billy-update-external-ids = billy.bin.update_external_ids:main
billy-update-leg-ids = billy.bin.update_leg_ids:main
billy-validate-api = billy.bin.validate_api:main
""")
