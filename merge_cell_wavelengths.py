# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
# ]
# ///
import os
import shutil
import re

from merge_model_xmls import merge_models

# Ask for directory input
dir_input = input('Enter the directory path: ')

# Get all filenames in the directory
filenames = os.listdir(dir_input)

# Create a dictionary to store unique substrings and their associated filenames
substring_dict = {}

# Find the part of the filename encapsulated by #
for filename in filenames:
    match = re.search(r'#[0-9][A-Z](.*?)#', filename)
    if match:
        substring = match.group(1)
        if substring in substring_dict:
            substring_dict[substring].append(filename)
        else:
            substring_dict[substring] = [filename]

# For each unique substring, create a new directory and copy associated files
for substring, files in substring_dict.items():
    new_dir = os.path.join(dir_input, substring)
    os.makedirs(new_dir, exist_ok=True)
    for file in files:
        shutil.copy(os.path.join(dir_input, file), new_dir)
    os.makedirs(os.path.join(dir_input, 'result'), exist_ok=True)
    merge_models(new_dir, file_save = os.path.join(dir_input, 'result', f'{dir_input}.1A{substring}.xml'))