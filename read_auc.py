import struct
FORMAT_VERSION = 5

data = {}
# Open the file and read the data
with open('test.auc', 'rb') as f:
    # read magic string 4 bytes and decode it to utf8 to verify we read UltraScan Data
    magic = f.read(4).decode()
    if magic != 'UCDA':
        assert "No UltraScan data"
    # read version number 2 bytes and decode it to utf8
    version_data = f.read(2).decode()
    try:
        version_data = int(version_data)
    except Exception as e:
        raise e
    # check for version number
    if version_data > FORMAT_VERSION:
        assert "Bad version"
    data["version"] = version_data
    # version number defines wavelength format
    if version_data > 4:
        wvlf_new = True
    else:
        wvlf_new = False
    # read type of experiment 2 bytes and decode it to utf8
    type_data = f.read(2).decode()
    if type_data not in ["RA", "IP", "RI", "FI", "WA", "WI"]:
        assert "Invalid type"
    data["type"] = type_data
    # read 1 byte for cell number
    cell_raw = f.read(1)
    # convert byte in little endian format to unsigned integer
    data["cell"] = int.from_bytes(cell_raw, 'little', signed=False)
    # read 1 byte for channel
    data["channel"] = f.read(1).decode()
    tmp = f.read(16) # read rawGUID UltraScan internal
    # read 240 bytes description, filled with \x00
    data["description"] = f.read(240).decode().strip('\x00')
    # read 4 bytes as little endian float
    min_radius = struct.unpack('f', f.read(4))[0]
    f.read(4) # unused data
    # read 4 bytes as little endian float
    delta_radius = struct.unpack('f',f.read(4))[0]
    # read 4 bytes as little endian float
    min_data1 = struct.unpack('f',f.read(4))[0]
    # read 4 bytes as little endian float
    max_data1 = struct.unpack('f',f.read(4))[0]
    # read 4 bytes as little endian float
    min_data2 = struct.unpack('f',f.read(4))[0]
    # read 4 bytes as little endian float
    max_data2 = struct.unpack('f',f.read(4))[0]
    # read 2 bytes as little endian int signed
    scan_count = int.from_bytes(f.read(2), 'little', signed=True)
    data["scan_count"] = scan_count
    data["scanData"] = []
    # read every scan
    for i in range(0, scan_count):
        # read 4 bytes type to verify we are in DATA range
        type_data = f.read(4).decode()
        if type_data != "DATA":
            assert "Not UltraScan data"
        scan = {}
        # read 4 bytes as little endian float
        scan['temperature'] = struct.unpack('f',f.read(4))[0]
        # read 4 bytes as little endian float
        scan['rpm'] = struct.unpack('f',f.read(4))[0]
        # read 4 bytes as little endian int
        scan['seconds'] = int.from_bytes(f.read(4), 'little', signed=True)
        # read 4 bytes as little endian float
        scan['omega2t'] = struct.unpack('f',f.read(4))[0]
        # read 2 bytes as signed little endian int and calculate wavelength from it
        if wvlf_new:
            wavelength = int.from_bytes(f.read(2),'little', signed=True) / 10
        else:
            wavelength = int.from_bytes(f.read(2), 'little', signed=True) / 100 + 180
        scan['wavelength'] = wavelength
        # read 4 bytes as little endian float
        scan['delta_r'] = struct.unpack('f',f.read(4))[0]
        # read 4 bytes as little endian int
        value_count = int.from_bytes(f.read(4), 'little', signed=True)
        data['valueCount'] = value_count
        factor1 = (max_data1 - min_data1) / 65535.0
        factor2 = (max_data2 - min_data2) / 65535.0
        stdDev = min_data2 != 0.0 or max_data2 != 0.0
        reading_values = []
        stddevs = []
        for j in range(0, value_count):
            # read 2 bytes as unsigned little endian int
            reading_value = min_data1 + factor1 * int.from_bytes(f.read(2), 'little', signed=False)
            if stdDev:
                # read 2 bytes as unsigned little endian int
                sval = min_data2 + factor2 * int.from_bytes(f.read(2), 'little', signed=False)
            else:
                sval = 0.0
            # append read values to data
            reading_values.append(reading_value)
            stddevs.append(sval)
        scan["reading_values"] = reading_values
        if stdDev:
            scan["stddevs"] = stddevs
            scan["nz_stddev"] = True
        else:
            scan["stddevs"] = []
            scan["nz_stddev"] = False
        # read (value_count+7)/8 bytes which are a Bytearray indicating if the position was interpolated or not
        interpolated = f.read((value_count+7)//8)
        scan['interpolated'] = [byte & 1 for byte in bytearray(interpolated)]
        data["scanData"].append(scan)

    # construct radius vector
    radius = []
    for j in range(0, value_count):
        radius.append(delta_radius * j + min_radius)
    data["radius"] = radius

