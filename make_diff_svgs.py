#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 21 18:09:12 2020

@author: Rob Harron

This script plots the day-to-day difference of Covid case rates from the first
date for which it makes sense (i.e. such that starting at the previous day,
there is data for each subsequent day.)

The script creates a collection of svg files, one for each day.
"""

import pandas as pd

import svg_utilities
import clean_data

svg_utilities.initalize_template_file(colormap='coolwarm')

#Set this to a different field to plot that field's diffs
plot_field = 'COVID_CASE_RATE'
pfd = plot_field + '_DIFF'

# Get data and clean it a bit more and make into a multiindex
data = clean_data.read_all_zcta_data()

# Compute discrete differences per ZCTA
data[pfd] = data.groupby('MODIFIED_ZCTA')[plot_field].diff()

# Get appropriate date range (starting 2020-05-19)
date0 = data.index.levels[1][0]; print("Ignore", date0) #first date
date1 = pd.Timestamp('2020-05-19') #First date that makes sense
date_indices = data.index.levels[1][data.index.levels[1] >= date1]

# We impose a max_rate threshold below the max and output showing only
# a handful of data points are beyond the threshhold
max_rate = 50
min_rate = -50
relevant_data = data[data.index.get_level_values(1).isin(date_indices)][pfd]
print("There are %s data points above the threshhold; they will be cut off"%(len(relevant_data[relevant_data >= max_rate])))

# Generate the svgs
svg_utilities.mi_generate_multiple_svgs_from_one_dataframe(data.drop(index=date0, level=1), plot_field=pfd, legend_title='Change in Covid Case Rate per 100k', filename_prefix=pfd + '/NYC', colormap='coolwarm', dates=date_indices, min_rate=min_rate, max_rate=max_rate, verbose=True)
