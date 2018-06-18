#!/bin/sh

/opt/openstates/venv-pupa/bin/pupa dbinit --country us

parties="
Democratic
Republican
Independent
Progressive
Progressive/Democratic
Democratic/Progressive
Democratic-Farmer-Labor
"

for party in ${parties}; do
  /opt/openstates/venv-pupa/bin/pupa party --action add "${party}"
done
