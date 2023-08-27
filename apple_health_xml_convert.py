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

	# Every health data type and some columns have a long identifer
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
	health_df.to_csv(csvpath + "/apple_health_export_" + today + ".csv", index=False)
	print("done!")

	return

def setup_argparse():
	parser = argparse.ArgumentParser(
		description='Convert Apple Health "export.xml" file into a csv for reports.',
		  epilog="... and that's how you parse an Apple.")

	parser.add_argument('file', metavar='path/to/export.xml', type=str, default="./Export.xml",
		     			help='Apple Health export.xml file')
	parser.add_argument('-o', '--output', metavar='path/to/reportdirectory', type=str, default='.',
						help='Output directory for reports')
	parser.add_argument('-q', '--quiet', action='store_true',
						help='Disable verbose mode')
	parser.add_argument('-d', '--debug', action='store_true',
						help='Enable debug mode')
	parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.0.1')

	args = parser.parse_args()
	return args


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
	else:
		print("No input file specified")
		sys.exit(1)

	# read the file
	xml_string = open(args.file).read()

	xml_string = pre_process(xml_string)
	health_df = xml_to_csv(xml_string)
	save_to_csv(args.output,health_df)

	return


# %%
if __name__ == '__main__':
	main()
