# -*- coding: utf-8 -*-
"""
Created on Fri Jun 12 21:41:41 2020

@author: TJ

This script needs an installation of gitpython.  To install it, run

conda install -c conda-forge gitpython

"""

import datetime
from io import StringIO
import pandas as pd
from git import Repo
from git import GitCommandError

def read_all_zcta_data(data_dir = '../coronavirus-data/'):
    '''
    Read all the historical zcta data

    Parameters
    ----------
    data_dir : str, optional
        Folderpath to the coronavirus-data repository. The default is 
        '../coronavirus-data/'.

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
    
    # Obtain the data from the git repo, only for dates where it exists
    commit_history = commit_history[commit_history['DATA_DATE'] >= '2020-04-01']
    commit_history['DATA'] = commit_history.apply(lambda x: read_zcta_data_from_git(repo, x['COMMIT_FIRST7'], x['DATA_DATE']), axis=1)
    
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
    
    # The COVID_CASE_RATE field is NaN for the older data, too
    # Compute it and attach it.
    data['COVID_CASE_RATE'].fillna(100000 * data['COVID_CASE_COUNT'] / data['POP_DENOMINATOR'], inplace=True)
    
    # Fine cleaning the data
    # Two dates have an extra 99999 ZCTA
    data.drop(data[data['MODIFIED_ZCTA']==99999].index, inplace=True)
    # 2020-04-10 has extra copy of previous day's data for ZCTA 11697
    data.drop(data[(data['DATA_DATE']=="2020-04-10") & (data['MODIFIED_ZCTA']==11697) & (data['COVID_CASE_COUNT']==52)].index, inplace=True)
    # Drop data on 2020-04-26
    data = data[data['DATA_DATE']!='2020-04-26']
    
    
    
    return data

def read_zcta_data_from_git(repo, commit7, data_date):
    '''
    Get formatted version of the zcta data using gitpython.
    
    100*COVID_CASE_COUNT/TOTAL = PERCENT_POSITIVE

    New data doesn't have this, so we create it using
    TOTAL = 100*COVID_CASE_COUNT/PERCENT_POSITIVE

    Parameters
    ----------
    repo : git.Repo
        The git repo from which to retrieve zcta data.
    
    commit7 : str
        First 7 characters of the hash of the commit from which to retrieve
        zcta data.
        
    data_date : pandas.Timestamp
        Date of the commit referred to by commit7.

    Returns
    -------
    data : pandas.DataFrame.
        Standardized version of the retrieved data.

    '''
    # First try to get data from data-by-modzcta.csv. If it's not there, get
    # it from tests-by-zcta.csv
    try:
        data = pd.read_csv(StringIO(repo.git.show(commit7 + ':./data-by-modzcta.csv')))
    except GitCommandError:
        data = pd.read_csv(StringIO(repo.git.show(commit7 + ':./tests-by-zcta.csv')))
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
