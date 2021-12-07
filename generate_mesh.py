import traceback
import pandas as pd
import numpy as np
import os
import sys
import re
import math
import numba

colnames = ['analyte name', 'mw', 's', 'D', 'f', 'f_f0', 'vbar20', 'extinction', 'axial', 'sigma', 'delta',
            'oligomer', 'shape', 'type', 'molar', 'signal']
# path s D
if len(sys.argv) != 4:
    dir_input = input('Enter path to xml file which should be read:')
    print("Possible axis: "+", ".join(['mw', 's', 'D', 'f', 'f_f0', 'vbar20']))
    dim1 = input('Enter first dimension:')
    dim2 = input('Enter second dimension:')
else:
    dir_input = sys.argv[1]
    dim1 = sys.argv[2]
    dim2 = sys.argv[3]

# read analytes
try:
    model_xml = pd.read_xml(dir_input, xpath='//ModelData/model/analyte')
except Exception as e:
    traceback.print_exc()
    raise e
# read model variance
try:
    metadata = pd.read_xml(dir_input, xpath='//ModelData/model')
except Exception as e:
    traceback.print_exc()
    raise e

#########
# basic variables
#########

VROUND = 10.0
VNEGOF = 1.0 / VROUND
MAX_ANNO = 99.9 / VROUND
ncomp = model_xml.size[0]

# get range values for each of the 3 dimensions
max_range = model_xml[['mw', 's', 'D', 'f', 'f_f0', 'vbar20']].max(axis=0)
min_range = model_xml[['mw', 's', 'D', 'f', 'f_f0', 'vbar20']].min(axis=0)
# extend ranges a bit
max_range += (max_range - min_range) * 0.05
min_range -= (max_range - min_range) * 0.05
z_min = model_xml['signal'].min()
z_max = model_xml['signal'].max()
# handle one component only
if ncomp == 1:
    z_min *= 0.9
    z_max *= 1.10
    min_range *= 0.9
    max_range *= 1.1

xavg = ((min_range ** 2) ** 0.5 + (max_range ** 2) ** 0.5) * 0.5
yavg = ((min_range ** 2) ** 0.5 + (max_range ** 2) ** 0.5) * 0.5
x_norm = MAX_ANNO / xavg
y_norm = MAX_ANNO / yavg
z_norm = MAX_ANNO / z_max
powrx = x_norm.apply(lambda x: round(math.log10(x)))
powry = y_norm.apply(lambda x: round(math.log10(x)))
powrz = z_norm.apply(lambda x: round(math.log10(x)))
x_norm = powrx.apply(lambda x: pow(10.0,x))
x_norm = powry.apply(lambda x: pow(10.0,x))
y_norm = powrz.apply(lambda x: pow(10.0,x))
x_norm *= 0.1
#defaults
z_scaling = 1
grid_res = 150
peak_smooth = 130
peak_width = 0.3
x_rel_scale = 1
y_rel_scale = 1
# create zero numpy array
zdata = np.zeros(grid_res,grid_res,ncomp)
# create global properties
hixd = round(grid_res) / 5
hiyd = round(grid_res) / 5
loxd = loyd = 5
nxd = hixd
nyd = hiyd
zval = z_min
@numba.njit(nogil=True,parallel=True)
def calc_grid_component(counter: int, component: pd.DataFrame):
    zdata_comp = np.zeros(grid_res,grid_res)


