import pandas as pd

from utils.us_constants import DENS_20W, VISC_20W


def denormalize(data: pd.DataFrame, density_exp: float, viscousity_exp: float, temperature_exp: float) -> pd.DataFrame:
    """Convert normalized s20,w and D20,w to s and D"""
    # create the normalized columns
    data['s20w'] = data['s']
    data['D20w'] = data['D']

    # denormalize the sedimentation coefficient
    data['s'] = data['s20w'] * (1 - data['vbar20'] * density_exp) * VISC_20W / (
            (1 - data['vbar20'] * DENS_20W) * viscousity_exp)
    # denormalize the diffusion coefficient
    data['D'] = data['D20w'] * temperature_exp * VISC_20W / 293.15 / viscousity_exp

    return data


def normalize(data: pd.DataFrame, density_exp: float, viscousity_exp: float, temperature_exp: float) -> pd.DataFrame:
    """Convert experimental data (s,D) to s20,w and D20,w"""
    # denormalize the sedimentation coefficient
    data['s20w'] = data['s'] / (1 - data['vbar20'] * density_exp) / VISC_20W * (
            (1 - data['vbar20'] * DENS_20W) * viscousity_exp)
    # denormalize the diffusion coefficient
    data['D20w'] = data['D'] / temperature_exp / VISC_20W * 293.15 * viscousity_exp

    return data
