# us3utils
Utils scripts UltraScan III 4.0

### requirements
pyhton 3.9.5
pandas ~ 1.3.4
mysql-connector-python==8.0.24

## fetch_model_xmls.py
Utils program for fetching model xmls for a given search string from the database. Useable directly from the commandline, but supports also input.
Necessary input values: GUID of the person, passwort of the person, ID of the person and search string.
```bash
python fetch_model_xmls.py GUID passwort ID search_string
```
Before using the database connection values have to be changed!

## merge_model_xmls.py
Utils program for merging multiple model xmls in a given directory and creating a new model xml. Useable directly from the commandline, but supports also input.
Necessary input values: directory
```bash
python merge_model_xmls.py
```
