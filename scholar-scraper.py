## Import relevant packages
import pandas as pd
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
import numpy as np
import scipy as sp

import pyodbc
from datetime import datetime
import hashlib

import time

from tqdm import tqdm 
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument("--headless")

from bs4 import BeautifulSoup

import os
import os.path

import warnings
warnings.filterwarnings(action='ignore')

## Defining useful functions

def get_scholar_search_url(search):
    '''
    Gets the Google Scholar search results for user inputted first and last names 

    Parameters:
        first_name (str): first name
        last_name (str): last name

    Returns:
        search_url (str): url of search query
    '''
    s = search.split(" ")
    query = ""
    for i in s:
        query = query + "+" + i

    query = query[1:]

    url = "https://scholar.google.com/citations?hl=en&view_op=search_authors&mauthors=" + query + "&btnG="
    
    return url

def generate_id(s):
    '''
    Generates a unique hash id for each column based on a string input which will be the paper title. 

    Parameters:
        s (str): a string input, which will be made up of multiple columns of a dataframe 'added' (concatenated) together

    Returns:
        An 8 digit hash that uniquely identifies the string entered, and hence the row of a dataframe it represents
    '''
    return int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16) % 10**8

def format_date(s):
    '''
    If a date does not contian a '/', it is likely in the form YYYY, so add the following '/1/1' to make compatable with datetime YYYY/mm/dd

    Parameters:
        s (str or numerical type): a string or numerical form of a date

    Returns:
        A date representing s in the form YYYY/mm/dd.
    '''
    s= str(s)
    n = s.count('/')
    
    if n == 2: #date is currently in form YYYY/mm/dd
        return s 
    elif n == 1: #date is currently in form YYYY/mm
        return s + '/1'
    elif len(s) == 4: #date is currently in form YYYY
        return s + '/1/1'
    else: #there is no date information
        return ''
    
def random_sleep(min, max):
    '''
    Instead of sleeping for a set time, this function sleeps for a random time defined by min and max

    Parameters:
        min (float): minimum time to sleep
        max (float): maximum time to sleep

    Returns:
        None
    '''
    #Time-to-sleep
    tts = np.random.random() #random number between 0 and 1
    tts *= (max - min) #now between 0 and (max-min)
    tts += min #now between min and max

    time.sleep(tts)

def get_paper_table(soup):
    '''
    Get's the table of academic papers from the html data. This contains their 'Title', number of 'Citations', 'Year' of publication, and the individual 'Paper url'
    which will be used by a later function to gather further details of the paper.

    Parameters:
        soup (bs4): parsed html data for the academics page
    '''
    
    l = list() #list to hold paper dictionaries 
    o = {} #dictionary for each paper

    allPapersContainer = soup.find("table",{"id":"gsc_a_t"}) #find the table of papers
    allPapers = allPapersContainer.find_all("tr") #extract all papers from within that panel 
    
    #allPapers[0:10]

    for paper in allPapers:
        #print(paper)
        #title
        try:
            o["Title"]=paper.find("a",{"class":"gsc_a_at"}).text
        except:
            o["Title"]=None

        #year
        try:
            o["Citations"]=paper.find("a",{"class":"gsc_a_ac gs_ibl"}).text
        except:
            o["Citations"]=None 
    
        #citations
        try:
            o["Year"]=paper.find("span",{"class":"gsc_a_h gsc_a_hc gs_ibl"}).text
        except:
            o["Year"]=None

        #paper-url
        try:
            search = paper.find("a","gsc_a_at").get("href")
            o["Paper url"]= "https://scholar.google.com" + search
        except:
            o["Paper url"]=None
            
        l.append(o)
        o={}
        
    paper_df = pd.DataFrame(l) #list of dictionaries to a dataframe
    paper_df.dropna(axis=0, inplace=True, ignore_index=True)
    print(f'{Fore.GREEN}-->{Style.RESET_ALL}', f'A list of all papers has been successfully stored.')

    return paper_df
    
def get_academic_table(soup):
    '''
    Get's the academics information from the html data. This will grab their name as 'Academic', university 'Affiliation', their total number of 'Citations', 
    their 'h-index' and 'i10-index', and then will breakdown their citations per year as far back as they are stored on Google Scholar.

    Parameters:
        soup (bs4): parsed html data for the academics page
    '''
    
    academic_df = pd.DataFrame(columns = ['Academic', 'Affiliation', 'Citations','h-index','i10-index'], index=[0])

    #Grabs the name and university affiliation from the top of the page (deals with capitalization, full names etc
    academic_df['Academic'][0] = soup.find("div",{"id":"gsc_prf_inw"}).text
    academic_df['Affiliation'][0] = soup.find("a",{"class":"gsc_prf_ila"}).text

    #Finds the html data associated with the info panel on the right
    sidePanel = soup.find("div",{"id":"gsc_rsb_cit"})
    table = sidePanel.find("tbody") #table with total citations
    rows = table.find_all("tr")

    for row in rows:
        field = row.find("a",{"class":"gsc_rsb_f gs_ibl"}).text
        
        try:
            academic_df[field][0] = row.find("td",{"class":"gsc_rsb_std"}).text 
        except:
            academic_df[field][0] = None
            

    #Gets citations per year from the hover-over info on the histogram
    #####
    #There is a complication here because not every year has citations, and year labels and values are not intrinsically linked.
    #Thus need to ensure the lists are the same length, and pair them up
    hist_labs = sidePanel.find_all("span", {"class":"gsc_g_t"})
    hist_vals = sidePanel.find_all("a", {"class":"gsc_g_a"}) 

    min_year = int(hist_labs[0].text)
    max_year = int(hist_labs[-1].text)
    num_years = int(max_year-min_year+1)

    
    #Years from min_year to max_year are indexed in the html from 28 to 1
    #If an index value is not present, then 0 citations
    #This loop stores only the index values for years with citation.
    real_year_index = list()
    for val in hist_vals:
        year_index = val.get("style")
        year_index = year_index.split(':')[-1] #splits style value at every : and keeps only the last one, the index
        real_year_index.append(int(year_index))    

    
    #List of all possible indices to compare against
    all_possible_indices = list()
    for x in reversed(range(num_years)):
        all_possible_indices.append(x+1)
        

    #Creating a binary list the length of all_possible_indices. If there WAS an index in the html, assign 1. If not, 0
    has_citations = list()
    for possible_index in all_possible_indices:
        if possible_index in real_year_index:
            has_citations.append(1)
        else:
            has_citations.append(0)

    
    #Now can run through the binary array and if 1, can assign relavnt value and if 0, will skip.
    #Will count through the histogram values inside the loop, since that list is smaller (as missing values were omitted)
    hist_val_counter = 0
    for idx, item in enumerate(has_citations):
        if item == 1:
            has_citations[idx] = hist_vals[hist_val_counter].text
            hist_val_counter += 1
        else:
            continue

    
    #Can now finally assign a column and value for each year and citation count
    for year, cite_count in zip(hist_labs, has_citations):
        academic_df["Citations in " + str(year.text)] = np.nan #initialize
        academic_df["Citations in " + str(year.text)] = cite_count
        
    
    print(f'{Fore.GREEN}-->{Style.RESET_ALL}', f'Total citation details have been successully stored.')

    
    return academic_df

def get_paper_details(paper_df, driver):
    '''
    Using the paper urls from the passed dataframe, gets additional details from this url using the passed webdriver and adds them to the paper_df dataframe. These
    additional details are: Google Scholar profile name, Publication date, Journal/Source/Conference (an entry will fit in only one of these catagories), Authors,
    Primary author, and Supporting authors.

    Parameters:
        paper_df (pandas df): dataframe of paper information
        driver (selenium): webdriver 

    Returns:
        detailed_paper_df (pandas df): original dataframe with additional columns
    '''
    
    print(f'{Fore.GREEN}-->{Style.RESET_ALL}', 'Additional information will now be gathered for each paper.')

    #Copy dataframe as to not overwrite data
    detailed_paper_df = paper_df.copy()
    
    # Want to obtain additonal info for each paper inc. primary author, coauthors, journal
    detailed_paper_df['Google Scholar profile name'] = np.nan
    detailed_paper_df['Publication date'] = np.nan
    detailed_paper_df['Journal'] = np.nan
    detailed_paper_df['Source'] = np.nan
    detailed_paper_df['Conference'] = np.nan
    detailed_paper_df['Authors'] = np.nan
    detailed_paper_df['Primary author'] = np.nan
    detailed_paper_df['Supporting authors'] = np.nan
    
    for idx, paper_url in enumerate(tqdm(paper_df['Paper url'], f'{Fore.GREEN}--> Papers{Style.RESET_ALL}', leave=None, ncols = 81)):
        driver.get(paper_url) #load webpage of paper
        random_sleep(1,6)

        resp = driver.page_source #grab html
        soup=BeautifulSoup(resp,'html.parser') #parse with bs4

        #Gets academics name from top of page. For consistency, will add as a feature so that if data is concatenated into a big set, 
        #it's easy to tell where the paper came from.
        name_body = soup.find("div",{"class":"gs_bdy_sb_sec"})
        name = name_body.find_all("a")[1].text
        detailed_paper_df['Google Scholar profile name'] = name
        #print(f'{Fore.RED}TEST: {name}{Style.RESET_ALL}')
        

        #This for loop deals with collecting the additional information from the articles specific page
        page_body = soup.find("div",{"id":"gsc_vcpb"})
        content = page_body.find_all("div",{"class":"gs_scl"})
        
        for item in content:
            field = item.find("div",{"class":"gsc_oci_field"}).text #gets the name of the field 

            if field in ['Publication date', 'Journal', 'Authors', 'Source', 'Conference']: #ignore fields that are not in this list
                try:
                    detailed_paper_df[field][idx] = item.find("div",{"class":"gsc_oci_value"}).text
                        
                except:
                    detailed_paper_df[field][idx] = 0
            
            else:
                continue

        #To prevent errors with lack of author, i.e. for a patent
        try:
            detailed_paper_df['Authors'][idx] = detailed_paper_df['Authors'][idx].split(', ') #split authors string into an actual list of authors
            detailed_paper_df['Primary author'][idx] = detailed_paper_df['Authors'][idx][0] #first author is primary
        except:
            detailed_paper_df['Authors'][idx] = np.nan
            detailed_paper_df['Primary author'][idx] = np.nan

        #Prevents error if paper has only one author
        try:
            if len(detailed_paper_df['Authors'][idx]) > 1:
                detailed_paper_df['Supporting authors'][idx] = detailed_paper_df['Authors'][idx][1:] #supporting are non first
        except:
            detailed_paper_df['Supporting authors'][idx] = np.nan
            

    return detailed_paper_df

def format_dfs(paper_df, academic_df):
    '''
    Appropriately formats the paper and academic dataframes. It standardises the publication date, so it is always in the form YYYY/mm/dd, generates a unique id for each
    paper and academic using a hash created from multiple columns in the data, and corrects the discrepancy in formatting for a lack of citations, from "" to np.nan. 

    Parameters:
        paper_df (pandas df): dataframe containing paper info
        academic_df (pandas df): dataframe containing academic info

    Returns:
        formatted_paper_df (pandas df)
        formatted_academic_df (pandas df)
    '''

    #Copy dataframes as to not overwrite data
    formatted_paper_df = paper_df.copy()
    formatted_academic_df = academic_df.copy()

    #Standardise 'Publication date'
    formatted_paper_df['Publication date'] = formatted_paper_df['Publication date'].apply(format_date)
    
    #Generate unique IDs
    try:
        formatted_paper_df['PaperID'] = formatted_paper_df[['Title', 'Publication date', 'Primary author']].sum(axis=1).apply(generate_id)
    except:
        formatted_paper_df['PaperID'] = formatted_paper_df[['Title', 'Publication date']].sum(axis=1).apply(generate_id) #incase of no author
        
    formatted_academic_df['AcademicID'] = formatted_academic_df[['Academic', 'Affiliation']].sum(axis=1).apply(generate_id)

    #Move IDs to first col
    temp_cols = formatted_paper_df.columns.to_list()
    index = formatted_paper_df.columns.get_loc('PaperID')
    new_cols = temp_cols[index:index+1] + temp_cols[0:index] + temp_cols[index+1:]
    formatted_paper_df = formatted_paper_df[new_cols]

    temp_cols = formatted_academic_df.columns.to_list()
    index = formatted_academic_df.columns.get_loc('AcademicID')
    new_cols = temp_cols[index:index+1] + temp_cols[0:index] + temp_cols[index+1:]
    formatted_academic_df = formatted_academic_df[new_cols]

    #Changing lack of citations to correctly be nan
    formatted_paper_df[formatted_paper_df['Citations'] == '']['Citations'] = np.nan
    
    print(f'{Fore.GREEN}-->{Style.RESET_ALL}', "Dataframes appropriately formatted.")
    
    return formatted_paper_df, formatted_academic_df

def click_show_more(driver):
    '''
    Ensures all papers are shown on the page by scrolling to the bottom and clicking "show more" until it cannot anymore, i.e. all papers are shown.

    Parameters:
        driver (selenium): web driver
    '''

    while 1==1:
        temp = driver.page_source #to check if the html button is disabled
        
        show_more = driver.find_element(By.ID, "gsc_bpf_more")
        if show_more.is_enabled():
            ActionChains(driver)\
                .scroll_to_element(show_more)\
                .perform()
    
            time.sleep(1)
            show_more.click()
            time.sleep(1)
        else:
            print(f'{Fore.GREEN}-->{Style.RESET_ALL}', "All papers have been loaded.")
            break

def searches_from_file(filename):
    '''
    Reads multiple search queries to be gathered from a text file named 'filename'. It reads line by line and stores each as an entry in a list, which is returned.

    Parameters:
        filename (str): name of text file containing Google Scholar profile search queries

    Returns:
        search_list (list str): list of strings containing search queries
    '''

    search_list = list()
    
    with open(filename) as file:
        Lines = file.readlines()
        for line in Lines:
            if line == '\n': #skips line if it is empty
                continue

            search_list.append(line.strip())

    return search_list

def get_current_datetime():
    '''
    Get's the current date and time using the datetime library and returns as a string

    Parameters:

    Returns:
        dt (str): string form of datetime object 
    '''

    now = datetime.now()

    dt = now.strftime("%Y-%m-%d")

    return dt


def dfs_by_query(search): #add name + university 
    '''
    Using selenium, scrapes html data from Google Scholar url, parses with bs4, and then extracts information for the Paper and Academic tables, which are stored in a pandas df. 
    This is the core function, at almost the highest level. It will be used in a loop to gather data for multiple search queries.

    Parameters:
        first_name (str): first name
        last_name (str): last name

    Returns:
        paper_df (pandas df): a dataframe containing paper information
        academic_df (pandas df): a dataframe containing academic information
    '''

    url = get_scholar_search_url(search) #gets Google Scholar url for searched name
    
    driver=webdriver.Chrome(options=options) #open chromium web driver
    print(f'{Fore.GREEN}-->{Style.RESET_ALL}', "Chrome driver launched...")
    
    driver.get(url) #load desired url with chromium
    driver.maximize_window() #maximize window
    time.sleep(1) #wait 1s to ensure webpage fully loads

    #This loads to the Google Scholar seach page. The results are shown on the page with the most relevant user at the top, which we click
    driver.find_element(By.CLASS_NAME, 'gs_ai_pho').click()
    time.sleep(1)

    #This clicks the 'Year' header which loads the page sorted by year instead of citation cout
    driver.find_element(By.LINK_TEXT, "YEAR").click()
    time.sleep(1)

    #Ensure all articles are listed by scrolling to the bottom of the page and clicking "Show More"
    click_show_more(driver)

    #Now scrape all html data and parse with bs4
    resp = driver.page_source 
    soup=BeautifulSoup(resp,'html.parser')

    
    # GET PAPER TABLE 
    paper_df = get_paper_table(soup)

    
    # GET ACADEMIC TABLE 
    academic_df = get_academic_table(soup)

    
    # GET PAPER DETAILS 
    paper_df = get_paper_details(paper_df, driver)

    
    driver.close() #close chromium driver
    print(f'{Fore.GREEN}-->{Style.RESET_ALL}', "Chrome driver successfully closed.")

    
    # APPROPRIATE FORMATTING
    f_paper_df, f_academic_df = format_dfs(paper_df, academic_df)

    
    # EXPORT DATAFRAMES TO CSV
    directory = 'Individual sheets\\'
    parent_dir = os.getcwd()
    path = os.path.join(parent_dir, directory)

    os.makedirs(path, exist_ok=True) #creates subdirectory if it doesn't already exist

    current_datetime = get_current_datetime()

    f_paper_df.to_csv(path + f'{search}_papers {current_datetime}.csv', index=False, index_label=False)
    print(f'{Fore.GREEN}-->{Style.RESET_ALL}', f'Successfully exported "{search} papers {current_datetime}.csv"')

    f_academic_df.to_csv(path + f'{search}_info {current_datetime}.csv', index=False, index_label=False)
    print(f'{Fore.GREEN}-->{Style.RESET_ALL}', f'Successfully exported "{search} info {current_datetime}.csv"')
    
    return f_paper_df, f_academic_df

## Driver code for program

#Initialize dataframes
paper_df = pd.DataFrame()
academic_df = pd.DataFrame()

#Generate search list
Searches = searches_from_file("search queries.txt")
search_length = len(Searches)

#Initlaise list of query errors
errors = list()

print(f'{Fore.BLUE}─{Style.RESET_ALL}' * 81)
title = '''\
   _____      __          __                                                     
  / ___/_____/ /_  ____  / /___ ______      ___________________ _____  ___  _____
  \__ \/ ___/ __ \/ __ \/ / __ `/ ___/_____/ ___/ ___/ ___/ __ `/ __ \/ _ \/ ___/
 ___/ / /__/ / / / /_/ / / /_/ / /  /_____(__  ) /__/ /  / /_/ / /_/ /  __/ /    
/____/\___/_/ /_/\____/_/\__,_/_/        /____/\___/_/   \__,_/ .___/\___/_/     
                                                             /_/                 '''
print(f'{Fore.BLUE}{title}{Style.RESET_ALL}')
print(f'{Fore.BLUE}─{Style.RESET_ALL}' * 81)

print(f'''\
      {Fore.BLUE}v1.1{Style.RESET_ALL}
      Created by Ted Binns
      
      This program scrapes academic and paper details from the Google Scholar
      profile pages associated with search queries that are entered in the
      file "search queries.txt".

      For more information on using this program, please see README.txt ''') 

for idx, search in enumerate(Searches):
    print(f'{Fore.GREEN}─{Style.RESET_ALL}' * 81) 
    print(f'Profile search {idx+1}/{search_length}: {Fore.GREEN}{search}{Style.RESET_ALL}')
    print(f'{Fore.GREEN}─{Style.RESET_ALL}' * 81) 
    
    try:
        p_df, a_df = dfs_by_query(search)
    except:
        print(f'{Fore.RED}An error occured with this query: {Style.RESET_ALL}"{search}"')
        errors.append(search)
        continue
    
    paper_df = pd.concat([paper_df, p_df], join='outer', axis=0)
    academic_df = pd.concat([academic_df, a_df], join='outer', axis=0)

    print(f'{Fore.GREEN}─{Style.RESET_ALL}' * 81) 

    current_datetime = get_current_datetime()
    print(f'{Fore.BLUE}--> Updating main file output with all previous search queries...{Style.RESET_ALL}') 
    paper_df.to_csv(f'all papers {current_datetime}.csv', index=False, index_label=False)
    academic_df.to_csv(f'all academics {current_datetime}.csv', index=False, index_label=False)

print(f'{Fore.GREEN}─{Style.RESET_ALL}' * 81) 
print(f'{Fore.BLUE}─{Style.RESET_ALL}' * 81) 
print(f'{Fore.BLUE}ALL TASKS COMPLETE{Style.RESET_ALL}')
print(f'{Fore.BLUE}─{Style.RESET_ALL}' * 81) 

if len(errors) > 0:
    print(f'{Fore.RED}Errors occurred with the following queries:{Style.RESET_ALL}')
    for e in errors:
        print(f'{Fore.RED}-->{Style.RESET_ALL} {e}')