import math
import traceback

import pandas as pd
import sys
import os


def dump_xml(df_out, name):
    fake_analyte_names = ['SC{:04d}'.format(i) for i in range(1, df_out.shape[0] + 1)]
    df_out['analyte name'] = fake_analyte_names
    xml = df_out[colnames].rename({'analyte name': 'name'}, axis=1) \
        .to_xml(index=False, row_name='analyte', root_name='model', attr_cols=['name'] + colnames[1:])
    xml = header + xml[46:] + '\n</ModelData>'

    with open(os.path.join(dirname, f'{name}.xml'), 'w+') as outfile:
        outfile.write(xml)


colnames = ['analyte name', 'mw', 's', 'D', 'f', 'f_f0', 'vbar20', 'extinction', 'axial', 'sigma', 'delta',
            'oligomer', 'shape', 'type', 'molar', 'signal']
aggregations = {col: 'mean' for col in
                ('mw', 'D', 'f', 'extinction', 'axial', 'sigma', 'delta', 'oligomer', 'shape', 'type', 'molar')}
aggregations['signal'] = 'sum'
dfs = []

if len(sys.argv) != 2:
    dir_input = input('Enter path to directory which should be condensed:')
else:
    dir_input = sys.argv[1]
dir = os.path.dirname(__file__)
dirname = os.path.join(dir, dir_input)
metadata = []
header = ''
max_var = 0
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
        dfs.append(model_xml)
    except Exception as e:
        traceback.print_exc()
        raise e
    # read model variance
    try:
        x = pd.read_xml(os.path.join(dirname, filename), xpath='//ModelData/model')
        metadata.append(x)
    except Exception as e:
        traceback.print_exc()
        raise e
metadata = pd.concat(metadata, axis=0)
max_var = metadata.variance.max()
# concatenate
df = pd.concat(dfs, axis=0)
print('finished importing data. starting to find unique analytes')
# aggregate by s, f_f0, vbar20
df_out = df.groupby(by=['s', 'f_f0', 'vbar20'], sort=False).agg(aggregations).reset_index(drop=False)
df_out['signal'] = df_out['signal'] / metadata.shape[0]
fake_analyte_names = ['SC{:04d}'.format(i) for i in range(1, df_out.shape[0] + 1)]
df_out['analyte name'] = fake_analyte_names
header = header.split('variance="')
header = header[0] + f'variance="{max_var}' + header[1][header[1].index('"'):]
print('start dumping to xml')
xml = df_out[colnames].rename({'analyte name': 'name'}, axis=1) \
    .to_xml(index=False, row_name='analyte', root_name='model', attr_cols=['name'] + colnames[1:])
xml = header + xml[46:] + '\n</ModelData>'
with open(os.path.join(dirname, 'm1337.xml'), 'w+') as outfile:
    outfile.write(xml)
print('starting c(s,ff0) file generation')
df_out['s'] *= 1e13
lm_viscosity = 0.01002 * 0.1  # D2O Viskosity
lm_density = 0.99832 * 1000  # D2O Density
df_out['r_h'] = 1 / df_out.D / 1e-4 * 1.38065e-23 * 293.15 / 6 / lm_viscosity / math.pi
df.to_csv(str(os.path.join(dirname, dir_input + '-c(s_ff0).dat')), index=False, header=False,
          columns=['s', 'M', 'f_f0', 'D', 'r_h', 'signal'], sep='\t')
print('finished')
