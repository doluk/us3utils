# us3utils
Utils scripts UltraScan III 4.0

### requirements
To set up your computer, you have to meet these requirements:
```
pyhton 3.9.5
pandas ~ 1.3.4
mysql-connector-python
lxml
numba
```
#### installation guide
1. Download and install python 3.10 (click [here](https://www.python.org/downloads/) to visit the python download page).
Make sure you add python to your path (an option during the installation)
2. Open a terminal window (windows and search for `cmd`)
3. Run the following command `pip install pandas mysql-connector-python lxml numba`
4. Download the code by clicking [here](https://github.com/doluk/us3utils/archive/refs/heads/main.zip)
5. Extract the files to a directory of your choice (doesn't matter)

#### user guide
After you navigated to the directory containing the scripts, you can use them in three ways:
- Double-clicking on them and entering needed values one after another
- Execute the scripts via commandline with `python script_name` without further arguments, which results in entering 
them one after another
- Execute the scripts via commandline with `python script_name arg1 arg2` specifying the needed arguments all by one

## fetch_model_xmls.py
Utils program for fetching model xmls for a given search string from the database. Usable directly from the 
commandline, but supports also input.
Necessary input values: GUID of the person, password of the person, ID of the person and search string.
```bash
python fetch_model_xmls.py GUID passwort ID search_string
```
Before using the database connection values have to be changed!

## merge_model_xmls.py
Utils program for merging multiple model xmls in a given directory and creating a new model xml. 
Usable directly from the commandline, but supports also input.
Necessary input values: directory
```bash
python merge_model_xmls.py
```

## calc_core_shell.py
Utils program for calculating the core-shell model properties according Carney et al. and Gonzalez-Rubio et al. 
based on a folder containing the statistics files of the ultrascan tool "Initialize Generic Algorithm". 
Usable directly from the commandline, but supports also input.
Necessary input values: directory
```bash
python calc_core_shell.py
```

