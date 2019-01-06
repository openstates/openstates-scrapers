#!/bin/sh
set -e

# copy environment variables
export OCD_DATABASE_NAME="openstatesorg"
export OCD_DATABASE_HOST=$PGHOST
export OCD_DATABASE_USER=$PGUSER
export OCD_DATABASE_PASSWORD=$PGPASSWORD

# checkout fresh copy of people directory
rm -rf /tmp/os-people
git clone https://github.com/openstates/people.git /tmp/os-people/
cd /tmp/os-people

# make virtualenv
python3 -m venv /tmp/people-venv
source /tmp/people-venv/bin/activate
pip install -r scripts/requirements.txt

# run the script
./scripts/to_database.py $@
