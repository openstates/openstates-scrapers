Rhode Island
============

Metadata
--------
Name: Rhode Island and Providence Plantations  
Abbreviation: RI  
Legislature Name: Rhode Island General Assembly  
Upper Chamber Name: Senate  
Lower Chamber Name: House of Representatives  
Upper Chamber Title: Senator  
Lower Chamber Title: Representative  
Upper Chamber Term: 2 years  
Lower Chamber Term: 2 years  


Information Locations
=====================

Legislators
-----------
http://www.rilin.state.ri.us/Documents/Senators.xls  
http://www.rilin.state.ri.us/Documents/Representatives.xls

* term
* chamber
* district
* full name
* party

Committees
----------
http://www.rilin.state.ri.us/Sitemap.html  
http://www.rilin.state.ri.us/ComMembers/ComMemS.asp?ComChoiceS=SCHM (example for one committee)

* chamber
* committee name
* members & roles

Bills
-----
http://www.rilin.state.ri.us/BillText11/HouseText11/HouseText11.html  
http://www.rilin.state.ri.us/BillText11/SenateText11/SenateText11.html  
http://www.rilin.state.ri.us/Journals11/HouseJournals11/Housejournals11.html  
http://www.rilin.state.ri.us/Journals11/SenateJournals11/Senatejournals11.html  
http://dirac.rilin.state.ri.us/billstatus/WebClass1.ASP?WCI=BillStatus&WCE=ifrmBillStatus&WCU
(Note: a POST with a comma delimited list of bill numbers passed as the 'hListBills' form
parameter to the following URL provides information on bills)

* session
* chamber
* bill id
* title
* type
* sponsors and cosponsors

- - -

Scraper Information
===================

legislators.py
--------------
Progress: finished

Sources:

* http://www.rilin.state.ri.us/Documents/Senators.xls
* http://www.rilin.state.ri.us/Documents/Representatives.xls

Data scraped:
* term
* chamber
* district_name
* full_name
* party
* office_address
* town_represented (comma delimited list of towns)
* email

Notes: The source information does not provide separate first/last name information, so only
full name is scraped.


committees.py
-------------
Progress: finished

Sources:

* http://www.rilin.state.ri.us/Sitemap.html

Data scraped:

* chamber
* membernames
* roles

Notes: It seems like the committee links from http://www.rilin.state.ri.us/Sitemap.html are
intermittently timing-out. There is a try/except clause to handle these timeouts.


bills.py
--------
Progress: some

Sources:

* http://www.rilin.state.ri.us/BillText11/HouseText11/HouseText11.html
* http://www.rilin.state.ri.us/BillText11/SenateText11/SenateText11.html
* http://www.rilin.state.ri.us/Journals11/HouseJournals11/Housejournals11.html
* http://www.rilin.state.ri.us/Journals11/SenateJournals11/Senatejournals11.html
* (Note: a POST with a comma delimited list of bill numbers passed as the 'hListBills' form
parameter to the following URL provides information on bills)
http://dirac.rilin.state.ri.us/billstatus/WebClass1.ASP?WCI=BillStatus&WCE=ifrmBillStatus&WCU

Implementation plan: Currently, bills are requested one at a time and the results are parsed
for the relevant data. It would potentially be quicker to request multiple bill details all at
once, but there is a difficulty in that the list of bills contains bills with irregular IDs
(they end with letters, e.g. 5002Aaa) which would need to be removed (the request page only
accepts numerical bill IDs). Additionally, bill actions are present in the results, but they
are currently not parsed. For vote information, the plan is to look into the House and Senate
Journals for the relevant days to get the roll call. Unfortunately, the journals are only
available as PDFs.

Data scraped:

* session
* chamber
* bill_id
* title
* type
* sponsors and cosponsors

Note: Currently, a try/except clause handles irregular bill IDs. It would be better to exclude
these before sending the POST request.
