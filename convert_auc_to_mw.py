import argparse
import collections
import pathlib
import re
import sys
from pathlib import Path
import struct


from read_auc import read_auc
from write_auc import write_auc
from write_mw import write_mw
from write_mwrs import write_mwrs
DIR = pathlib.Path(r"PATH")
FILEPATTERN = re.compile(r"(?P<runID>[A-Za-z0-9-_]*)\.(?P<optic>[A-Z]*)\.(?P<cell>[0-9])\.(?P<channel>[A-Z])\.(?P<wavelength>[0-9]+)\.auc")
# Step 1: Find all .auc files and extract metadata
auc_files = list(DIR.glob("*.auc"))

# Dictionary to store processed data grouped by runID, cell, channel
grouped_data = {}

print(f"Found {len(auc_files)} .auc files")
counter = 0
for file_path in auc_files:
    filename = file_path.name
    
    # Extract metadata from filename
    match = FILEPATTERN.match(filename)
    if not match:
        print(f"Skipping file {filename} - doesn't match pattern")
        continue
    
    runID = match.group('runID')
    optic = match.group('optic')
    cell = match.group('cell')
    channel = match.group('channel')
    wavelength = int(match.group('wavelength'))
    data = read_auc(str(file_path))
    if not grouped_data.get(runID):
        grouped_data[runID] = {}
    if not grouped_data[runID].get(cell):
        grouped_data[runID][cell] = {}
    if not grouped_data[runID][cell].get(channel):
        grouped_data[runID][cell][channel] = {}
    grouped_data[runID][cell][channel][wavelength] = data

for runID, cells in grouped_data.items():
    for cell, channels in cells.items():
        for channel, wavelengths in channels.items():
            scans = {}
            min_radius = 0.0
            max_radius = 0.0
            delta_r = 0.0
            counter = 0
            for wavelength, data in wavelengths.items():
                min_radius += data['min_radius']
                delta_r += data['delta_radius']
                max_radius += data['radius'][-1]
                counter += 1
                for x, scan in enumerate(data['scanData']):
                    if not scans.get(x):
                        scans[x] = []
                    scans[x].append(scan)
            delta_r /= counter
            min_radius /= counter
            max_radius /= counter
            for x, scan in scans.items():
                temperature = 0.0
                omega2t = 0.0
                rpm = 0.0
                seconds = 0.0
                delta_radius = 0.0
                wavels = []
                readings = []
                reading_count = 0
                for s in scan:
                    wavels.append(int(s['wavelength']))
                    temperature += s['temperature']
                    omega2t += s['omega2t']
                    seconds += s['seconds']
                    rpm += s['rpm']
                    delta_radius += s['delta_r']
                    readings.append(s['reading_values'])
                    reading_count += len(s['reading_values'])
                temperature /= len(scan)
                omega2t /= len(scan)
                seconds /= len(scan)
                rpm /= len(scan)
                delta_radius /= len(scan)
                reading_count /= len(scan)
                data = write_mw(1234,
                                1711494000,11060,
                                int(cell),
                                channel,
                                x+1,
                                wavelengths[wavelength]['description'],
                                int(round(rpm)), temperature,
                                omega2t,
                                int(round(seconds)), int(reading_count), min_radius*10.0,
                                max_radius*10.0, wavels, readings)
                with open(DIR / f"{channel}{x+1:03}.MW{cell}", 'wb') as f:
                    f.write(data)
