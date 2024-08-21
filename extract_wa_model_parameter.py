# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "numpy",
#     "pandas",
# ]
# ///
# Read all .xml files from a given directory
import os
import traceback

import numpy as np
import pandas as pd


def merge_models(dir_input):
	dir = os.path.dirname(__file__)
	dirname = os.path.join(dir, dir_input)
	metadata = []
	dfs = []
	header = ''
	max_var = 0
	results = {}
	print(f'{len(os.listdir(dirname))} files found, start reading')
	for filename in os.listdir(dirname):
		if not filename.endswith('.xml'):
			continue
		# read first file header
		if not header:
			with open(os.path.join(dirname, filename)) as infile:
				header = '\n'.join(infile.readlines()[:4])
		# read analytes
		try:
			model_xml = pd.read_xml(os.path.join(dirname, filename), xpath='//ModelData/model/analyte')
		except Exception as e:
			traceback.print_exc()
			raise e

		# read model variance
		try:
			x = pd.read_xml(os.path.join(dirname, filename), xpath='//ModelData/model')
		except Exception as e:
			traceback.print_exc()
			raise e
		model_xml['filename'] = filename
		results[filename] = {}
		grouped = model_xml.groupby('filename')
		results[filename]['signal'] = grouped['signal'].sum()[0]
		results[filename]['filename'] = filename
		results[filename]['variance'] = x.variance.mean()
		results[filename]['max_variance'] = x.variance.max()
		results[filename]['min_variance'] = x.variance.min()
		for i in ['mw', 's', 'D', 'f', 'f_f0', 'vbar20']:
			if i == 'vbar20':
				multiplier = 10
			elif i == 'D':
				multiplier = 1e6
			elif i == 's':
				multiplier = 1e13
			elif i == 'mw':
				multiplier = 1
			elif i == 'f':
				multiplier = 1e8
			else:
				multiplier = 1
			model_xml[i] = model_xml[i] * multiplier
			value = model_xml.groupby('filename').apply(lambda y: np.average(y[i], weights=y['signal']))
			results[filename][f'wa_{i}'] = value[0]
			# compute the normal average
			average = model_xml.groupby('filename')[i].mean()
			results[filename][f'avg_{i}'] = average[0]
			# compute the standard deviation
			results[filename][f'{i}_std'] = model_xml.groupby('filename')[i].std()[0]
	# save results to a file
	results_df = pd.DataFrame(results).T
	results_df.to_csv(os.path.join(dirname, 'results.csv'))

	# calculate the weight average and standard deviation of every column except 'analyte name'


merge_models(r"7169_L5%IT%")
merge_models(r"7169_L5%MC%")
merge_models(r"7168_L5%IT%")
merge_models(r"7168_L5%MC%")
merge_models(r"7155_L5%IT%")
merge_models(r"7155_L5%MC%")