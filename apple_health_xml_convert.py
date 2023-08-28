#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Apple Health XML to CSV
==============================
:File: convert.py
:Description: Convert Apple Health "export.xml" file into a csv
:Version: 0.0.1
:Created: 2019-10-04
:Authors: Jason Meno (jam)
:Dependencies: An export.xml file from Apple Health
:License: BSD-2-Clause
"""

# %% Imports
import pandas as pd
import xml.etree.ElementTree as ET
import datetime as dt
import re
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages



# %% Function Definitions
def pre_process(xml_string):
	"""
	The export.xml file is where all your data is, but Apple Health Export has
	two main problems that make it difficult to parse:
		1. The DTD markup syntax is exported incorrectly by Apple Health for some data types.
		2. The invisible character \x0b (sometimes rendered as U+000b) likes to destroy trees. Think of the trees!

	Knowing this, we can save the trees and pre-processes the XML data to avoid destruction and ParseErrors.
	"""

	print("Pre-processing...", end="")
	sys.stdout.flush()

	xml_string = strip_dtd(xml_string)
	xml_string = strip_invisible_character(xml_string)
	print("done!")

	return xml_string


def strip_invisible_character(xml_string):

	return xml_string.replace("\x0b", "")


def strip_dtd(xml_string):
	start_strip = re.search('<!DOCTYPE', xml_string).span()[0]
	end_strip = re.search(']>', xml_string).span()[1]

	return xml_string[:start_strip] + xml_string[end_strip:]


def xml_to_csv(xml_string):
	"""Loops through the element tree, retrieving all objects, and then
	combining them together into a dataframe
	"""

	print("Converting XML File to CSV...", end="")
	sys.stdout.flush()

	etree = ET.ElementTree(ET.fromstring(xml_string))

	attribute_list = []

	for child in etree.getroot():
		child_attrib = child.attrib
		for metadata_entry in list(child):
			metadata_values = list(metadata_entry.attrib.values())
			if len(metadata_values) == 2:
				metadata_dict = {metadata_values[0]: metadata_values[1]}
				child_attrib.update(metadata_dict)

		attribute_list.append(child_attrib)

	health_df = pd.DataFrame(attribute_list)

	# Every health data type and some columns have a long identifier
	# Removing these for readability
	health_df.type = health_df.type.str.replace('HKQuantityTypeIdentifier', "")
	health_df.type = health_df.type.str.replace('HKCategoryTypeIdentifier', "")
	health_df.columns = \
		health_df.columns.str.replace("HKCharacteristicTypeIdentifier", "")

	# Reorder some of the columns for easier visual data review
	original_cols = list(health_df)
	shifted_cols = ['type',
					'sourceName',
					'value',
					'unit',
					'startDate',
					'endDate',
					'creationDate']

	# Add loop specific column ordering if metadata entries exist
	if 'com.loopkit.InsulinKit.MetadataKeyProgrammedTempBasalRate' in original_cols:
		shifted_cols.append(
			'com.loopkit.InsulinKit.MetadataKeyProgrammedTempBasalRate')

	if 'com.loopkit.InsulinKit.MetadataKeyScheduledBasalRate' in original_cols:
		shifted_cols.append(
			'com.loopkit.InsulinKit.MetadataKeyScheduledBasalRate')

	if 'com.loudnate.CarbKit.HKMetadataKey.AbsorptionTimeMinutes' in original_cols:
		shifted_cols.append(
			'com.loudnate.CarbKit.HKMetadataKey.AbsorptionTimeMinutes')

	remaining_cols = list(set(original_cols) - set(shifted_cols))
	reordered_cols = shifted_cols + remaining_cols
	health_df = health_df.reindex(labels=reordered_cols, axis='columns')

	# Sort by newest data first
	health_df.sort_values(by='startDate', ascending=False, inplace=True)

	print("done!")

	return health_df


def save_to_csv(csvpath,health_df):
	print("Saving CSV file...", end="")
	sys.stdout.flush()

	today = dt.datetime.now().strftime('%Y-%m-%d')
	csvpath = csvpath + "/apple_health_export_" + today + ".csv"

	health_df.to_csv(csvpath,index=False)
	print("done!")

	return (csvpath)

def setup_argparse():
	parser = argparse.ArgumentParser(
		description='Convert Apple Health "export.xml" file into a csv for reports.',
		  epilog="... and that's how you parse an Apple.")

	parser.add_argument('file', metavar='path/to/export.xml', type=str,
		     			default="./Export.xml",
		     			help='Apple Health export.xml file')
	parser.add_argument('-o', '--output', metavar='path/to/reportdirectory', type=str,
		     			default='.',
						help='Output directory for reports')
	parser.add_argument('-q', '--quiet', action='store_true',
						help='Disable verbose mode')
	parser.add_argument('-d', '--debug', action='store_true',
						help='Enable debug mode')
	parser.add_argument('-s', '--skip', action='store_true',
						help='Skip reading fresh data and use CSV instead')

	parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.0.1')

	args = parser.parse_args()
	return args


# Function to plot the data and trend
def plot_data_with_trend(data, hdata, title=''):
    fig, ax1 = plt.subplots(figsize=(15, 7))
    ax1.scatter(data['startDate'], data['value_systolic'], label='Systolic', color='b', marker='o')
    ax1.scatter(data['startDate'], data['value_diastolic'], label='Diastolic', color='r', marker='o')
    z_systolic = np.polyfit(data.index, data['value_systolic'], 1)
    p_systolic = np.poly1d(z_systolic)
    ax1.plot(data['startDate'], p_systolic(data.index), linestyle='-', color='b', alpha=0.5)
    z_diastolic = np.polyfit(data.index, data['value_diastolic'], 1)


    p_diastolic = np.poly1d(z_diastolic)
    ax1.plot(data['startDate'], p_diastolic(data.index), linestyle='-', color='r', alpha=0.5)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Blood Pressure (mmHg)')
    ax1.set_title(title)
    ax1.legend(loc='upper left')

    heart_rate_filtered = hdata[(hdata['startDate'] >= data['startDate'].min()) &
                                          (hdata['startDate'] <= data['startDate'].max())]
    ax2 = ax1.twinx()
    ax2.scatter(heart_rate_filtered['startDate'], heart_rate_filtered['value'], label='Heart Rate', color='g', marker='x')
    ax2.set_ylabel('Heart Rate (count/min)')
    ax2.legend(loc='upper right')
    plt.tight_layout()
    plt.show()


# Function to filter out weeks with no recorded values
def filter_weeks_with_data(data):
    data['week'] = data['startDate'].dt.isocalendar().week
    data['year'] = data['startDate'].dt.year
    valid_weeks = data.groupby(['year', 'week']).filter(lambda x: len(x) > 0)
    return valid_weeks

# Function to plot data with German labels and adjusted x-axis limits
def plot_data_with_german_labels_adjusted(data, hdata, title):
    fig, ax1 = plt.subplots(figsize=(15, 7))
    ax1.scatter(data['startDate'], data['value_systolic'], label='Systolisch', color='b', marker='o')
    ax1.scatter(data['startDate'], data['value_diastolic'], label='Diastolisch', color='r', marker='o')
    z_systolic = np.polyfit(data.index, data['value_systolic'], 1)
    p_systolic = np.poly1d(z_systolic)
    ax1.plot(data['startDate'], p_systolic(data.index), linestyle='-', color='b', alpha=0.5)
    z_diastolic = np.polyfit(data.index, data['value_diastolic'], 1)
    p_diastolic = np.poly1d(z_diastolic)
    ax1.plot(data['startDate'], p_diastolic(data.index), linestyle='-', color='r', alpha=0.5)
    ax1.set_xlabel('Datum')
    ax1.set_ylabel('Blutdruck (mmHg)')
    ax1.set_title(title)
    ax1.legend(loc='upper left')
    ax1.set_xlim([data['startDate'].min(), data['startDate'].max()])
    heart_rate_filtered = hdata[(hdata['startDate'] >= data['startDate'].min()) &
                                          (hdata['startDate'] <= data['startDate'].max())]
    ax2 = ax1.twinx()
    ax2.scatter(heart_rate_filtered['startDate'], heart_rate_filtered['value'], label='Herzfrequenz', color='g', marker='x')
    ax2.set_ylabel('Herzfrequenz (Schläge/Min)')
    ax2.legend(loc='upper right')
    plt.tight_layout()
    plt.show()

# Function to save plot to PDF with consistent y-axis
def save_plot_to_pdf(data, hdata, title, y_min, y_max, ax):
    ax.scatter(data['startDate'], data['value_systolic'], label='Systolisch', color='b', marker='o')
    ax.scatter(data['startDate'], data['value_diastolic'], label='Diastolisch', color='r', marker='o')

    # Trendline for Systolic
    z_systolic = np.polyfit(data.index, data['value_systolic'], 1)
    p_systolic = np.poly1d(z_systolic)
    ax.plot(data['startDate'], p_systolic(data.index), linestyle='-', color='b', alpha=0.5)

    # Trendline for Diastolic
    z_diastolic = np.polyfit(data.index, data['value_diastolic'], 1)
    p_diastolic = np.poly1d(z_diastolic)
    ax.plot(data['startDate'], p_diastolic(data.index), linestyle='-', color='r', alpha=0.5)

    # Labels, title, and consistent y-axis limits
    ax.set_xlabel('Datum')
    ax.set_ylabel('Blutdruck (mmHg)')
    ax.set_title(title)
    ax.legend(loc='upper left')
    ax.set_xlim([data['startDate'].min(), data['startDate'].max()])
    ax.set_ylim([y_min, y_max])

    # Heart Rate on a secondary y-axis
    heart_rate_filtered = hdata[(hdata['startDate'] >= data['startDate'].min()) &
                                          (hdata['startDate'] <= data['startDate'].max())]
    ax2 = ax.twinx()
    ax2.scatter(heart_rate_filtered['startDate'], heart_rate_filtered['value'], label='Herzfrequenz', color='g', marker='x')
    ax2.set_ylabel('Herzfrequenz (Schläge/Min)')
    ax2.legend(loc='upper right')



# %% Main Function
def main():
	args = setup_argparse()

	if args.debug:
		print("Debug mode enabled")
		print(args)
	if args.quiet:
		print("Verbose mode disabled")
	if args.output:
		print("Output directory: " + args.output)
	if args.file:
		print("Input file: " + args.file)
	if args.skip:
		print("Skipping reading fresh data and using CSV instead")
		csvpath = args.output + "/apple_health_export" + ".csv"

	else:
		print("No input file specified")
		sys.exit(1)

	if not args.skip:
		# read the file
		xml_string = open(args.file).read()

		xml_string = pre_process(xml_string)
		health_df = xml_to_csv(xml_string)
		csvpath = save_to_csv(args.output,health_df)

	data = pd.read_csv(csvpath, parse_dates=['startDate', 'endDate', 'creationDate'])
	#data = pd.read_csv(csvpath, parse_dates=['startDate', 'endDate', 'creationDate'], dtype={'value': float})

	# Data filtering for systolic and diastolic blood pressure
	heart_rate_data = data[data['type'] == "HeartRate"]
	# heart_rate_data['value'] = pd.to_numeric(heart_rate_data['value'], errors='coerce')
	heart_rate_data.loc[:, 'value'] = pd.to_numeric(heart_rate_data['value'], errors='coerce')

	data_systolic = data[data['type'] == "BloodPressureSystolic"].rename(columns={"value": "value_systolic", "type": "type_systolic", "sourceName": "sourceName_systolic", "endDate": "endDate_systolic", "creationDate": "creationDate_systolic"})
	data_systolic.loc[:, 'value_systolic'] = pd.to_numeric(data_systolic['value_systolic'], errors='coerce')

	data_diastolic = data[data['type'] == "BloodPressureDiastolic"].rename(columns={"value": "value_diastolic", "type": "type_diastolic", "sourceName": "sourceName_diastolic", "endDate": "endDate_diastolic", "creationDate": "creationDate_diastolic"})
	data_diastolic.loc[:, 'value_diastolic'] = pd.to_numeric(data_diastolic['value_diastolic'], errors='coerce')

	merged_data = pd.merge_asof(data_systolic.sort_values('startDate'), data_diastolic.sort_values('startDate'), on="startDate", direction="nearest")

	# Data splitting by year
	data_2015_2016 = merged_data[(merged_data['startDate'].dt.year == 2015) | (merged_data['startDate'].dt.year == 2016)]
	data_2019 = merged_data[merged_data['startDate'].dt.year == 2019]
	data_2023 = merged_data[merged_data['startDate'].dt.year == 2023]


	# Average blood pressure calculation
	average_systolic = merged_data['value_systolic'].mean()
	average_diastolic = merged_data['value_diastolic'].mean()
	average_systolic_2015_2016 = data_2015_2016['value_systolic'].mean()
	average_diastolic_2015_2016 = data_2015_2016['value_diastolic'].mean()
	average_systolic_2019 = data_2019['value_systolic'].mean()
	average_diastolic_2019 = data_2019['value_diastolic'].mean()
	average_systolic_2023 = data_2023['value_systolic'].mean()
	average_diastolic_2023 = data_2023['value_diastolic'].mean()

	y_min_limit = merged_data['value_diastolic'].min()
	y_max_limit = merged_data['value_systolic'].max()

	# Extracting week and year from the startDate for boxplot
	merged_data['week'] = merged_data['startDate'].dt.isocalendar().week
	merged_data['year'] = merged_data['startDate'].dt.year

	# Relevant data filtering for 2015 + 2016, 2019, and 2023
	relevant_data = merged_data[merged_data['year'].isin([2015, 2016, 2019, 2023])]

	# Plotting the boxplots
	fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

	# Boxplot for Systolic Blood Pressure
	relevant_data.boxplot(column='value_systolic', by=['year', 'week'], ax=ax1, grid=False)
	ax1.set_title('Boxplot für Systolischen Blutdruck')
	ax1.set_ylabel('Systolischer Blutdruck (mmHg)')
	ax1.set_xlabel('')

	# Boxplot for Diastolic Blood Pressure
	relevant_data.boxplot(column='value_diastolic', by=['year', 'week'], ax=ax2, grid=False)
	ax2.set_title('Boxplot für Diastolischen Blutdruck')
	ax2.set_ylabel('Diastolischer Blutdruck (mmHg)')
	ax2.set_xlabel('Jahr, Woche')

	# Adjusting layout
	fig.suptitle('')
	plt.tight_layout()
	plt.xticks(rotation=90)
	plt.show()


	# Create a PDF to save the plots
	with PdfPages(args.output + '/blood_pressure_boxplots.pdf') as pdf:
		fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

		# Boxplot for Systolic Blood Pressure
		relevant_data.boxplot(column='value_systolic', by=['year', 'week'], ax=ax1, grid=False)
		ax1.set_title('Boxplot für Systolischen Blutdruck')
		ax1.set_ylabel('Systolischer Blutdruck (mmHg)')
		ax1.set_xlabel('')

		# Boxplot for Diastolic Blood Pressure
		relevant_data.boxplot(column='value_diastolic', by=['year', 'week'], ax=ax2, grid=False)
		ax2.set_title('Boxplot für Diastolischen Blutdruck')
		ax2.set_ylabel('Diastolischer Blutdruck (mmHg)')
		ax2.set_xlabel('Jahr, Woche')

		# Adjusting layout
		fig.suptitle('')
		plt.tight_layout()
		plt.xticks(rotation=90)

		# Save the plot to the PDF
		pdf.savefig(fig)
		plt.close()


	# Create a PDF file to save the plots
	with PdfPages(args.output + '/blood_pressure_charts_and_boxplots.pdf') as pdf:
		# Scatterplots for 2015 + 2016, 2019, and 2023
		fig, ax1 = plt.subplots(figsize=(15, 7))
		save_plot_to_pdf(data_2015_2016, heart_rate_data, 'Blutdruck und Herzfrequenz für 2015 + 2016', y_min_limit, y_max_limit, ax1)
		pdf.savefig(fig)
		plt.close()

		fig, ax1 = plt.subplots(figsize=(15, 7))
		save_plot_to_pdf(data_2019, heart_rate_data, 'Blutdruck und Herzfrequenz für 2019', y_min_limit, y_max_limit, ax1)
		pdf.savefig(fig)
		plt.close()

		fig, ax1 = plt.subplots(figsize=(15, 7))
		save_plot_to_pdf(data_2023, heart_rate_data, 'Blutdruck und Herzfrequenz für 2023', y_min_limit, y_max_limit, ax1)
		pdf.savefig(fig)
		plt.close()

		# Boxplots
		fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
		relevant_data.boxplot(column='value_systolic', by=['year', 'week'], ax=ax1, grid=False)
		ax1.set_title('Boxplot für Systolischen Blutdruck')
		ax1.set_ylabel('Systolischer Blutdruck (mmHg)')
		ax1.set_xlabel('')
		relevant_data.boxplot(column='value_diastolic', by=['year', 'week'], ax=ax2, grid=False)
		ax2.set_title('Boxplot für Diastolischen Blutdruck')
		ax2.set_ylabel('Diastolischer Blutdruck (mmHg)')
		ax2.set_xlabel('Jahr, Woche')
		fig.suptitle('')
		plt.tight_layout()
		plt.xticks(rotation=90)
		pdf.savefig(fig)
		plt.close()


	return


# %%
if __name__ == '__main__':
	main()
