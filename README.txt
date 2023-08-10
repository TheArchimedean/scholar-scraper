   _____      __          __                                                     
  / ___/_____/ /_  ____  / /___ ______      ___________________ _____  ___  _____
  \__ \/ ___/ __ \/ __ \/ / __ `/ ___/_____/ ___/ ___/ ___/ __ `/ __ \/ _ \/ ___/
 ___/ / /__/ / / / /_/ / / /_/ / /  /_____(__  ) /__/ /  / /_/ / /_/ /  __/ /    
/____/\___/_/ /_/\____/_/\__,_/_/        /____/\___/_/   \__,_/ .___/\___/_/     
                                                             /_/                 
      v1.1
      Created by Ted Binns

      This program scrapes academic and paper details from the Google Scholar
      profile pages associated with search queries that are entered in the
      file "search queries.txt".


*********IMPORTANT*********
----------------------------------------------------------------------------
After running the script, it is HIGHLY RECOMMENDED to save the files 
somewhere else on your computer. This script does not amend files, but
would write over the top of them. To prevent losing data from particularly
the large concatenated csv, it is recommended to make a copy of it elsewhere
on your machine.



RUNNING THE PROGRAM
----------------------------------------------------------------------------
1. Add the desired queries to 'search queries.txt', one per line. These 
   queries should represent searches on Google Scholar profiles. A
   recommended query could look like 'first-name last-name university', i.e. 

	john doe york

2. Open command prompt/powershell

3. Navigate to the directory where both scholar-scraper.py and the search text
   file from step 1 is located. e.g. 
   on windows, it could be 
	> cd C:\Files\Projects\

4. Install the required packages using pip
	>pip install -r requirements.txt

5. Now run the Python script
	>python3 scholar-scraper.py

   The application uses a headless chrome driver, meaning the webpage being
   loaded and scraped is loaded in the background, so as to not interrupt
   other work on the computer.

   The console contains information on the progress of the script, including
   progress bars on paper collection for each academic.

   The program will read 'ALL TASKS COMPLETE' when complete, and print a list
   of failed search queries. These failures are likely to be caused by the
   user not having a profile on Google Scholar.



RESULTS
----------------------------------------------------------------------------
Resulting data is stored in two ways. The first is an individual academic
and papers csv for each query stored in the 'Individual sheets' folder.

	Academic -> contains information on the academic such as their name,
		    affiliated university and citation information.
	Paper    -> contains each paper an academic has written (that is on
		    Google Scholar. It has the name, number of citations, 
		    publication date, source and author information.

A larger csv with all previous files concatenated is also created and stored
in the main directory. This contains all previous information in one place.
After each search query, the papers and academic details are added to the 
existing large csv, so that in the case of a crash, at least some information
is salvaged.

IMPORTANT: The program does NOT append the csv - it writes a new one each time
	   it is run so be careful when running the script that you have an 
	   existing copy backed up elsewhere if it is important.



RUNTIME
----------------------------------------------------------------------------
The program will take variable amount of time to run, as it pseudo-randomly
spends different amount of times on each web page to circumvent Google's
bot detection. Though on average, expect the program to take 3-4 seconds
per paper an academic has.
