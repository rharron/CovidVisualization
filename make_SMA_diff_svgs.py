#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 22 17:39:15 2020

@author: Rob Harron

This script plots the moving average of the day-to-day difference of Covid
case rates from the first date for which it makes sense.

The script creates a collection of svg files, one for each day.
"""

import pandas as pd

import svg_utilities
import clean_data

#svg_utilities.initalize_template_file(colormap='coolwarm')

# Set this to a different field to plot that field's moving average of diffs
plot_field = 'COVID_CASE_RATE'
number_of_days = 3 # Number of days to average
pfdiff = plot_field + '_DIFF'
pfd = plot_field + '_DIFF_SMA%s'%(number_of_days)

# Get data and clean it a bit more and make into a multiindex
data = clean_data.read_all_zcta_data()
data.dropna(subset=['MODIFIED_ZCTA'], inplace=True)
data = data.astype({'MODIFIED_ZCTA' : int})

data.set_index(['MODIFIED_ZCTA','DATA_DATE'], inplace=True)
data.sort_index(inplace=True)

# Compute discrete differences per ZCTA and simple moving average
data[pfdiff] = data.groupby('MODIFIED_ZCTA')[plot_field].diff()
data[pfd] = data.groupby('MODIFIED_ZCTA')[pfdiff].rolling(window=3).mean().droplevel(0)

# Get appropriate date range (starting 2020-05-20)
date1 = pd.Timestamp('2020-05-20') #First date that makes sense
date_indices = data.index.levels[1][data.index.levels[1] >= date1]

# We impose a max_rate threshold below the max and output showing only
# a handful of data points are beyond the threshhold
max_rate = 50
min_rate = -50
relevant_data = data[data.index.get_level_values(1).isin(date_indices)][pfd]
print("There are %s data points above the threshhold; they will be cut off"%(len(relevant_data[relevant_data >= max_rate])))

# Generate the svgs
svg_utilities.mi_generate_multiple_svgs_from_one_dataframe(data, plot_field=pfd, legend_title='SMA%s of Change in Covid Case Rate per 100k'%(number_of_days), filename_prefix=pfd + '/NYC', colormap='coolwarm', dates=date_indices, min_rate=min_rate, max_rate=max_rate, verbose=True)
