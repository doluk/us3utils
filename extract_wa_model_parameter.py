# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "numpy",
#     "pandas",
#     "lxml",
# ]
# ///
# Read all .xml files from a given directory
import os
import traceback

import numpy as np
import pandas as pd
multiplier = 1
aggregations = {col: 'mean' for col in
                ('mw', 'D', 'f', 'extinction', 'axial', 'sigma', 'delta', 'oligomer', 'shape', 'type', 'molar')}
aggregations['signal'] = 'sum'

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
        grouped = model_xml.groupby(by=['s', 'f_f0', 'vbar20'], sort=False).aggregate(aggregations).reset_index(drop=False)
        grouped = grouped[['signal', 'mw', 's', 'D', 'f', 'f_f0', 'vbar20']]
        grouped['signal'] /= x.shape[0]
        species_count = grouped['signal'].count()
        results[filename]['signal'] = grouped['signal'].sum()
        results[filename]['filename'] = filename
        results[filename]['variance'] = x.variance.mean()
        results[filename]['model_rmsd'] = np.sqrt(x.variance.mean())
        results[filename]['max_variance'] = x.variance.max()
        results[filename]['min_variance'] = x.variance.min()
        filter_model_xml = grouped.copy()
        for i in ['mw', 's', 'D', 'f', 'f_f0', 'vbar20']:
            # if i == 'vbar20':
            #     multiplier = 10
            # elif i == 'D':
            #     multiplier = 1e6
            # elif i == 's':
            #     multiplier = 1e13
            # elif i == 'mw':
            #     multiplier = 1
            # elif i == 'f':
            #     multiplier = 1e8
            # else:
            #     multiplier = 1
            model_xml.loc[:, i] *= multiplier

            
            value: float = np.average(grouped[i], weights=grouped['signal'])
            results[filename][f'wa_{i}'] = value
            sum_squared_signal = np.square(grouped['signal']).sum()
            squared_sum_signal = grouped['signal'].sum() ** 2
            divider = sum_squared_signal / (squared_sum_signal - sum_squared_signal)
            signal_sum = 0.0
            value_sum = 0.0
            for j in range(grouped.shape[0]):
                value_sum += grouped['signal'].loc[j] * (grouped[i].loc[j] - value) * (grouped[i].loc[j] - value)
            std_wa_avg = (value_sum * divider) ** 0.5
            results[filename][f'wa_{i}_std'] = std_wa_avg
            # compute the normal average
            average = grouped[i].mean()
            results[filename][f'avg_{i}'] = average
            # compute the standard deviation
            results[filename][f'{i}_std'] = grouped[i].std()
    
        # Filter data based on conditions
        filtered_data = filter_model_xml[(filter_model_xml['s'] >= 1.5e-13) & (filter_model_xml['s'] <= 3e-13) & (filter_model_xml['f_f0'] <= 2)]
        # Repeat calculations with filtered data
        if not filtered_data.empty:
            grouped_filtered = filtered_data
            species_count = grouped_filtered['signal'].count()
            results[filename]['filtered_signal'] = grouped_filtered['signal'].sum()
            
            for i in ['mw', 's', 'D', 'f', 'f_f0', 'vbar20']:
                # if i == 'vbar20':
                #     multiplier = 10
                # elif i == 'D':
                #     multiplier = 1e6
                # elif i == 's':
                #     multiplier = 1e13
                # elif i == 'mw':
                #     multiplier = 1
                # elif i == 'f':
                #     multiplier = 1e8
                # else:
                #     multiplier = 1
                filtered_data.loc[:, i] *= multiplier
                value = np.average(filtered_data[i], weights=filtered_data['signal'])
                sum_squared_signal = np.square(filtered_data['signal']).sum()
                squared_sum_signal = filtered_data['signal'].sum()**2
                divider = sum_squared_signal / (squared_sum_signal - sum_squared_signal)
                results[filename][f'filtered_wa_{i}'] = value
                # calculate the standard deviation of the weighted average
                std_wa_avg = np.sqrt(np.sum(filtered_data['signal']*(filtered_data[i]-value)**2)*divider)
                results[filename][f'filtered_wa_{i}_std'] = std_wa_avg
                average = filtered_data[i].mean()
                results[filename][f'filtered_avg_{i}'] = average
                results[filename][f'filtered_{i}_std'] = filtered_data[i].std()
    
    # save results to a file
    results_df = pd.DataFrame(results).T
    results_df.to_csv(os.path.join(dirname, f'{dirname} - results.csv'))

    # calculate the weight average and standard deviation of every column except 'analyte name'

merge_models(r"%BFE-Run2424-Myo-SV-FVM-v2%2DSA-MC%")
#merge_models(r"%BFE-Run2424-Myo-SV-FEM%2DSA-MC%")
#merge_models(r"%BFE-Run2424-Myo-SV-FVM%2DSA-MC%")
