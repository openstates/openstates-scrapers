#!/bin/bash

/opt/openstates/venv-pupa/bin/pupa dbinit --country us

parties="
Democratic
Republican
Independent
Progressive
Progressive/Democratic
Democratic/Progressive
Democratic-Farmer-Labor
Nonpartisan
Partido Nuevo Progresista
Partido Popular Democrático
Partido Independentista Puertorriqueño
"

IFS=$(echo -en "\n\b")
for party in ${parties}; do
  /opt/openstates/venv-pupa/bin/pupa party --action add "${party}"
done
