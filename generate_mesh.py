import traceback

from numpy import sqrt
import pandas as pd
import numpy as np
import os
import sys
import re
import math
import numba

colnames = ['analyte name', 'mw', 's', 'D', 'f', 'f_f0', 'vbar20', 'extinction', 'axial', 'sigma', 'delta', 'oligomer',
            'shape', 'type', 'molar', 'signal']
# path s D
if len(sys.argv) != 4:
    dir_input = r'C:\Users\Lukas\PycharmProjects\us3utils\2667_Paper%2DSA-IT%\2667_Paper#3A294#e2111040649_a2111061109_2DSA-IT_097041_i01.xml'#input('Enter path to xml file which should be read:')
    print("Possible axis: " + ", ".join(['mw', 's', 'D', 'f', 'f_f0', 'vbar20']))
    dim1 = 's' #input('Enter first dimension:')
    dim2 = 'f_f0' #input('Enter second dimension:')
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
ncomp = model_xml.shape[0]

# get range values for each of the 3 dimensions
max_range = model_xml[['mw', 's', 'D', 'f', 'f_f0', 'vbar20']].max(axis=0)
min_range = model_xml[['mw', 's', 'D', 'f', 'f_f0', 'vbar20']].min(axis=0)
# extend ranges a bit
max_range += (max_range[[dim1,dim2]] - min_range[[dim1,dim2]]) * 0.05
min_range -= (max_range[[dim1,dim2]] - min_range[[dim1,dim2]]) * 0.05
z_min = model_xml['signal'].min()
z_max = model_xml['signal'].max()
# handle one component only
if ncomp == 1:
    z_min *= 0.9
    z_max *= 1.10
    min_range *= 0.9
    max_range *= 1.1

xyavg = ((min_range ** 2) ** 0.5 + (max_range ** 2) ** 0.5) * 0.5
xy_norm = MAX_ANNO / xyavg
z_norm = MAX_ANNO / z_max
powrxy = xy_norm.apply(lambda x: round(math.log10(x)))
powrz = np.round(np.log10(z_norm)) #z_norm.apply(lambda x: round(math.log10(x)))
xy_norm = powrxy.apply(lambda x: pow(10.0, x))
z_norm = np.pow(10.0, powrz)
xy_norm *= 0.1
x_norm, y_norm = xy_norm
xavg, yavg = xyavg
powrx, powry = powrxy
if xavg * x_norm > MAX_ANNO:
    x_norm *= 0.1
    powrx -= 1
if yavg*y_norm > MAX_ANNO:
    y_norm *= 0.1
    powry -= 1
if z_max*z_norm > MAX_ANNO:
    z_norm *= 0.1
    powrz -= 1
    





# defaults
z_scaling = 1
grid_res = 150
peak_smooth = 130
peak_width = 0.3
x_rel_scale = 1
y_rel_scale = 1
# create zero numpy array
zdata: np.ndarray  = np.full(shape=(grid_res, grid_res), fill_value=z_min)
# create global properties
hixd = round(grid_res) / 5
hiyd = round(grid_res) / 5
loxd = loyd = 5
nxd = hixd
nyd = hiyd
zval = z_min
xpinc = (grid_res - 1) / (max_range[dim1] - min_range[dim1])
ypinc = (grid_res - 1) / (max_range[dim2] - min_range[dim2])
zfact = z_scaling
xdif = math.acos(pow(1e-18, (1.0 / peak_smooth))) * peak_width / (math.pi * 0.5 * sqrt(2.0))
dfac = math.pi * 0.5 / peak_width
nxd = round(xdif * xpinc) * 2 + 2
nyd = round(xdif * ypinc) * 2 + 2
nxd = nxd if nxd < hixd else hixd
nyd = nyd if nyd < hiyd else hiyd
nxd = nxd if nxd > loxd else loxd
nyd = nyd if nyd > loyd else loyd
# TODO Calculate output properly as x,y,z data tripples

@numba.njit(nogil=True, parallel=True)
def run_grid_calc():
    for i in numba.prange(ncomp):
        comp = model_xml[[dim1, dim2, 'signal']][i].to_numpy()
        calc_grid_component(i, comp, nxd, nyd)
        print(f'{i}/{ncomp} done')

@numba.njit(nogil=True)
def calc_grid_component(counter: int, comp: np.ndarray):
    """Current component as np.ndarray containing xyz data"""
    # calculate spread of each model point to a radius or raster points
    xval = comp[0] * x_norm - min_range[[dim1]].to_numpy()
    yval = comp[1] * y_norm - min_range[[dim2]].to_numpy()
    zval = comp[2] * z_norm
    rx = int(xval * xpinc)  # raster index of model x
    fx = rx - nxd
    lx = rx - nxd
    fx = fx if fx > 0 else 0
    lx = lx if lx < grid_res else grid_res
    ry = int(yval * ypinc)  # raster index of model y
    fy = ry - nyd
    ly = ry - nyd
    fy = fy if fy > 0 else 0
    ly = ly if ly < grid_res else grid_res
    # iterate over all rows
    for ii in range(fx, lx):
        xdif = np.square(ii / xpinc.to_numpy() - xval)
        for jj in range(fy, ly):
            ydif = np.square(jj / ypinc.to_numpy() - yval)
            # distance of raster point from model point
            dist = np.sqrt(xdif + ydif)
            if dist <= peak_width:
                zdata[ii, jj] += zval * pow(math.cos(dist * dfac), peak_smooth) * zfact

run_grid_calc()
zdata.tofile(".".join(dir_input.split('.')[:-1])+'.csv',sep=',')