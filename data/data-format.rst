.. _database:

=====================
Structuring Your Data
=====================
The following documentaiton describes how state data is structured.
You do not need to structure your data if you are using the Python or
Ruby legislation scraper APIs.

Directory Structure
===================
All data should be stored in a directory named after the state's
initials in the *data* directory.  For example, the legislative data
for New York should be stored in the *data/ny* directory.  Your script
must create the directories if they do not already exist.

Within your state's directory should be the following:

* **bills** directory where json files containg bill data are stored
* **legislators** directory to hold json files containing data on the legislators
* **state_metadata.json**  which holds the state metadata


Structuring State Metadata
==========================

The following data is stored in *state_metadata.json*

**Required Attributes**: 

* **state** two letter abbreviation of state, such as "ma" for Massachusetts
* **state_name** non-abbreviated name of state, such as "Massachusetts"


**Optional Attributes**:

* **full_state_name** full official name of state, such as "Comonwealth
   of Massachusetts"
* **upper_chamber_name** name of the upper chamber (this is often "Senate")
* **lower_chamber_name** name of the upper chamber (this is often "House")
* **upper_title** title of member of upper chamber (such as "Senator")
* **lower_title** title of member of lower chamber (such as "Assembly Member")
* **legislator_name** name of state's legislature (such as "The General
   Court of The Commonwealth of Massachusetts")
* **upper_term** length of term for member of upper chamber
* **lower_term** length of term for member of lower chamber
* **sessions** list of session names
* **session_details** contains attributes named after each session name
   in session with the following information
     * **sub_sessions** list of names of any special sessions that took
        place within this session
     * **years** list of years during which the session took place



Structuring Bill Data
=====================



Structuring Legistlative Data
=============================

