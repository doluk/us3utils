import math
import sys
import traceback
from typing import List

from matplotlib import cm
import matplotlib.pyplot as plt
import numba
import numpy as np
from numpy import sqrt
import pandas as pd

colnames = ['analyte name', 'mw', 's', 'D', 'f', 'f_f0', 'vbar20', 'extinction', 'axial', 'sigma', 'delta', 'oligomer',
            'shape', 'type', 'molar', 'signal']
xy_combs = [('s', 'f_f0'), ('s', 'D'), ('s', 'vbar20'), ('s', 'mw'), ('D', 'f_f0'), ('D', 'vbar20'), ('D', 'mw'),
            ('mw', 'f_f0'), ('mw', 'vbar20')]
# path s D
if len(sys.argv) != 4:
    dir_input = input('Enter path to xml file which should be read:')
    print("Possible axis: " + ", ".join(['mw', 's', 'D', 'f', 'f_f0', 'vbar20']))
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

# get range values for each of the 3 dimensions
max_range = model_merged[[dim1, dim2]].max(axis=0)
min_range = model_merged[[dim1, dim2]].min(axis=0)
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
powrz = np.round(np.log10(z_norm))  # z_norm.apply(lambda x: round(math.log10(x)))
xy_norm = powrxy.apply(lambda x: pow(10.0, x))
z_norm = math.pow(10.0, powrz)

x_norm, y_norm = xy_norm[[dim1, dim2]]
x_norm *= 0.1
xavg, yavg = xyavg[[dim1, dim2]]
powrx, powry = powrxy[[dim1, dim2]]
if xavg * x_norm > MAX_ANNO:
    x_norm *= 0.1
    powrx -= 1
if yavg * y_norm > MAX_ANNO:
    y_norm *= 0.1
    powry -= 1
if z_max * z_norm > MAX_ANNO:
    z_norm *= 0.1
    powrz -= 1

min_range_dim1 = min_range[[dim1]].to_numpy()
max_range_dim1 = max_range[[dim1]].to_numpy()
min_range_dim2 = min_range[[dim2]].to_numpy()
max_range_dim2 = max_range[[dim2]].to_numpy()
min_range_dim1 *= x_norm
max_range_dim1 *= x_norm
min_range_dim2 *= y_norm
max_range_dim2 *= y_norm
z_min *= z_norm
z_max *= z_norm
dim_1_sign = np.int(min_range_dim1 / np.abs(min_range_dim1))
dim_2_sign = min_range_dim2 / np.abs(min_range_dim2)
x_min = min_range_dim1 = np.floor(min_range_dim1 * VROUND * dim_1_sign) / VROUND * dim_1_sign
y_min = min_range_dim2 = np.floor(min_range_dim2 * VROUND * dim_2_sign) / VROUND * dim_2_sign
x_max = max_range_dim1 = np.ceil(max_range_dim1 * VROUND) / VROUND
y_max = max_range_dim2 = np.ceil(max_range_dim2 * VROUND) / VROUND
min_range_dim1 = np.array([0]) if min_range_dim1 == 0 else min_range_dim1
min_range_dim1 = min_range_dim1 - VNEGOF if min_range_dim1 < 0 else min_range_dim1
min_range_dim2 = min_range_dim2 - VNEGOF if min_range_dim2 < 0 else min_range_dim2
z_max = np.ceil(z_max * 10) / 10
z_min = np.array([0])

# defaults
z_scaling = 1
grid_res = 150
peak_smooth = 130
peak_width = 0.3
x_rel_scale = 1
y_rel_scale = 1
# create zero numpy array
zdata: np.ndarray = np.full(shape=(grid_res, grid_res), fill_value=z_min, dtype=np.float32)
zdata_cntrl: np.ndarray = np.full(shape=(grid_res, grid_res), fill_value=z_min)
# create global properties
hixd = hiyd = np.array([round(grid_res) / 5])
loxd = loyd = np.array([5])
nxd = hixd
nyd = hiyd
zval = z_min
xpinc = (grid_res - 1) / (max_range_dim1 - min_range_dim1)
ypinc = (grid_res - 1) / (max_range_dim2 - min_range_dim2)
zfact = z_scaling
xdif = math.acos(pow(1e-18, (1.0 / peak_smooth))) * peak_width / (math.pi * 0.5 * sqrt(2.0))
dfac = math.pi * 0.5 / peak_width
nxd = np.round(xdif * xpinc) * 2 + 2
nyd = np.round(xdif * ypinc) * 2 + 2
nxd = nxd if nxd < hixd else hixd
nyd = nyd if nyd < hiyd else hiyd
nxd = nxd if nxd > loxd else loxd
nyd = nyd if nyd > loyd else loyd
components = model_merged[[dim1, dim2, 'signal']].to_numpy()


@numba.njit(nogil=True, parallel=True)
def run_grid_calc(dimension1: str, dimension2: str, zdata: np.ndarray):
    for i in numba.prange(ncomp):
        zdata = calc_grid_component(components[i], zdata)
    return zdata


@numba.njit(nogil=True, debug=True)
def calc_grid_component(comp: np.ndarray, zdata):
    # get the components relevant properties
    xval = comp[0] * x_norm - min_range_dim1
    yval = comp[1] * y_norm - min_range_dim2
    zval = comp[2] * z_norm
    rx = (xval * xpinc).astype(np.int64)  # raster index of model x
    fx = rx - nxd
    lx = rx + nxd
    fx = fx.astype(np.int64) if fx.astype(np.int64) > np.zeros((1,)).astype(np.int64) \
        else np.zeros((1,)).astype(np.int64)
    lx = lx.astype(np.int64) if lx.astype(np.int64) < np.full(shape=(1,), fill_value=grid_res).astype(np.int64) \
        else np.full(shape=(1,), fill_value=grid_res).astype(np.int64)
    ry = (yval * ypinc).astype(np.int64)  # raster index of model y
    fy = ry - nyd
    ly = ry + nyd
    fy = fy.astype(np.int64) if fy.astype(np.int64) > np.zeros((1,)).astype(np.int64) \
        else np.zeros((1,)).astype(np.int64)
    ly = ly.astype(np.int64) if ly.astype(np.int64) < np.full(shape=(1,), fill_value=grid_res).astype(np.int64) \
        else np.full(shape=(1,), fill_value=grid_res).astype(np.int64)
    for ii in numba.prange(lx.astype(np.int64)[0] - fx.astype(np.int64)[0]):
        ii = ii + fx.astype(np.int64)[0]
        xdif = np.square(ii / xpinc - xval)
        for jj in numba.prange(ly.astype(np.int64)[0] - fy.astype(np.int64)[0]):

            jj = jj + fy.astype(np.int64)[0]
            ydif = np.square(jj / ypinc - yval)

            dist = np.sqrt(xdif + ydif)

            if dist <= np.array([peak_width]):
                zdata[int(jj), int(ii)] = zdata[int(jj), int(ii)] + (
                        np.array([zval]) * np.power(np.cos(dist * dfac), peak_smooth) * np.array([zfact]))[0]
    return zdata


zdata = run_grid_calc(dim1, dim2, zdata)
# generate axis
x_axis, x_step = np.linspace(min_range_dim1, max_range_dim1, grid_res, retstep=True)
y_axis, y_step = np.linspace(min_range_dim2, max_range_dim2, grid_res, retstep=True)
xy_coords: List[np.ndarray] = np.meshgrid(x_axis, y_axis)
xyz_data = np.array([[x, y, z] for x, y, z in zip(xy_coords[0].ravel(), xy_coords[1].ravel(), zdata.ravel())])
xyz_frame = pd.DataFrame(xyz_data, columns=[dim1, dim2, 'signal'])
xyz_frame.to_csv(".".join(dir_input.split('.')[:-1]) + f'{dim1}-{dim2}.csv')
# plot figure as preview
fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
surf = ax.plot_surface(xy_coords[0], xy_coords[1], zdata, cmap=cm.coolwarm, linewidth=0, antialiased=True)
ax.set_zlim(z_min, z_max)
ax.set_xlim(min_range_dim1, max_range_dim1)
ax.set_ylim(min_range_dim2, max_range_dim2)
ax.zaxis.set_major_formatter('{x:.02f}')
plt.show()
print('finished')
