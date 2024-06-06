import argparse
import collections
from pathlib import Path
import struct

from write_auc import write_auc
from write_mwrs import write_mwrs


def count_scans(directory):
    """Count the number of scans for each cell in the directory"""
    # Dictionary to store cell: scan count pairs
    scan_counts = collections.defaultdict(int)

    # Loop through all files in the directory
    for filename in Path(directory).iterdir():
        # Check if the file is .IPX where X is cell number
        if filename.suffix.startswith('.IP') and filename.suffix[3:].isdigit():
            # Get the cell number
            cell_number = int(filename.suffix[3:])

            # Increment the count of scans for this cell
            scan_counts[cell_number] = max(scan_counts[cell_number], int(filename.stem))

    # Output the scan count for each cell
    for cell, scan_count in scan_counts.items():
        print(f'Cell {cell} has {scan_count} scans.')
    return scan_counts

def generate_scans_to_read(scan_pairs):
    """Generate the list of scans to read from the pairs"""
    scans_to_read = set()
    print(scan_pairs)
    for pair in scan_pairs:
        [lower, upper] = pair
        for i in range(int(lower), int(upper)+1):
            scans_to_read.add(i)
    scans_to_read = sorted(scans_to_read, key=lambda x: int(x))
    return scans_to_read


def read_scans(directory, scans_to_read, cells):
    """Read the scans from the directory"""
    raw_scans = {}
    for scan in scans_to_read:
        for cell in cells:
            filename = Path(directory) / f'{scan:05}.IP{cell}'
            data = {'cell': cell, 'scan': scan, 'channel': 'A'}
            if filename.exists():
                print(f'Reading {filename}')
                with open(filename) as f:
                    radii = []
                    full_radii = []
                    readings = []
                    radius_old = 0
                    for c, line in enumerate(f.readlines()):
                        if c == 0:
                            data['description'] = line.strip().split(', ')[1]
                        elif c == 1:
                            [idk, cell2, temperature, speed, seconds, omega2t, wavelength, idk4] = line.strip().split()
                            data['temperature'] = float(temperature)
                            data['speed'] = int(speed)
                            data['seconds'] = int(seconds)
                            data['omega2t'] = float(omega2t)
                            data['wavelength'] = int(wavelength)
                            if cell != int(cell2):
                                raise Exception(f'Cell {cell} does not match cell {cell2} in file {filename}')
                        else:
                            line = line.strip().split()
                            radius = float(line[0])
                            reading = float(line[-1])
                            readings.append(reading)
                            full_radii.append(radius)
                            if not radius_old:
                                radius_old = radius
                                data['radius_start'] = radius
                            else:
                                radii.append(abs(radius - radius_old))
                                radius_old = radius
                    data['readings'] = readings
                    data['radius'] = full_radii
                    avg_step = round(sum(radii) / len(radii), 6)
                    data['radius_step'] = avg_step
                raw_scans[f'{cell}_{scan}'] = data
    return raw_scans

def export_packages_mwrs(raw_data, output_dir, cells, packages):
    """Export the packages to mwrs files"""
    packs = []
    for pair in packages:
        [lower, upper] = pair
        packs.append([x for x in range(int(lower), int(upper)+1)])
    # iterate over packages
    # create a new package
    # iterate over cells
    for cell in cells:
        # create a new cell
        for i in packs:
            wave = min(i)
            for x in i:
                if f'{cell}_{x}' not in raw_data:
                    raise Exception(f'Cell {cell} scan {x} not found in raw data')
                scan = raw_data[f'{cell}_{x}']
                data = write_mwrs(cell, scan['channel'], scan['scan'], scan['speed'], scan['speed'],
                                  scan['temperature'], scan['omega2t'], scan['seconds'], scan['radius_start'],
                                  scan['radius_step'], [wave], len(scan['readings']),
                                  [scan['readings']])
                with open(Path(output_dir) / f"{scan['description']}.{cell}.A.sample.{x:03}.mwrs", 'wb') as f:
                    f.write(data)

def export_packages_auc(raw_data, output_dir, cells, packages, run_id: str = None):
    """Export the packages to auc files"""
    packs = []

    for pair in packages:
        [lower, upper] = pair
        packs.append([x for x in range(int(lower), int(upper) + 1)])
    for cell in cells:
        for i in packs:
            wave = max(i)
            scan = raw_data[f'{cell}_{i[0]}']
            c_run_id = run_id if run_id else scan['description']
            data = {'cell': cell, 'description': scan['description'],
                    'radii': scan['radius'],
                    'scanData': []}
            for x in i:
                if f'{cell}_{x}' not in raw_data:
                    raise Exception(f'Cell {cell} scan {x} not found in raw data')
                scan = raw_data[f'{cell}_{x}']
                data['scanData'].append({'temperature': scan['temperature'], 'speed': scan['speed'],
                                       'seconds': scan['seconds'], 'omega2t': scan['omega2t'],
                                       'wavelength': wave, 'radius_step': scan['radius_step'],
                                       'reading_values': scan['readings'][:-1]})
            filename = Path(output_dir) / c_run_id / f"{c_run_id}.IP.{cell}.A.{wave:04}.auc"
            if not Path(output_dir).is_dir():
                Path(output_dir).mkdir()
            if not (Path(output_dir) / c_run_id).is_dir():
                (Path(output_dir) / c_run_id).mkdir()
            write_auc(str(filename), data)



def main(directory, scan_pairs, scans_per_package):
    # Your processing logic goes here
    run_id = Path(directory).stem
    scan_counts = count_scans(directory)
    if not scan_pairs or len(scan_pairs) == 0:
        # generate scan pairs from scans per package
        scan_pairs = []
        max_scans = max(scan_counts.values())
        for i in range(1, max_scans, scans_per_package):
            if i + scans_per_package > max_scans:
                scan_pairs.append([i-(i+scans_per_package-max_scans), max_scans])
            else:
                scan_pairs.append([i, i + scans_per_package - 1])

    print(scan_pairs)
    scans_to_read = generate_scans_to_read(scan_pairs)
    max_scan = max(scans_to_read)
    for cell, scan_count in scan_counts.items():
        if scan_count < max_scan:
            raise Exception(f'Cell {cell} has only {scan_count} scans, skipping')
    raw_data = read_scans(directory, scans_to_read, scan_counts.keys())
    output_dir = Path(directory) / 'auc'
    export_packages_auc(raw_data, str(output_dir), scan_counts.keys(), scan_pairs, run_id)





if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some raw data.')
    parser.add_argument('directory', type=str, help='Input directory with raw data')
    parser.add_argument('-scan_pairs', type=str, nargs='+', help='Pairs of numbers', required=False)
    parser.add_argument('-spp', type=int, help='Scans per package', required=False)

    args = parser.parse_args()
    if args.scan_pairs is None and args.spp is None:
        raise Exception('Either Scan pairs or scans per package is required')
    if args.scan_pairs:
        # parse string pair into tuple of integers
        scan_pairs = [tuple(map(int, pair.split(','))) for pair in args.scan_pairs]
    else:
        scan_pairs = []

    main(args.directory, scan_pairs, args.spp)