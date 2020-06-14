# -*- coding: utf-8 -*-
"""
Created on Fri Jun 12 21:41:41 2020

@author: TJ

This script needs an installation of gitpython.  To install it, run

conda install -c conda-forge gitpython

"""

import datetime, os
import pandas as pd
pd.options.display.max_columns = 20
from git import Repo

def read_all_zcta_data(data_dir = '../coronavirus-data/', historical_data_dir = 'historical_data/'):
    '''
    Read all the historical zcta data

    Parameters
    ----------
    data_dir : str, optional
        Folderpath to the coronavirus-data repository. The default is 
        '../coronavirus-data/'.
    historical_data_dir : str, optional
        Folderpath to the historical data. The default is 'historical_data/'.

    Returns
    -------
    data : pandas.DataFrame
        Formatted DataFrame of all historical data along with timestamps of
        when the data was created.

    '''
    # Access the coronavirus-data repo
    repo = Repo(data_dir)
    
    # Get information about the commits
    commit_history = pd.DataFrame({'GIT_COMMIT': repo.iter_commits()})
    commit_history['COMMIT'] = commit_history['GIT_COMMIT'].astype(str)
    commit_history['COMMIT_FIRST7'] = commit_history['COMMIT'].str[:7]
    commit_history['MESSAGE'] = commit_history['GIT_COMMIT'].apply(lambda x: x.message)
    commit_history['COMMITTED_DATETIME'] = commit_history['GIT_COMMIT'].apply(lambda x: x.committed_datetime)
    
    # Only keeping commits that possibly have a date in it
    commit_history = commit_history[commit_history['MESSAGE'].str.contains('[0-9].+[0-9]')]
    
    # Try to extract a date from the commit message
    # TODO: Compare to the commit message to make sure what we got was reasonable
    commit_history['DATA_DATE_STR'] = commit_history['MESSAGE'].str.extract('([0-9][0-9\./]+[0-9])')[0]
    commit_history['DATA_DATE_STR'] = commit_history['DATA_DATE_STR'].str.replace('\.', '/')
    
    # Convert the date into a datetime object
    commit_history['DATA_DATE'] = commit_history['DATA_DATE_STR'].apply(datestring2020_to_datetime)
    
    # For each data date, choose the row with the most recent commit
    commit_history = commit_history.sort_values('COMMITTED_DATETIME', ascending=False)
    commit_history = commit_history.drop_duplicates('DATA_DATE')
    
    # Get the file names along with information on how to tie them back to the 
    # commits
    hist_data_files = os.listdir(historical_data_dir)
    hist_data_files.sort()
    historical_data = pd.DataFrame({'FILENAME': hist_data_files})
    historical_data['FILEPATH'] = historical_data_dir + historical_data['FILENAME']
    historical_data['COMMIT_FIRST7'] = historical_data['FILENAME'].str.split('.').str[-2]
    historical_data['FILETYPE'] = historical_data['FILENAME'].str.split('.').str[0]
    
    # If data-by-modzcta and tests-by-zcta show up on the same commit, choose 
    # data-by-modzcta
    historical_data = historical_data.sort_values('FILETYPE')
    historical_data = historical_data.drop_duplicates('COMMIT_FIRST7')
    
    # Attach the filepath to the commit history
    commit_history = pd.merge(left=historical_data, right=commit_history, on='COMMIT_FIRST7')
    
    # Read all the csvs as pandas DataFrames
    commit_history['DATA'] = commit_history.apply(lambda x: read_zcta_data(x['FILEPATH'], x['DATA_DATE']), axis=1)
    
    # Final Data
    data = pd.concat(list(commit_history['DATA']))
    
    # Many of the older records have a null NEIGHBORHOOD_NAME and BOROUGH_GROUP.
    # Fill in the old data with the newer data.
    zcta_info = data[['MODIFIED_ZCTA', 'NEIGHBORHOOD_NAME', 'BOROUGH_GROUP', 'DATA_DATE']].dropna()
    # Take the most recent nieghborbhood name and borough group
    zcta_info = zcta_info.sort_values('DATA_DATE', ascending=False)
    zcta_info = zcta_info[['MODIFIED_ZCTA', 'NEIGHBORHOOD_NAME', 'BOROUGH_GROUP']].drop_duplicates('MODIFIED_ZCTA')
    # Remove this fields from the original data
    data = data[[x for x in data if x not in ['NEIGHBORHOOD_NAME', 'BOROUGH_GROUP']]]
    # Attach the new values to the data
    data = pd.merge(left=data, right=zcta_info, how='left')
    
    # The POP_DENOMINATOR field is null for the older data
    # The POP_DENOMINATOR is the same for all csvs which contain it.  Attach
    # This to the older data.
    pop_denominator = data[['MODIFIED_ZCTA', 'POP_DENOMINATOR']].drop_duplicates()
    pop_denominator = pop_denominator[pop_denominator['POP_DENOMINATOR'].notnull()]
    assert((~pop_denominator['MODIFIED_ZCTA'].duplicated()).all())
    data = data[[x for x in data if x!='POP_DENOMINATOR']]
    # Attach POP_DENOMINATOR to all the data
    data = pd.merge(left=data, right=pop_denominator, on='MODIFIED_ZCTA', how='left')

    return data

def read_zcta_data(filepath, data_date):
    '''
    Get formatted version of the zcta data.
    
    100*COVID_CASE_COUNT/TOTAL = PERCENT_POSITIVE

    New data doesn't have this, so we create it using
    TOTAL = 100*COVID_CASE_COUNT/PERCENT_POSITIVE


    Parameters
    ----------
    filepath : str
        Path to the file to read

    Returns
    -------
    data : pandas.DataFrame
        Standardized version of the data

    '''
    data = pd.read_csv(filepath)
    data.columns = data.columns.str.upper()
    data = data.rename(columns = {'POSITIVE': 'COVID_CASE_COUNT', 
                                  'ZCTA_CUM.PERC_POS': 'PERCENT_POSITIVE',
                                  'MODZCTA_CUM_PERC_POS': 'PERCENT_POSITIVE',
                                  'MODZCTA': 'MODIFIED_ZCTA'})
    
    # The new data doesn't have a TOTAL column.  Create this column when it
    # doesn't exist
    if 'TOTAL' not in data:
        data['TOTAL'] = (100*data['COVID_CASE_COUNT']/data['PERCENT_POSITIVE']).apply(lambda x: round(x) if pd.notnull(x) else x)
        
    data['DATA_DATE'] = data_date
    return data
    
def datestring2020_to_datetime(x):
    '''
    Convert a string of the form MM/DD into a datetime object assuming that
    the year is 2020
    '''
    date = datetime.datetime.strptime(x, '%m/%d')
    date = datetime.datetime(2020, date.month, date.day)
    return date




