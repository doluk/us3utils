# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "numpy",
#     "numba",
#     "scipy",
# ]
# ///
import math
import os
import traceback
from utils import converter as cv, us_maths
import pandas as pd
import re
import sys
attributes = ['Name', 'MW', 's', 'D', 'ff0', 'vbar', 'c_p']
axis = ['mw', 's', 'D', 'f', 'f_f0', 'vbar20', 's20w', 'D20w']
colnames = ['analyte name', 'mw', 's', 'D', 'f', 'f_f0', 'vbar20', 'extinction', 'axial', 'sigma', 'delta',
            'oligomer', 'shape', 'type', 'molar', 'signal']
aggregations = {col: 'mean' for col in
                ('mw', 'D', 'f', 'extinction', 'axial', 'sigma', 'delta', 'oligomer', 'shape', 'type', 'molar')}
aggregations['signal'] = 'sum'
dfs = []





def generate_mwl_mesh(dir_input, nsmooth, temp_exp, visc_exp, dens_exp):
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
        # read model variance
        try:
            x = pd.read_xml(os.path.join(dirname, filename), xpath='//ModelData/model')
            metadata.append(x)
        except Exception as e:
            traceback.print_exc()
            raise e
        # read analytes
        try:
            model_xml = pd.read_xml(os.path.join(dirname, filename), xpath='//ModelData/model/analyte')
            model_xml['wavelength'] = x['wavelength']
            dfs.append(model_xml)
        except Exception as e:
            traceback.print_exc()
            raise e


    metadata = pd.concat(metadata, axis=0)
    max_var = metadata.variance.max()
    # concatenate
    df = pd.concat(dfs, axis=0)
    model_merged = df.groupby(by=['s', 'f_f0', 'vbar20','wavelength'], sort=False).agg(aggregations).reset_index(drop=False)
    model_merged = cv.denormalize(model_merged, dens_exp, visc_exp, temp_exp)
    models_count = metadata.shape[0]
    nlambda = model_merged['wavelength'].nunique()
    wl_min = model_merged['wavelength'].min()
    wl_max = model_merged['wavelength'].max()
    axis_min = model_merged.min(axis=0)
    axis_max = model_merged.max(axis=0)
    for ax in axis:
        nxvals = model_merged[ax].nunique()
        temp_data = model_merged[['wavelength','signal',ax]].groupby(by=[ax,'wavelength'],sort=False).agg({
            'signal':'mean'}).reset_index().sort_values([ax,'wavelength'])
        zeros = []
        for x in temp_data[ax]:
            for y in temp_data['wavelength']:
                zeros.append((x,y,0))
        out_dfs = [pd.DataFrame(zeros,columns=[ax,'wavelength','signal'])]
        for axvl in temp_data[ax]:
            temp_vec = temp_data[temp_data[ax] == axvl]
            temp_cvec = temp_vec.loc[:,['signal']].to_numpy()
            temp_cvec = us_maths.gaussian_smoothing(temp_cvec,nsmooth)
            temp_vec = temp_vec.to_numpy()
            temp_data_out = [(x[0],x[1],y[0]) for x,y in zip(temp_vec,temp_cvec)]
            out_dfs.append(pd.DataFrame(temp_data_out,columns=[ax,'wavelength','signal']))
        out_data = pd.concat(out_dfs,axis=0)
        out_data = out_data.groupby(by=[ax,'wavelength'],sort=False).agg({'signal':'sum'}).reset_index()
        out_data.to_csv(dirname+'\\'+dir_input.split('\\')[-1] + f'-{ax}.csv')
        print(f'{ax} done')

if __name__ == '__main__':
    if len(sys.argv) != 6:
        dir_input = input('Enter path to directory which should be used:')
        try:
            nsmooth = input('Enter the smoothing factor:')
            nsmooth = int(nsmooth)
        except Exception as e:
            print('Invalid input as temperature')
            raise e
        try:
            temp_exp = input('Enter the temperature of the experiment in Kelvin:')
            temp_exp = float(temp_exp)
        except Exception as e:
            print('Invalid input as temperature')
            raise e
        try:
            visc_exp = input('Enter the viscosity of the solvent used in the experiment in mPas:')
            visc_exp = float(visc_exp)
        except Exception as e:
            print('Invalid input as viscosity')
            raise e
        try:
            dens_exp = input('Enter the density of the solvent used in the experiment:')
            dens_exp = float(dens_exp)
        except Exception as e:
            print('Invalid input as density')
            raise e
    else:
        dir_input = sys.argv[1]
        nsmooth = int(sys.argv[2])
        temp_exp = float(sys.argv[3])
        visc_exp = float(sys.argv[4])
        dens_exp = float(sys.argv[5])
    generate_mwl_mesh(dir_input, nsmooth, temp_exp, visc_exp, dens_exp)
