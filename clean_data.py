# -*- coding: utf-8 -*-
"""
Created on Fri Jun 12 21:41:41 2020

@author: TJ

This script needs an installation of gitpython.  To install it, run

conda install -c conda-forge gitpython

100*COVID_CASE_COUNT/TOTAL = PERCENT_POSITIVE

New dadta doesn't have this, so we create it using
TOTAL = 100*COVID_CASE_COUNT/PERCENT_POSITIVE

"""

# TODO: Get a date date onto the data
# TODO: Fill in NEIGHBORHOOD_NAME and BOROUGH_GROUP when possible

import datetime, os
import pandas as pd
from git import Repo

data_dir = '../coronavirus-data/'
repo = Repo(data_dir)

commit_history = pd.DataFrame({'GIT_COMMIT': repo.iter_commits()})
commit_history['COMMIT'] = commit_history['GIT_COMMIT'].astype(str)
commit_history['COMMIT_FIRST7'] = commit_history['COMMIT'].str[:7]
commit_history['MESSAGE'] = commit_history['GIT_COMMIT'].apply(lambda x: x.message)
commit_history['COMMITTED_DATETIME'] = commit_history['GIT_COMMIT'].apply(lambda x: x.committed_datetime)

# Only keeping commits that possibly have a date in it
commit_history = commit_history[commit_history['MESSAGE'].str.contains('[0-9].+[0-9]')]


commit_history['DATA_DATE_STR'] = commit_history['MESSAGE'].str.extract('([0-9][0-9\./]+[0-9])')[0]
commit_history['DATA_DATE_STR'] = commit_history['DATA_DATE_STR'].str.replace('\.', '/')

def datestring_to_datetime(x):
    date = datetime.datetime.strptime(x, '%m/%d')
    date = datetime.datetime(2020, date.month, date.day)
    return date

# TODO: Compare to the commit message to make sure what we got was reasonable
# Make sure message quality issues are taken care of
commit_history['DATA_DATE'] = commit_history['DATA_DATE_STR'].apply(datestring_to_datetime)

# Choose the most recent commit for every data date
commit_history = commit_history.sort_values('COMMITTED_DATETIME', ascending=False)
commit_history = commit_history.drop_duplicates('DATA_DATE')

# Get the file names
historical_data = pd.DataFrame({'FILENAME': os.listdir('historical_data')})
historical_data['FILEPATH'] = 'historical_data/' + historical_data['FILENAME']
historical_data['COMMIT_FIRST7'] = historical_data['FILENAME'].str.split('.').str[-2]
historical_data['FILETYPE'] = historical_data['FILENAME'].str.split('.').str[0]
# If data-by-modzcta and tests-by-zcta show up on the same commit, choose data-by-modzcta
historical_data = historical_data.sort_values('FILETYPE')
historical_data = historical_data.drop_duplicates('COMMIT_FIRST7')


# Attach the filepath to the commit history
commit_history = pd.merge(left=historical_data, right=commit_history, on='COMMIT_FIRST7')

def read_zcta_data(filepath):
    '''
    Get formatted version of the data

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
    if 'TOTAL' not in data:
        data['TOTAL'] = (100*data['COVID_CASE_COUNT']/data['PERCENT_POSITIVE']).apply(lambda x: round(x) if pd.notnull(x) else x)
    return data
commit_history['DATA'] = commit_history['FILEPATH'].apply(read_zcta_data)
commit_history['COLUMNS'] = commit_history['DATA'].apply(lambda x: tuple(sorted(x)))


commit_history.groupby(by=['FILETYPE', 'COLUMNS']).size()

# Final Data
data = pd.concat(list(commit_history['DATA']))

