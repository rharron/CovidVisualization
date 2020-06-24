#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on June 2020

@author: Rob Harron

Python functions for creating svg visualizations of the the NYC Health
Department's Covid-19 data.

"""


import os, re
import locale
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# The fields present in the (most recent) NYC Covid-19 data tables
ZCTA_fields = ['Case Rate per 100k',
    'ZIP Code',
    'Neighborhood',
    'Case Count',
    'Rate per 100,000',
    'Percent of people tested who tested positive',
    'Deaths',
    'Death rate per 100,000']

# Conversion dictionary between the svg template's name for the data and the
# databases name for it.
fields_to_data_by_modzcta_dict = {
    'Case Rate per 100k' : 'COVID_CASE_RATE',
    'Neighborhood' : 'NEIGHBORHOOD_NAME',
    'Case Count' : 'COVID_CASE_COUNT',
    'Rate per 100,000' : 'COVID_CASE_RATE',
    'Percent of people tested who tested positive' : 'PERCENT_POSITIVE',
    'Deaths' : 'COVID_DEATH_COUNT',
    'Death rate per 100,000' : 'COVID_DEATH_RATE'
    }

# Some zip codes are part of the same ZCTA (and listed under the first one)
# This dictionary is needed in outputting the aria labels in the svg.
double_zips = {
    10001 : '10001, 10118',
    10019 : '10019, 10020',
    10075 : '10075, 10162',
    11004 : '11004, 11005',
    11211 : '11211, 11249',
    11217 : '11217, 11243'
    }

def rgb1to256(rgb1):
    r'''
    A helper function that converts from matplotlibs rgb format to svg's.

    Parameters
    ----------
    rgb1 : tuple (or listable)
        a tuple representing an rgb value with entries between 0 and 1.

    Returns
    -------
    tuple
        a tuple representing the corresponding rgb value with entries between
        0 and 255.

    '''
    return tuple(np.ceil(256 * c).astype('int') - 1 for c in rgb1[:3])

def initalize_template_file(colormap='rainbow'):
    r'''
    Creates template files for use with 'mi_generate_svg_from_day_dataframe'.
    
    This function only needs to be run once for each colormap used.

    Parameters
    ----------
    colormap : str, optional
        The name of a standard matplotlib color map.
        The default is 'rainbow'.

    Returns
    -------
    None.
        Creates the file 'template_colormap.svg' which is used by
        'mi_generate_svg_from_day_dataframe' to create full svg files.

    '''
    # Some regex used in creating the legend
    offset_re = re.compile("\".*?\"")
    rgb_re = re.compile('rgb\([0-9]*, [0-9]*, [0-9]*\)')
    
    with open("template_" + colormap + ".svg", 'w') as outfile:
        # Get nychealth's map file, it's all one line
        map_file = open('NYCmap06-12.svg', 'r')
        LINE = map_file.readline()
        map_file.close()
        
        # Break it up into segments based on ZCTA
        tokens = LINE.split("<path aria-label=")
        
        # Adjust the legend colours in the initial segment
        cm = eval("plt.cm." + colormap)
        header_delim = "<stop offset="
        header_tokens = tokens[0].split(header_delim)
        outfile.write(header_tokens[0])
        step = 1/21
        for i in range(22):
            val = step * i
            this_rgb = rgb1to256(cm(val))
            header_tokens[i+1] = header_delim + rgb_re.sub("rgb%s"%(this_rgb,), offset_re.sub("\"%s\""%(val), header_tokens[i+1], 1), 1)
            if i == 21:
                header_tokens[i+1] += "\n"
            outfile.write(header_tokens[i+1])
        delim = 'role='
        for token in tokens[1:-1]:
            outfile.write(delim + token.split(delim)[1] + "\n")
        delimend = "stroke-width=\"0.5\"></path>"
        token, endgame = tokens[-1].split(delimend)
        outfile.write(delim + token.split(delim)[1] + delimend + "\n")
        outfile.write(endgame)
    return

def mi_generate_svg_from_day_dataframe(zcta_data, plot_field='COVID_CASE_RATE', legend_title=None, filename_prefix='NYC', min_rate=551, max_rate = 4429.24, colormap='rainbow'):
    r'''
    Generate a map of NYC (by ZCTA, in svg format) colored according to value
    of some data and a specified color palette.

    Parameters
    ----------
    zcta_data : pandas.DataFrame
        A pandas.DataFrame with multiindex whose level 0 are the ZCTA and
        whose level 1 is a pandas.Timestamp representing the date of the data.
    plot_field : str, optional
        The column name from zcta_data whose data is to be plotted.    
        The default is 'COVID_CASE_RATE'.
    legend_title : str, optional
        The title to place in the svg's legend
        The default is None. The legend title is then set to 'plot_field'
    filename_prefix : str, optional
        A prefix for the file name. Allows for file to be output in another
        directory.
        The default is 'NYC'.
    min_rate : float (or other numerical type), optional
        The value that maps to the leftmost colormap color. Lower values will
        map to the same color.
        The default is 551.
    max_rate : float (or other numerical type), optional
        The value that maps to the rightmost colormap color. Higher values
        will map to the same color.
        The default is 4429.24.
    colormap : str, optional
        The name of a standard matplotlib color map.
        The default is 'rainbow'.

    Returns
    -------
    None.
        Creates an svg file that plots the data from the specified field on
        a map of NYC using the specified color palette.

    '''
    # Preparations for later use
    rgb_re = re.compile('rgb\([0-9]*, [0-9]*, [0-9]*\)')
    delta_values = max_rate - min_rate
    locale.setlocale(locale.LC_ALL, '')
    if legend_title is None:
        legend_title = plot_field
    
    # Get colormap from argument
    cm = eval("plt.cm." + colormap)
    
    # Set output filename based on colormap and 'DATA_DATE" value (there should only be one)
    date = zcta_data.index[0][1]
    filename =  filename_prefix + "_" + plot_field + "_" + colormap + "_" + date.strftime("%Y-%m-%d-%H-%M-%S") + ".svg"
    
    with open(filename, 'w') as outfile:
        # Open the svg template file and write out the initial segment
        template_file = open('template_' + colormap + '.svg', 'r')
        template_out = template_file.readline()
        outfile.write(template_out)
        
        # For each ZCTA, write out an aria-label with relevant data
        # and then the corresponding template block with this date's rgb value
        zips = zcta_data.index.levels[0]
        for zcta in zips:
            # First two data fields need custom handling
            field = ZCTA_fields[0]
            out = "<path aria-label=\"" + field + ": %s"%(zcta_data.loc[zcta, date][fields_to_data_by_modzcta_dict[field]]) + ";\n"
            outfile.write(out)
            out = "\tZIP Code: %s;\n"%(double_zips[zcta] if zcta in double_zips else zcta)
            outfile.write(out)
            
            # Process and write out the remaining data fields
            for i in range(2, len(ZCTA_fields)):
                field = ZCTA_fields[i]
                out = "\t" + field + ": %s"%(zcta_data.loc[zcta, date][fields_to_data_by_modzcta_dict[field]]) + ";\n"
                if i == len(ZCTA_fields) - 1:
                    out = out[:-2] + "\"\n"
                outfile.write(out)
                
            # Compute rgb value based on plotted field's value
            rate = zcta_data.loc[zcta, date][plot_field]
            rate01 = (rate - min_rate) / delta_values
            this_rgb = rgb1to256(cm(rate01))
            template_out = template_file.readline()
            # Update template's rgb value with computed one
            template_out = rgb_re.sub("rgb%s"%(this_rgb,), template_out)
            outfile.write(template_out)
        
        # Write out end segment of the file from the template, adding in date and max-min info
        template_out = template_file.readline()
        if os.name == 'nt':
            # On Windows
            date_str = "Date: %s"%(date.strftime("%b %#d, %Y"))
        else:
            date_str = "Date: %s"%(date.strftime("%b %-d, %Y"))
            
        legend_title_str = "><tspan x=\"0\" dy=\"-1.2em\">"+ date_str + "</tspan><tspan x=\"0\" dy=\"1.4em\">" + legend_title + "</tspan>"
        template_out = re.sub(">Case Rate per 100k", legend_title_str, template_out)
        legend_title_str = "\'" + date_str + "; " + legend_title
        template_out = re.sub("\'Case Rate per 100k", legend_title_str, template_out)
        minstr = locale.format_string("%.2f", min_rate, grouping=True)
        maxstr = locale.format_string("%.2f", max_rate, grouping=True)
        template_out = template_out.replace("551 to 4,429", minstr + " to " + maxstr)
        template_out = template_out.replace("551<", minstr + "<")
        template_out = template_out.replace("4,429<", maxstr + "<")
        outfile.write(template_out)
        template_file.close()
    return

def mi_generate_multiple_svgs_from_one_dataframe(data, plot_field='COVID_CASE_RATE', legend_title=None, filename_prefix='NYC', colormap='rainbow', dates=None, min_rate=None, max_rate=None, verbose=True):
    r'''
    Generate a collection of maps of NYC (by ZCTA, in svg format), one for
    each specified date, colored according to value of some data and a
    specified color palette.

    Parameters
    ----------
    data : pandas.DataFrame
        A pandas.DataFrame with multiindex whose level 0 are the ZCTA and
        whose level 1 are pandas.Timestamp's representing the dates of the
        data.
    plot_field : str, optional
        The column name from zcta_data whose data is to be plotted.    
        The default is 'COVID_CASE_RATE'.
    legend_title : str, optional
        The title to place in the legends of the svg's
        The default is None. The legend title is then set to 'plot_field'
    filename_prefix : str, optional
        A prefix for the file names. Allows for file to be output in another
        directory.
        The default is 'NYC'.
    colormap : str, optional
        The name of a standard matplotlib color map.
        The default is 'rainbow'.
    dates : pandas.DatetimeIndex
        The dates for which an svg should be created.
        The default is None. The dates are then taken from the level 1 index
        of 'data'.
    min_rate : float (or other numerical type), optional
        The value that maps to the leftmost colormap color. Lower values will
        map to the same color.
        The default is None. The min_rate is then computed as the minimum
        attained value.
    max_rate : float (or other numerical type), optional
        The value that maps to the rightmost colormap color. Higher values
        will map to the same color.
        The default is None. The max_rate is then computed as the maximum
        attained value.
    verbose : boolean, optional
        The default is True. Whether to print out the date of the current
        svg file being created.

    Returns
    -------
    None.
        Creates svg files that plot the data for each specified date from the
        specified field on a map of NYC using the specified color palette.

    '''
    # Assumes clean_data has removed NaN from ZCTA and cast values to ints
    
    # Get max and min values of the field being plotted, if not specified
    if dates is None:
        if max_rate is None:
            max_rate = data[plot_field].max()
        if min_rate is None:
            min_rate = data[plot_field].min()
        dates = data.index.levels[1]
    else:
        relevant_data = data[data.index.get_level_values(1).isin(dates)][plot_field]
        if max_rate is None:
            max_rate = relevant_data.max()
        if min_rate is None:
            min_rate = data[plot_field].min()
    
    # Make an svg for each date      
    for date in dates:
        if verbose:
            print(date)
        mi_generate_svg_from_day_dataframe(data.loc[pd.IndexSlice[:, date], :], plot_field=plot_field, legend_title=legend_title, filename_prefix=filename_prefix, min_rate=min_rate, max_rate=max_rate, colormap=colormap)
    return
