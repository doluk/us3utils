import struct

def read_mwrs(filename: str):
    with open(filename, 'rb') as f:
        data = f.read()

    # Reconstruct the header from the binary data
    (cell, channel, scan, set_speed, speed, temperature, omegat2, seconds, radius_count, radius_start, radius_step,
     lambda_count) = struct.unpack('>BcHHHhfiHHHH', data[:26])
    channel = channel.decode()

    position = 26
    # Read the wavelengths
    lambdas = [struct.unpack('>H', data[position + 2 * i:position + 2 * (i + 1)])[0] for i in range(lambda_count)]
    position += 2 * lambda_count

    # Read the intensities
    intensity = []
    for _ in lambdas:
        intensities = []
        for i in range(radius_count):
            radius_struct = struct.unpack('>i', data[position + 4 * i:position + 4 * (i + 1)])
            intensities.append(radius_struct[0])
        position += 4 * radius_count
        intensity.append(intensities)

    # Convert temperature and radii back to original values
    temperature = temperature / 10
    radius_start = radius_start / 1000
    radius_step = radius_step / 10000

    return cell, channel.decode(), scan, set_speed, speed, temperature, omegat2, seconds, radius_count, radius_start, radius_step, lambdas, intensity
