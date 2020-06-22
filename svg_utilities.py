#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import locale
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

ZCTA_fields = ['Case Rate per 100k',
    'ZIP Code',
    'Neighborhood',
    'Case Count',
    'Rate per 100,000',
    'Percent of people tested who tested positive',
    'Deaths',
    'Death rate per 100,000']

fields_to_data_by_modzcta_dict = {
    'Case Rate per 100k' : 'COVID_CASE_RATE',
    'Neighborhood' : 'NEIGHBORHOOD_NAME',
    'Case Count' : 'COVID_CASE_COUNT',
    'Rate per 100,000' : 'COVID_CASE_RATE',
    'Percent of people tested who tested positive' : 'PERCENT_POSITIVE',
    'Deaths' : 'COVID_DEATH_COUNT',
    'Death rate per 100,000' : 'COVID_DEATH_RATE'
    }

double_zips = {
    10001 : '10001, 10118',
    10019 : '10019, 10020',
    10075 : '10075, 10162',
    11004 : '11004, 11005',
    11211 : '11211, 11249',
    11217 : '11217, 11243'
    }

#Temporarily hardcode these
#max_rate = 4429.24
min_rate = 551.01

def rgb1to256(rgb1):
    return tuple(np.ceil(256 * c).astype('int') - 1 for c in rgb1[:3])

def initalize_template_file(colormap='rainbow'):
    # Only need to run this once per colormap
    
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
        #outfile.write(header_tokens[0] + "\n")
        outfile.write(header_tokens[0])
        step = 1/21
        for i in range(22):
            val = step * i
            this_rgb = rgb1to256(cm(val))
            header_tokens[i+1] = header_delim + rgb_re.sub("rgb%s"%(this_rgb,), offset_re.sub("\"%s\""%(val), header_tokens[i+1], 1), 1)
            #outfile.write(header_tokens[i+1] + "\n")
            if i == 21:
                header_tokens[i+1] += "\n"
            outfile.write(header_tokens[i+1])
        #outfile.write(tokens[0] + "\n")
        delim = 'role='
        for token in tokens[1:-1]:
            outfile.write(delim + token.split(delim)[1] + "\n")
        delimend = "stroke-width=\"0.5\"></path>"
        token, endgame = tokens[-1].split(delimend)
        outfile.write(delim + token.split(delim)[1] + delimend + "\n")
        outfile.write(endgame)
    return

def generate_svg_from_day_dataframe(zcta_data, plot_field='COVID_CASE_RATE', filename_prefix='NYC', min_rate=551, max_rate = 4429.24, colormap='rainbow'):
    # Preparations for later use
    rgb_re = re.compile('rgb\([0-9]*, [0-9]*, [0-9]*\)')
    delta_values = max_rate - min_rate
    locale.setlocale(locale.LC_ALL, '')
    
    # Get colormap from argument
    cm = eval("plt.cm." + colormap)
    
    # Set output filename based on colormap and 'DATA_DATE" value (there should only be one)
    date = zcta_data['DATA_DATE'].iloc[0]
    filename =  filename_prefix + "_" + plot_field + "_" + colormap + "_" + date.strftime("%Y-%m-%d-%H-%M-%S") + ".svg"
    
    with open(filename, 'w') as outfile:
        # Open the svg template file and write out the initial segment
        template_file = open('template_' + colormap + '.svg', 'r')
        template_out = template_file.readline()
        outfile.write(template_out)
        
        # For each ZCTA, write out an aria-label with relevant data
        # and then the corresponding template block with this date's rgb value
        zips = zcta_data['MODIFIED_ZCTA']
        zcta_data = zcta_data.set_index('MODIFIED_ZCTA')
        for zcta in zips:
            # First two data fields need custom handling
            field = ZCTA_fields[0]
            out = "<path aria-label=\"" + field + ": %s"%(zcta_data.loc[zcta][fields_to_data_by_modzcta_dict[field]]) + ";\n"
            outfile.write(out)
            out = "\tZIP Code: %s;\n"%(double_zips[zcta] if zcta in double_zips else zcta)
            outfile.write(out)
            
            # Process and write out the remaining data fields
            for i in range(2, len(ZCTA_fields)):
                field = ZCTA_fields[i]
                out = "\t" + field + ": %s"%(zcta_data.loc[zcta][fields_to_data_by_modzcta_dict[field]]) + ";\n"
                if i == len(ZCTA_fields) - 1:
                    out = out[:-2] + "\"\n"
                outfile.write(out)
                
            # Compute rgb value based on plotted field's value
            rate = zcta_data.loc[zcta][plot_field]
            rate01 = (rate - min_rate) / delta_values
            this_rgb = rgb1to256(cm(rate01))
            template_out = template_file.readline()
            # Update template's rgb value with computed one
            template_out = rgb_re.sub("rgb%s"%(this_rgb,), template_out)
            outfile.write(template_out)
        
        # Write out end segment of the file from the template, adding in date and max-min info
        template_out = template_file.readline()
        date_str = "Date: %s"%(date.strftime("%b %-d, %Y"))
        legend_title = "><tspan x=\"0\" dy=\"-1.2em\">"+ date_str + "</tspan><tspan x=\"0\" dy=\"1.4em\">Case Rate per 100k</tspan>"
        template_out = re.sub(">Case Rate per 100k", legend_title, template_out)
        legend_title = "\'" + date_str + "; Case Rate per 100k"
        template_out = re.sub("\'Case Rate per 100k", legend_title, template_out)
        minstr = locale.format_string("%.2f", min_rate, grouping=True)
        maxstr = locale.format_string("%.2f", max_rate, grouping=True)
        template_out = template_out.replace("551 to 4,429", minstr + " to " + maxstr)
        template_out = template_out.replace("551<", minstr + "<")
        template_out = template_out.replace("4,429<", maxstr + "<")
        outfile.write(template_out)
        template_file.close()
    return

def mi_generate_svg_from_day_dataframe(zcta_data, plot_field='COVID_CASE_RATE', filename_prefix='NYC', min_rate=551, max_rate = 4429.24, colormap='rainbow'):
    # Preparations for later use
    rgb_re = re.compile('rgb\([0-9]*, [0-9]*, [0-9]*\)')
    delta_values = max_rate - min_rate
    locale.setlocale(locale.LC_ALL, '')
    
    # Get colormap from argument
    cm = eval("plt.cm." + colormap)
    
    # Set output filename based on colormap and 'DATA_DATE" value (there should only be one)
    date = zcta_data.index[0][1]#zcta_data['DATA_DATE'].iloc[0]
    filename =  filename_prefix + "_" + plot_field + "_" + colormap + "_" + date.strftime("%Y-%m-%d-%H-%M-%S") + ".svg"
    
    with open(filename, 'w') as outfile:
        # Open the svg template file and write out the initial segment
        template_file = open('template_' + colormap + '.svg', 'r')
        template_out = template_file.readline()
        outfile.write(template_out)
        
        # For each ZCTA, write out an aria-label with relevant data
        # and then the corresponding template block with this date's rgb value
        zips = zcta_data.index.levels[0]
        #zcta_data = zcta_data.set_index('MODIFIED_ZCTA')
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
        date_str = "Date: %s"%(date.strftime("%b %-d, %Y"))
        legend_title = "><tspan x=\"0\" dy=\"-1.2em\">"+ date_str + "</tspan><tspan x=\"0\" dy=\"1.4em\">Case Rate per 100k</tspan>"
        template_out = re.sub(">Case Rate per 100k", legend_title, template_out)
        legend_title = "\'" + date_str + "; Case Rate per 100k"
        template_out = re.sub("\'Case Rate per 100k", legend_title, template_out)
        minstr = locale.format_string("%.2f", min_rate, grouping=True)
        maxstr = locale.format_string("%.2f", max_rate, grouping=True)
        template_out = template_out.replace("551 to 4,429", minstr + " to " + maxstr)
        template_out = template_out.replace("551<", minstr + "<")
        template_out = template_out.replace("4,429<", maxstr + "<")
        outfile.write(template_out)
        template_file.close()
    return
    
def generate_multiple_svgs_from_one_dataframe(data, plot_field='COVID_CASE_RATE', filename_prefix='NYC', colormap='rainbow', verbose=True):
    # Sample usage:
    # data = clean_data.read_all_zcta_data()
    # svg_utilities.generate_multiple_svgs_from_one_dataframe(data)
    
    # Earlier data contains an NA ZCTA, drop those and convert all ZCTA to ints
    data.dropna(subset=['MODIFIED_ZCTA'], inplace=True)
    data = data.astype({'MODIFIED_ZCTA' : int})
    
    # Get max value of the field being plotted
    max_rate = data[plot_field].max()
    min_rate = data[plot_field].min()
    
    # Make an svg for each date
    for date in data.DATA_DATE.drop_duplicates():
        if verbose:
            print(date)
        generate_svg_from_day_dataframe(data[data['DATA_DATE']==date], plot_field=plot_field, filename_prefix=filename_prefix, min_rate=min_rate, max_rate=max_rate, colormap=colormap)
    return

def mi_generate_multiple_svgs_from_one_dataframe(data, plot_field='COVID_CASE_RATE', filename_prefix='NYC', colormap='rainbow', dates=None, max_rate=None, verbose=True):
    # Multiindex version of previous function
    # Assumes clean_data has removed NaN from ZCTA and cast values to ints
    # Sample usage:
    # data = clean_data.read_all_zcta_data()
    # svg_utilities.generate_multiple_svgs_from_one_dataframe(data)
    
    # Earlier data contains an NA ZCTA, drop those and convert all ZCTA to ints
    #data.dropna(subset=['MODIFIED_ZCTA'], inplace=True)
    #data = data.astype({'MODIFIED_ZCTA' : int})
    
    # Get max value of the field being plotted
    if dates is None:
        if max_rate is None:
            max_rate = data[plot_field].max()
        min_rate = data[plot_field].min()
        dates = data.index.levels[1]
    else:
        relevant_data = data[data.index.get_level_values(1).isin(dates)][plot_field]
        #print(relevant_data)
        if max_rate is None:
            max_rate = relevant_data.max()
        min_rate = relevant_data.min()
    
    # Make an svg for each date      
    for date in dates:
        if verbose:
            print(date)
        mi_generate_svg_from_day_dataframe(data.loc[pd.IndexSlice[:, date], :], plot_field=plot_field, filename_prefix=filename_prefix, min_rate=min_rate, max_rate=max_rate, colormap=colormap)
    return


        
        
        
        
        
        