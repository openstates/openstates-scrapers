==========
California
==========

MySQL Dumps
-----------

California's legislative MySQL dumps can be found at ftp://www.leginfo.ca.gov/pub/bill/. If you are using Windows, follow the directions in their provided ``README``. If you are using Unix:

1. Download ``pubinfo_load.zip`` and unzip in a temporary directory
2. Run provided ``create_capublic`` script with your MySQL credentials and path of temp directory
3. For each session you're interested in:

   a. Download and unzip ``pubinfo_YEAR.zip`` into above directory
   b. Run ``load_data`` script
   c. Run ``cleanup`` script

4. To get data from the last week you can use ``pubinfo_Mon.zip`` through ``pubinfo_Sun.zip``

You'll need to make sure MySQL can read from the temp directory in order to load CA's legislative XML (check your AppArmor settings on Linux, many distros restrict MySQL filesystem read access by default).