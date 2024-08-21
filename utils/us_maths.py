# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "scipy",
# ]
# ///
from math import exp, sqrt, pi
import numpy as np
from scipy.ndimage import gaussian_filter1d


def normal_distribution(sigma: float, mean: float, x: float):
    exponent = -sqrt((x - mean) / sigma) / 2.0
    return exp(exponent) / sqrt(2.0 * pi * sqrt(sigma))


def gaussian_smoothing(array: np.ndarray, smooth: int):
    """Apply a normalized Gaussian smoothing kernel that goes out to 2 standard deviations"""
    return gaussian_filter1d(array, smooth)


def dvirt_equal(d1, d2):
    eps = 1.e-4
    return abs((d1-d2)/d2)<eps
