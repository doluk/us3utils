import struct
from typing import Sequence


def write_mw(
    magic_number: int,
    date_time_ubit48: int,
    version_number: int,
    cell: int,
    channel: str,
    scan: int,
    sample: str,
    speed: int,
    temperature_c: float,
    w2t: float,
    seconds: int,
    radius_count: int,
    radius_start: float,
    radius_end: float,
    lambdas: Sequence[int],
    intensity_matrix: Sequence[Sequence[int]],
) -> bytes:
    """
    Write an .mw file payload (big-endian) matching the provided MATLAB reader.

    Parameters:
    - magic_number: uint32
    - date_time_ubit48: 48-bit unsigned int (pack into 6 bytes big-endian)
    - version_number: uint16
    - cell: uint8
    - channel: single ASCII char
    - scan: uint16
    - sample: bytes of length <= 64 (will be right-padded with zeros to 64)
    - speed: uint16
    - temperature_c: float degrees C (will be stored as uint16 of tenths)
    - w2t_ms: uint32 milliseconds (MATLAB multiplies by 1000 when reading)
    - seconds: uint32
    - radius_count: uint16
    - radius_start_mm: float (will be stored as uint16 of mm*1000)
    - radius_end_mm: float (will be stored as uint16 of mm*1000)
    - lambdas_tenths_nm: iterable of uint16 values (wavelengths in 0.1 nm)
    - intensity_matrix: 2D iterable radius_count x lambda_count of unsigned ints,
                        written with element type matching MATLAB fread '*uint' (use 32-bit here)

    Returns:
        bytes suitable to write to an .mw file.
    """

    # Header
    # uint32 magic
    bin_data = struct.pack(">I", magic_number)

    # 48-bit date/time as 6 big-endian bytes
    if not (0 <= date_time_ubit48 < (1 << 48)):
        raise ValueError("date_time_ubit48 must be a 48-bit unsigned integer")
    bin_data += date_time_ubit48.to_bytes(6, byteorder="big", signed=False)

    # uint16 version
    bin_data += struct.pack(">H", version_number)

    # uint8 cell
    bin_data += struct.pack(">B", cell)

    # 1-char channel
    if len(channel) != 1:
        raise ValueError("channel must be a single character")
    bin_data += channel.encode("ASCII")

    # uint16 scan
    bin_data += struct.pack(">H", scan)

    # 64-char sample (pad/truncate)
    if len(sample) > 64:
        sample = sample[:64]
    sample_code = sample.encode() + b'\x00' * (64 - len(sample))
    bin_data += sample_code

    # uint16 speed
    bin_data += struct.pack(">H", int(round(speed)))

    # uint16 temperature in tenths C
    bin_data += struct.pack(">H", int(round(temperature_c * 10)))

    # uint32 w2t (milliseconds as given; MATLAB multiplies by 1000 on read)
    bin_data += struct.pack(">I", int(round(w2t / 1000.0)))

    # uint32 seconds
    bin_data += struct.pack(">I", int(round(seconds)))

    # uint16 radiusCount
    bin_data += struct.pack(">H", radius_count)

    # uint16 radiusStart in micrometers (mm * 1000)
    bin_data += struct.pack(">H", int(round(radius_start * 100.0)))

    # uint16 radiusEnd in micrometers (mm * 1000)
    bin_data += struct.pack(">H", int(round(radius_end * 100.0)))

    # uint16 lambdaCount
    lambda_count = len(lambdas)
    bin_data += struct.pack(">H", lambda_count)

    # lambda array uint16 each (tenths of nm)
    for lamb in lambdas:
        bin_data += struct.pack(">H", int(round(lamb * 10.0)))

    # After header + lambdas, MATLAB seeks to byte offset:
    # start_byte = 100 + lambdaCount*2
    # Ensure our header length matches 100 bytes before lambdas:
    # 4 (magic) + 6 (date) + 2 (ver) + 1 (cell) + 1 (channel) + 2 (scan) +
    # 64 (sample) + 2 (speed) + 2 (temp) + 4 (w2t) + 4 (seconds) +
    # 2 (radiusCount) + 2 (radiusStart) + 2 (radiusEnd) + 2 (lambdaCount) = 98
    # Note: The MATLAB code's offset implies 100 bytes before lambdas.
    # To align, we add 2 bytes of reserved/padding to reach 100.
    # This matches the seek to 100 + lambdaCount*2 for intensity.
    # If your real format already accounts for 100, remove this padding.
    if len(bin_data) == 98 + lambda_count * 2:
        bin_data += b"\x00\x00"
    elif len(bin_data) != 100 + lambda_count * 2:
        raise ValueError(f"Unexpected header size {len(bin_data)} bytes; expected 100 before lambdas segment.")

    # At this point we have 100 bytes + 2*lambda_count bytes written.

    # Intensity matrix: MATLAB used fread(..., '*uint') which defaults to uint32 here.
    # Write as big-endian uint32 in row-major [radiusCount, lambdaCount]
    if len(intensity_matrix) != lambda_count:
        raise ValueError("intensity_matrix row count must equal radius_count")
    for row in intensity_matrix:
        if len(row) != radius_count:
            raise ValueError("each intensity row length must equal lambda_count")
        for val in row:
            val = max(val, 0.0)
            # Ensure non-negative and fit into uint32
            if val < 0 or val > 0xFFFFFFFF:
                raise ValueError("intensity values must be in range 0..2^32-1")
            bin_data += struct.pack(">I", int(val))

    return bin_data
