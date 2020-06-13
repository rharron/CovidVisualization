# -*- coding: utf-8 -*-
"""
Created on Fri Jun 12 21:41:41 2020

@author: TJ
"""

import pandas as pd
from git import Repo

data_dir = '../coronavirus-data/'
repo = Repo(data_dir)

commit_history = pd.DataFrame({'GIT_COMMIT': repo.iter_commits()})
commit_history['COMMIT'] = commit_history['GIT_COMMIT'].astype(str)
commit_history['COMMIT_FIRST7'] = commit_history['COMMIT'].str[:7]
commit_history['MESSAGE'] = commit_history['GIT_COMMIT'].apply(lambda x: x.message)

