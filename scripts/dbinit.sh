#!/bin/sh

/opt/openstates/venv-pupa/bin/pupa dbinit --country us

parties="
Democratic
Republican
Independent
Libertarian
Progressive
Progressive/Democratic
Democratic/Progressive
Democratic-Farmer-Labor
Nonpartisan
Partido Nuevo Progresista
Partido Popular Democrático
Partido Independentista Puertorriqueño
"

echo "${parties}" | while read -r party; do
  if [ -n "${party}" ]; then
    /opt/openstates/venv-pupa/bin/pupa party --action add "${party}"
  fi
done
