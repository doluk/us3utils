import struct

def read_tmst(filename):
    with open(filename, 'rb') as f:
        # Read header
        magic_number = f.read(4).decode('utf-8')
        major_version = struct.unpack('>B', f.read(1))[0]
        minor_version = struct.unpack('>B', f.read(1))[0]

        # Assuming the rest of the header information (like time_count, constant_incr, etc.) is known beforehand or hard-coded

        # Read data records
        records = []
        while True:
            try:
                time = struct.unpack('>I', f.read(4))[0]  # I4
                raw_speed = struct.unpack('>f', f.read(4))[0]  # F4
                set_speed = struct.unpack('>I', f.read(4))[0]  # I4
                omega2T = struct.unpack('>f', f.read(4))[0]  # F4
                temperature = struct.unpack('>f', f.read(4))[0]  # F4
                step = struct.unpack('>H', f.read(2))[0]  # I2
                scan = struct.unpack('>H', f.read(2))[0]  # I2

                record = {
                    'Time': time,
                    'RawSpeed': raw_speed,
                    'SetSpeed': set_speed,
                    'Omega2T': omega2T,
                    'Temperature': temperature,
                    'Step': step,
                    'Scan': scan
                }
                records.append(record)
            except struct.error:
                # End of file
                break

    return {
        'MagicNumber': magic_number,
        'MajorVersion': major_version,
        'MinorVersion': minor_version,
        'Records': records
    }
