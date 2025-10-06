import struct

def write_mwrs(cell: int, channel: str, scan: int, set_speed: int, speed: int, temperature: int, omegat2: float,
               seconds: int, radius_start: float, radius_step: float, lambdas: list[int],
               radius_points: int, intensity: list[list[float]]) -> bytes:
    """Write the mwrs file"""
    # change the format specifier to big-endian
    bin_data = struct.pack('>BcHHHhfiHHHH', cell, channel.encode('ASCII'), scan, set_speed, speed, int(temperature *
                                                                                                       10),
                           omegat2,
                           seconds, radius_points, int(radius_start * 1000), int(radius_step * 10000), len(lambdas))

    # pack the wavelengths
    for lamb in lambdas:
        bin_data += struct.pack('>H', lamb)

    # pack the intensity values
    for intensities in intensity:
        offset = min(intensities + [0])
        for intens in intensities:
            bin_data += struct.pack('>I', int((intens - offset) * 10000))

    return bin_data
