
=======
Scripts
=======

All scripts with the same task should have the same name and accept the same
command line arguments. (Though they can be written in any language.)

All of these scripts should reside a subdirectory for the given state.

---------------
get_legislation
---------------

Grab a listing of all bills (state, chamber, session, bill_id, remote_url) 
matching the given criteria.

Arguments
---------

  -y YEARS, --year=YEARS
                        year(s) to scrape
  --upper               scrape upper chamber
  --lower               scrape lower chamber

