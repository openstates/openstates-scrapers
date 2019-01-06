#!/bin/sh

until mysql -h "${MYSQL_HOST:-"localhost"}" -u "${MYSQL_USER:-"mysql"}" -e "SHOW DATABASES"; do
  sleep 1
done

$PUPA_ENV/bin/python -m openstates.ca.download
