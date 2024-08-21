# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "llvmlite",
#     "numba",
#     "numpy",
#     "pandas",
# ]
# ///
import math
import sys
import traceback

import numba
import numpy as np
from numpy import sqrt
import pandas as pd

from utils import converter as cv

colnames = ['analyte name', 'mw', 's', 'D', 'f', 'f_f0', 'vbar20', 'extinction', 'axial', 'sigma', 'delta', 'oligomer',
            'shape', 'type', 'molar', 'signal']
#xy_combs = [('s', 'f_f0'), ('s', 'D'), ('s', 'vbar20'), ('s', 'mw'), ('D', 'f_f0'), ('D', 'vbar20'), ('D', 'mw'),
#            ('s20w', 'f_f0'), ('s20w', 'D20w'), ('s20w', 'vbar20'), ('s20w', 'mw'), ('D20w', 'f_f0'),
#            ('D20w', 'vbar20'), ('D20w', 'mw'), ('s', 'D20w'), ('s20w', 'D'), ('mw', 'f_f0'), ('mw', 'vbar20')]
xy_combs = [ ('s', 'D'), ('s20w', 'D20w'), ('s', 'D20w'), ('s20w', 'D')]
# xy_combs = [('s', 'D')]
axis = ['mw', 's', 'D', 'f', 'f_f0', 'vbar20', 's20w', 'D20w']


@numba.njit(nogil=True, parallel=True)
def run_grid_calc(components: np.ndarray, min_range_dim1, x_norm, nxd, xpinc, min_range_dim2, y_norm, nyd, ypinc,
                  z_norm, zfact, dfac, grid_res):
    """Calculate the z-mesh for the given components for two dimensions"""
    # create zero numpy array
    zdata: np.ndarray = np.full(shape=(grid_res, grid_res), fill_value=z_min, dtype=np.float32)
    # Iterate over every component
    for i in numba.prange(ncomp):
        zdata += calc_grid_component(components[i], min_range_dim1, x_norm, nxd, xpinc, min_range_dim2, y_norm, nyd,
                                     ypinc, z_norm, zfact, dfac, grid_res)
    return zdata


@numba.njit(nogil=True)
def calc_grid_component(comp: np.ndarray, min_range_dim1, x_norm, nxd, xpinc, min_range_dim2, y_norm, nyd, ypinc,
                        z_norm, zfact, dfac, grid_res):
    """Calculate the influence of one component onto the z-mesh"""
    # create zero numpy array
    zdata: np.ndarray = np.full(shape=(grid_res, grid_res), fill_value=z_min, dtype=np.float32)
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


def calc_all_grids(z_norm, powrz, z_min, z_max):
    xyz_dfs = []
    if z_max * z_norm > MAX_ANNO:
        z_norm *= 0.1
        powrz -= 1
    z_min *= z_norm
    z_max *= z_norm
    for c, dims in enumerate(xy_of_interest):
        [dimension1, dimension2] = dims
        print(f'Starting grid calculation {c + 1}/{len(xy_of_interest)}')
        xavg, yavg = xyavg[[dimension1, dimension2]]
        powrx, powry = powrxy[[dimension1, dimension2]]
        x_norm, y_norm = xy_norm[[dimension1, dimension2]]
        x_norm *= 0.1
        if xavg * x_norm > MAX_ANNO:
            x_norm *= 0.1
            powrx -= 1
        if yavg * y_norm > MAX_ANNO:
            y_norm *= 0.1
            powry -= 1

        min_range_dim1 = min_range[[dimension1]].to_numpy()
        max_range_dim1 = max_range[[dimension1]].to_numpy()
        min_range_dim2 = min_range[[dimension2]].to_numpy()
        max_range_dim2 = max_range[[dimension2]].to_numpy()
        min_range_dim1 *= x_norm
        max_range_dim1 *= x_norm
        min_range_dim2 *= y_norm
        max_range_dim2 *= y_norm

        dim_1_sign = int(min_range_dim1 / np.abs(min_range_dim1))
        dim_2_sign = min_range_dim2 / np.abs(min_range_dim2)
        min_range_dim1 = np.floor(min_range_dim1 * VROUND * dim_1_sign) / VROUND * dim_1_sign
        min_range_dim2 = np.floor(min_range_dim2 * VROUND * dim_2_sign) / VROUND * dim_2_sign
        max_range_dim1 = np.ceil(max_range_dim1 * VROUND) / VROUND
        max_range_dim2 = np.ceil(max_range_dim2 * VROUND) / VROUND
        min_range_dim1 = np.array([0]) if min_range_dim1 == 0 else min_range_dim1
        min_range_dim1 = min_range_dim1 - VNEGOF if min_range_dim1 < 0 else min_range_dim1
        min_range_dim2 = min_range_dim2 - VNEGOF if min_range_dim2 < 0 else min_range_dim2
        z_max_t = np.array([np.ceil(z_max * 10) / 10], dtype=np.float64)
        z_min_t = np.array([0], dtype=np.float64)
        # create global properties
        hixd = hiyd = np.array([round(grid_res) / 5])
        loxd = loyd = np.array([5])
        nxd = hixd
        nyd = hiyd
        zval = z_min
        delta_dim1: np.ndarray = max_range_dim1 - min_range_dim1
        delta_dim2: np.ndarray = max_range_dim2 - min_range_dim2
        xpinc = (grid_res - 1) / (delta_dim1 if delta_dim1 else 1)
        ypinc = (grid_res - 1) / (delta_dim2 if delta_dim2 else 1)
        zfact = z_scaling
        xdif = math.acos(pow(1e-18, (1.0 / peak_smooth))) * peak_width / (math.pi * 0.5 * sqrt(2.0))
        dfac = math.pi * 0.5 / peak_width
        nxd = np.round(xdif * xpinc) * 2 + 2
        nyd = np.round(xdif * ypinc) * 2 + 2
        nxd = nxd if nxd < hixd else hixd
        nyd = nyd if nyd < hiyd else hiyd
        nxd = nxd if nxd > loxd else loxd
        nyd = nyd if nyd > loyd else loyd
        components = model_merged[[dimension1, dimension2, 'signal']].to_numpy()
        print(f"x_min={min_range_dim1} x_max={max_range_dim1} x_norm={x_norm}")
        print(f"y_min={min_range_dim2} y_max={max_range_dim2} y_norm={y_norm}")
        print(f"z_min={z_min_t} z_max={z_max_t} z_norm={z_norm}")
        zdata = run_grid_calc(components, min_range_dim1, x_norm, nxd, xpinc, min_range_dim2, y_norm, nyd, ypinc,
                              z_norm, zfact, dfac, grid_res)
        x_axis, x_step = np.linspace(min_range_dim1, max_range_dim1, grid_res, retstep=True)
        y_axis, y_step = np.linspace(min_range_dim2, max_range_dim2, grid_res, retstep=True)
        xy_coords = np.meshgrid(x_axis, y_axis)
        xyz_data = np.array([[x/x_norm, y/y_norm, z/z_norm] for x, y, z in zip(xy_coords[0].ravel(), xy_coords[
            1].ravel(),
                                                              zdata.ravel())])
        xyz_frame = pd.DataFrame(xyz_data, columns=[dimension1, dimension2, f'signal-{dimension1}-{dimension2}'])
        xyz_dfs.append(xyz_frame)
        print(f'Finished grid calculation {c + 1}/{len(xy_of_interest)}')
    data = pd.concat(xyz_dfs, axis=1)
    data.to_csv(".".join(dir_input.split('.')[:-1]) + '.csv')


if len(sys.argv) == 7:
    dir_input = sys.argv[1]
    temp_exp = float(sys.argv[2])
    visc_exp = float(sys.argv[3])
    dens_exp = float(sys.argv[4])
    xy_of_interest = [x for x in sys.argv[5:7] if x in axis]
    if len(xy_of_interest) != 2:
        print('Invalid specified axis')
        exit(1)
    else:
        xy_of_interest = [xy_of_interest]

elif len(sys.argv) == 5:
    dir_input = sys.argv[1]
    temp_exp = float(sys.argv[2])
    visc_exp = float(sys.argv[3])
    dens_exp = float(sys.argv[4])
    xy_of_interest = xy_combs
else:
    dir_input = input('Enter path to xml file which should be read:')
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
    xy_of_interest = xy_combs

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
                ('mw', 'D', 'f')}
aggregations['signal'] = 'sum'
model_merged = model_xml.groupby(by=['s', 'f_f0', 'vbar20'], sort=False).agg(aggregations).reset_index(drop=False)
model_merged = cv.denormalize(model_merged, dens_exp, visc_exp, temp_exp)
#########
# basic variables
#########

VROUND = 10.0
VNEGOF = 1.0 / VROUND
MAX_ANNO = 99.9 / VROUND
ncomp = model_merged.shape[0]
# defaults
z_scaling = 1
grid_res = 250
peak_smooth = 130
peak_width = 0.3
x_rel_scale = 1
y_rel_scale = 1
# get range values for each dimension
max_range = model_merged.max(axis=0)
min_range = model_merged.min(axis=0)
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

calc_all_grids(z_norm, powrz, z_min, z_max)
print('finish')
