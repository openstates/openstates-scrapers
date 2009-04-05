About the Project
=================

The goal here is to build scrapers and parsers in order to get as much state 
legislative data as possible in one place.

For details on the reasons for the project and goals behind the project see 
`the project announcement <http://sunlightlabs.com/blog/2009/02/26/fifty-state-project/>`_.

For an editable overview of each state's progress visit the `Sunlight Labs Wiki <http://wiki.sunlightlabs.com/index.php/State_Legislation_Page>`_.

Project Goals
-------------

1. Collect URLs of State Legislature and Legislative Information Pages [done]
2. Grab legislators and legislation
     1. Build scrapers and obtain data files for legislation in each of the fifty states
     2. create sponsor relationship between legislators and legislation 
3. Grab votes
     1. Build scrapers and obtain data files for legislator votes on legislation
     2. create voting relationship between legislators and legislation 
4. Build tools on top of data 

To encourage as many contributions as possible we aren't saying "write in Python" 
or anything, but we do need the code to follow a few guidelines.

For details on how scripts should be written and how they should run see scripts/README.rst.
For details on how data should be stored see data/README.rst.

Usage (proposed)
----------------
Valid options:
 --year: a year or years the parser should attempt
 --all: Attempt to parse years from 1969-2009
 --upper: Parse upper chamber
 --lower: Parse lower chamber
 
The vision is that the flow will look something like this:
    $  ./scripts/nc/get_legislation --year=2009 --upper


Contributing
============

If you are interested in contributing the recommended procedure is to check on 
the `Sunlight Labs Wiki`_ and in the repository to see where your state is.  
The next step is generally to announce your interest on the `Sunlight Labs Mailing 
List <http://groups.google.com/group/sunlightlabs>`_ (this is where you can ask 
questions and make suggestions regarding the project).

Managing a State
----------------

Once you have claimed a state on the wiki and mailing list you should probably 
maintain your own fork of the project on `github <http://github.com>`_.

Please avoid making changes to files in other states/etc. on your state branch.  
Stick to editing files in the scripts/*your_state* directory and where necessary 
in any relevant utils directories.

Whenever your state script works as it should announce it on the mailing list and 
someone will merge your changes into the core.

Licensing
---------

We feel that in order to protect everyone's intellectual property it makes the 
most sense to keep the code under the `AGPL license <http://www.fsf.org/licensing/licenses/agpl-3.0.html>`_.  
In a nutshell this means that you are not permitted to make changes to this source 
without releasing your code as well, this is intended to prevent abuse but we 
are sensitive to license choice on a project of this scale so if you have strong 
objections please raise them on the mailing list. See LICENSING for the full terms 
of the AGPLv3.

Requirements
============

Python (2.4+)
-------------
* BeautifulSoup

Ruby (1.8.*+)
-------------
* hpricot (gem install hpricot)
* fastercsv (gem install fastercsv)
* mechanize (gem install mechanize)

A note on new requirements
--------------------------
Because there are potentially fifty plus contributors to this project, a real 
effort should be made to keep the requirements of running the full suite to a minimum.

In other words, if you can write your parser in language X and Y, choose language X 
if language X is already a requirement.
If you are using a language (say Python) and you need to parse HTML and there is 
already an HTML parsing library (say BeautifulSoup) favor that over some other 
library (unless absolutely necessary).
