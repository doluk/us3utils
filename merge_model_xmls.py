import pandas as pd
import sys
import os


colnames = ['analyte name', 'mw','s','D','f','f_f0','vbar20','extinction','axial','sigma','delta',
            'oligomer','shape','type','molar','signal']
aggregations = {col: 'mean' for col in ('mw','D','f','extinction','axial','sigma','delta','oligomer','shape','type','molar')}
aggregations['signal'] = 'sum'
dfs = []

if len(sys.argv) != 2:
    dir_input = input('Enter path to directory which should be condensed:')
else:
    dir_input = sys.argv[1]
dir = os.path.dirname(__file__)
dirname = os.path.join(dir,dir_input)

header=''
max_var = 0
for filename in os.listdir(dirname):
    if not filename.endswith('.xml'):
        continue
    # read first file header
    if not header:
        with open(os.path.join(dirname,filename)) as infile:
            header = '\n'.join(infile.readlines()[:4])
    # read analytes
    try:
        dfs.append(pd.read_xml(filename, xpath='//ModelData/model/analyte'))
    except:
        print(filename)
    # read model variance
    try:
        metadata = pd.read_xml(filename, xpath='//ModelData/model')
    except:
        pass
    #max_var = max(max_var, metadata.variance.max())
exit(1)
# concatenate
df = pd.concat(dfs, axis=0)

# aggregate by s, f_f0, vbar20
df_out = df.groupby(by=['s','f_f0','vbar20'],sort=False).agg(aggregations).reset_index(drop=False)
fake_analyte_names = ['SC{:04d}'.format(i) for i in range(1, df_out.shape[0] + 1)]
df_out['analyte name'] = fake_analyte_names

header = header.split('variance="')
header = header[0] + f'variance="{max_var}' + header[1][header[1].index('"'):]

xml = df_out[colnames].rename({'analyte name': 'name'}, axis=1) \
    .to_xml(index=False, row_name='analyte', root_name='model', attr_cols=['name'] + colnames[1:])
xml = header + xml[46:] + '\n</ModelData>'

with open(os.path.join(dirname, 'm1337.xml'), 'w+') as outfile:
    outfile.write(xml)