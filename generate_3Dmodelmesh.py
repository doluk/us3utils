import traceback
from typing import List

from numpy import sqrt
import pandas as pd
import numpy as np
import os
import sys
import re
import math
import numba
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator

colnames = ['analyte name', 'mw', 's', 'D', 'f', 'f_f0', 'vbar20', 'extinction', 'axial', 'sigma', 'delta', 'oligomer',
            'shape', 'type', 'molar', 'signal']
xy_combs = [('s','f_f0'),('s','D'),('s','vbar20'),('s','mw'),('D','f_f0'),('D','vbar20'),('D','mw'),('mw','f_f0'),
            ('mw','vbar20')]
# path s D
if len(sys.argv) != 4:
    dir_input = r'C:\Users\Lukas\PycharmProjects\us3utils\2667_Paper%2DSA-MC%mcN050\2667_Paper#3A290#e2111040649_a2111061137_2DSA-MC_097119_mcN050.xml'#input('Enter path to xml file which should be read:')
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
aggregations = {col: 'mean' for col in
                ('mw', 'D', 'f', 'extinction', 'axial', 'sigma', 'delta', 'oligomer', 'shape', 'type', 'molar')}
aggregations['signal'] = 'sum'
model_merged = model_xml.groupby(by=['s', 'f_f0', 'vbar20'], sort=False).agg(aggregations).reset_index(drop=False)

#########
# basic variables
#########

VROUND = 10.0
VNEGOF = 1.0 / VROUND
MAX_ANNO = 99.9 / VROUND
ncomp = model_merged.shape[0]
model_merged['s'] *= 1e13
# get range values for each of the 3 dimensions
max_range = model_merged[[dim1,dim2]].max(axis=0)
min_range = model_merged[[dim1,dim2]].min(axis=0)
# extend ranges a bit
max_range += (max_range - min_range) * 0.05
min_range -= (max_range - min_range) * 0.05
z_min = model_merged['signal'].min()
z_max = model_merged['signal'].max()
# handle one component only
if ncomp == 1:
    z_min *= 0.9
    z_max *= 1.10
    min_range *= 0.9
    max_range *= 1.1

xyavg = (np.abs(min_range) + np.abs(max_range)) * 0.5
xy_norm = MAX_ANNO / xyavg
z_norm = MAX_ANNO / z_max
powrxy = xy_norm.apply(lambda x: round(math.log10(x)))
powrz = np.round(np.log10(z_norm)) #z_norm.apply(lambda x: round(math.log10(x)))
xy_norm = powrxy.apply(lambda x: pow(10.0, x))
z_norm = math.pow(10.0, powrz)
xy_norm *= 0.1
x_norm, y_norm = xy_norm[[dim1,dim2]]
xavg, yavg = xyavg[[dim1,dim2]]
powrx, powry = powrxy[[dim1,dim2]]
# defaults
z_scaling = 1
grid_res = 150
peak_smooth = 130
peak_width = 0.3
x_rel_scale = 1
y_rel_scale = 1
# create zero numpy array
zdata: np.ndarray = np.full(shape=(grid_res, grid_res), fill_value=z_min)
zdata_cntrl: np.ndarray = np.full(shape=(grid_res, grid_res), fill_value=z_min)
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
components = model_merged[[dim1, dim2, 'signal']].to_numpy()

min_range_dim1 = min_range[[dim1]].to_numpy()
max_range_dim1 = max_range[[dim1]].to_numpy()
min_range_dim2 = min_range[[dim2]].to_numpy()
max_range_dim2 = max_range[[dim2]].to_numpy()
#@numba.njit(nogil=True,parallel=True)
#def calc_all_grids():
#    for dimemsion1, dimension2 in xy_combs:
#        x_norm, y_norm = xy_norm[[dimemsion1,dimension2]]
#        xavg, yavg = xyavg[[dimemsion1,dimension2]]
#        powrx, powry = powrxy[[dimemsion1,dimension2]]
#        # create zero numpy array
#        zdata: np.ndarray = np.full(shape=(grid_res, grid_res), fill_value=z_min)
#        # create global properties
#        hixd = round(grid_res) / 5
#        hiyd = round(grid_res) / 5
#        loxd = loyd = 5
#        nxd = hixd
#        nyd = hiyd
#        zval = z_min
#        xpinc = (grid_res - 1) / (max_range[dim1] - min_range[dim1])
#        ypinc = (grid_res - 1) / (max_range[dim2] - min_range[dim2])
#        zfact = z_scaling
#        xdif = math.acos(pow(1e-18, (1.0 / peak_smooth))) * peak_width / (math.pi * 0.5 * sqrt(2.0))
#        dfac = math.pi * 0.5 / peak_width
#        nxd = round(xdif * xpinc) * 2 + 2
#        nyd = round(xdif * ypinc) * 2 + 2
#        nxd = nxd if nxd < hixd else hixd
#        nyd = nyd if nyd < hiyd else hiyd
#        nxd = nxd if nxd > loxd else loxd
#        nyd = nyd if nyd > loyd else loyd
#
#        if xavg * x_norm > MAX_ANNO:
#            x_norm *= 0.1
#            powrx -= 1
#        if yavg * y_norm > MAX_ANNO:
#            y_norm *= 0.1
#            powry -= 1
#        if z_max * z_norm > MAX_ANNO:
#            z_norm *= 0.1
#            powrz -= 1
#        run_grid_calc(dimemsion1,dimension2,)
#        zdata.tofile(".".join(dir_input.split('.')[:-1]) + f'{dimemsion1}-{dimension2}.csv', sep=',')

#@numba.njit(nogil=True, parallel=True)
def run_grid_calc(dimension1: str,dimension2: str):
    for i in range(ncomp):
        comp = components[i]
        #print(comp)
        calc_grid_component(comp)
        print(f'{i+1}/{ncomp} done')

#@numba.njit(nogil=True)
def calc_grid_component(comp: np.ndarray):
    """Current component as np.ndarray containing xyz data"""
    if comp[2] == z_max:
        print(comp)
        sw = True
        pass
    else:
        sw = False
    # calculate spread of each model point to a radius or raster points
    #xval = comp[0] - min_range_dim1#comp[0] * x_norm - min_range_dim1
    yval = comp[1] - min_range_dim2#comp[1] * y_norm - min_range_dim2
    #zval = comp[2] * z_norm#comp[2] * z_norm
    xval = comp[0] * x_norm - min_range_dim1
    #yval = comp[1] * y_norm - min_range_dim2
    zval = comp[2] * z_norm
    rx = (xval * xpinc).astype(np.int64)  # raster index of model x
    fx = rx - nxd
    lx = rx + nxd
    fx = fx if fx > 0 else 0
    lx = lx if lx < grid_res else grid_res
    if sw:
        print(f'rx: {rx}, lx: {lx}, fx: {fx}')
    #lx = lx if lx > fx else fx
    ry = (yval * ypinc).astype(np.int64)  # raster index of model y
    fy = ry - nyd
    ly = ry + nyd
    fy = fy if fy > 0 else 0
    ly = ly if ly < grid_res else grid_res
    if sw:
        print(f'ry: {ry}, ly: {ly}, fy: {fy}')
    #ly = ly if ly > fy else fy
    # iterate over all rows
    for ii in range(int(fx), int(lx)):
        xdif = np.square(ii / xpinc - xval)
        for jj in range(int(fy), int(ly)):
            ydif = np.square(jj / ypinc - yval)
            # distance of raster point from model point
            dist = np.sqrt(xdif + ydif)
            if dist <= peak_width:
                #print(ii,'|',jj)
                #print(zval * pow(math.cos(dist * dfac), peak_smooth) * zfact)
                zdata[jj, ii] += zval * pow(math.cos(dist * dfac), peak_smooth) * zfact
                zdata_cntrl[jj,ii] += comp[2]*100

run_grid_calc(dim1,dim2)
zdata.tofile(".".join(dir_input.split('.')[:-1])+'.csv',sep=',')
# generate axis
x_axis,x_step = np.linspace(min_range[[dim1]],max_range[[dim1]],grid_res,retstep=True)
y_axis,y_step = np.linspace(min_range[[dim2]],max_range[[dim2]],grid_res,retstep=True)
xy_coords: List[np.ndarray] = np.meshgrid(x_axis,y_axis)
xyz_data = np.array([[x,y,z] for x,y,z in zip(xy_coords[0].ravel(),xy_coords[1].ravel(),zdata.ravel())])
xyz_data.tofile(".".join(dir_input.split('.')[:-1]) + f'{dim1}-{dim2}.csv', sep=',')
fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
surf = ax.plot_surface(xy_coords[0], xy_coords[1], zdata, cmap=cm.coolwarm,
                       linewidth=0, antialiased=False)
ax.set_zlim(z_min,zdata.max()*1.1)
ax.set_xlim(min_range_dim1,max_range_dim1)
ax.set_ylim(min_range_dim2,max_range_dim2)
ax.zaxis.set_major_formatter('{x:.02f}')

# Add a color bar which maps values to colors.
fig.colorbar(surf, shrink=0.5, aspect=5)

plt.show()
fig1, ax1 = plt.subplots(subplot_kw={"projection": "3d"})
surf = ax1.plot_surface(xy_coords[0], xy_coords[1], zdata_cntrl, cmap=cm.coolwarm,
                       linewidth=0, antialiased=False)
ax1.set_zlim(z_min,zdata_cntrl.max()*1.1)
ax1.set_xlim(min_range_dim1,max_range_dim1)
ax1.set_ylim(min_range_dim2,max_range_dim2)
ax1.zaxis.set_major_formatter('{x:.02f}')

# Add a color bar which maps values to colors.
fig.colorbar(surf, shrink=0.5, aspect=5)

plt.show()
print('finish')