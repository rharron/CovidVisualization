#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import pandas
import matplotlib.pyplot as plt
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

def initalize_template_file():
    #Only need to run this once
    with open("template.svg", 'w') as outfile:
        map_file = open('NYCmap06-12.svg', 'r')
        for LINE in map_file:
            break
        map_file.close()
        tokens = LINE.split("<path aria-label=")
        outfile.write(tokens[0] + "\n")
        delim = 'role='
        for token in tokens[1:-1]:
            outfile.write(delim + token.split(delim)[1] + "\n")
        delimend = "stroke-width=\"0.5\"></path>"
        token, endgame = tokens[-1].split(delimend)
        outfile.write(delim + token.split(delim)[1] + delimend + "\n")
        outfile.write(endgame)
    return

def generate_svg_from_data_by_modzcta(filename):
    #Sample usage
    #generate_svg_from_data_by_modzcta("historical_data/data-by-modzcta.csv.001.b92f6e5.csv")
    with open(filename + ".svg", 'w') as outfile:
        rgb_re = re.compile('rgb\([0-9]*, [0-9]*, [0-9]*\)')
        infile = open(filename, 'r')
        zcta_data = pandas.read_csv(infile)
        infile.close()
        template_file = open('template.svg', 'r')
        template_out = template_file.readline()
        outfile.write(template_out)
        zips = zcta_data['MODIFIED_ZCTA']
        zcta_data = zcta_data.set_index('MODIFIED_ZCTA')
        for zcta in zips:
            #this_row = zcta_data[zcta_data['MODIFIED_ZCTA']==zcta]
            field = ZCTA_fields[0]
            out = "<path aria-label=\"" + field + ": %s"%(zcta_data.loc[zcta][fields_to_data_by_modzcta_dict[field]]) + ";\n"
            outfile.write(out)
            out = "\tZIP Code: %s;\n"%(double_zips[zcta] if zcta in double_zips else zcta)
            outfile.write(out)
            for i in range(2, len(ZCTA_fields)):
                field = ZCTA_fields[i]
                out = "\t" + field + ": %s"%(zcta_data.loc[zcta][fields_to_data_by_modzcta_dict[field]]) + ";\n"
                if i == len(ZCTA_fields) - 1:
                    out = out[:-2] + "\"\n"
                outfile.write(out)
                #print(out)
            rate = zcta_data.loc[zcta]['COVID_CASE_RATE']
            rate01 = rate / max_rate
            this_rgb = rgb1to256(plt.cm.rainbow(rate01))
            #print(this_rgb)
            template_out = template_file.readline()
            template_out = rgb_re.sub("rgb%s"%(this_rgb,), template_out)
            #print(template_out)
            outfile.write(template_out)
        template_out = template_file.readline()
        outfile.write(template_out)
        template_file.close()
    return

def generate_svg_from_day_dataframe(zcta_data, plot_field='COVID_CASE_RATE', filename_prefix='NYC', max_rate = 4429.24):
    # Set output filename based on 'DATA_DATE" value (there should only be one)
    rgb_re = re.compile('rgb\([0-9]*, [0-9]*, [0-9]*\)')
    filename =  filename_prefix + "_" + plot_field + "_" + zcta_data['DATA_DATE'].iloc[0].strftime("%Y-%m-%d-%H-%M-%S") + ".svg"
    with open(filename, 'w') as outfile:
        template_file = open('template.svg', 'r')
        template_out = template_file.readline()
        outfile.write(template_out)
        zips = zcta_data['MODIFIED_ZCTA']
        zcta_data = zcta_data.set_index('MODIFIED_ZCTA')
        for zcta in zips:
            #this_row = zcta_data[zcta_data['MODIFIED_ZCTA']==zcta]
            field = ZCTA_fields[0]
            out = "<path aria-label=\"" + field + ": %s"%(zcta_data.loc[zcta][fields_to_data_by_modzcta_dict[field]]) + ";\n"
            outfile.write(out)
            out = "\tZIP Code: %s;\n"%(double_zips[zcta] if zcta in double_zips else zcta)
            outfile.write(out)
            for i in range(2, len(ZCTA_fields)):
                field = ZCTA_fields[i]
                out = "\t" + field + ": %s"%(zcta_data.loc[zcta][fields_to_data_by_modzcta_dict[field]]) + ";\n"
                if i == len(ZCTA_fields) - 1:
                    out = out[:-2] + "\"\n"
                outfile.write(out)
                #print(out)
            rate = zcta_data.loc[zcta][plot_field]
            rate01 = rate / max_rate
            this_rgb = rgb1to256(plt.cm.rainbow(rate01))
            #print(this_rgb)
            template_out = template_file.readline()
            template_out = rgb_re.sub("rgb%s"%(this_rgb,), template_out)
            #print(template_out)
            outfile.write(template_out)
        template_out = template_file.readline()
        outfile.write(template_out)
        template_file.close()
    return
    
def generate_multiple_svgs_from_one_dataframe(data, plot_field='COVID_CASE_RATE', filename_prefix='NYC', verbose=True):
    data.dropna(subset=['MODIFIED_ZCTA'], inplace=True)
    data = data.astype({'MODIFIED_ZCTA' : int})
    max_rate = data[plot_field].max()
    for date in data.DATA_DATE.drop_duplicates():
        if verbose:
            print(date)
        generate_svg_from_day_dataframe(data[data['DATA_DATE']==date], plot_field=plot_field, filename_prefix=filename_prefix)
    return


        
        
        
        
        
        