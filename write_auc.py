import struct


def write_auc(filename: str, data: dict):
	with open(filename, 'wb') as f:
		f.write('UCDA'.encode('utf-8'))
		f.write('05'.encode('utf-8'))
		f.write('IP'.encode('utf-8'))
		f.write(struct.pack('<B', data['cell']))
		f.write('A'.encode())
		f.write(bytes(16))  # rawGUID UltraScan internal, not used
		description = data['description'].encode() + b'\x00' * (240 - len(data['description']))
		f.write(description)
		min_radius = min(data['radii'])
		delta_radius = sum([scan['radius_step'] for scan in data['scanData']])/len(data['scanData'])
		f.write(struct.pack('<f', min(data['radii'])))
		f.write(struct.pack('<f', 0))  # unused data
		f.write(struct.pack('<f', sum([scan['radius_step'] for scan in data['scanData']])/len(data['scanData'])))
		min_data = min([min(scan['reading_values']) for scan in data['scanData']])
		max_data = max([max(scan['reading_values']) for scan in data['scanData']])
		f.write(struct.pack('<f', min_data))
		f.write(struct.pack('<f', max_data))
		f.write(struct.pack('<f', 0.0))
		f.write(struct.pack('<f', 0.0))
		f.write(struct.pack('<h', len(data['scanData'])))

		for scan in data['scanData']:
			f.write('DATA'.encode())
			f.write(struct.pack('<f', scan['temperature']))
			f.write(struct.pack('<f', scan['speed']))
			f.write(struct.pack('<i', scan['seconds']))
			f.write(struct.pack('<f', scan['omega2t']))
			f.write(struct.pack('<h', scan['wavelength'] * 10))
			f.write(struct.pack('<f', scan['radius_step']))
			f.write(struct.pack('<i', len(scan['reading_values'])))

			reading_values = scan['reading_values']

			factor1 = (max_data - min_data) / 65535.0

			for i in reading_values:
				bval = round((i - min_data) / factor1)
				f.write(struct.pack('<H', bval))

			interpolated = [0] * ((len(reading_values) + 7) // 8)
			byte_arr = bytes(bytearray(interpolated))
			f.write(byte_arr)