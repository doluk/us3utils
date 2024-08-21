# us3utils
Utils scripts UltraScan III 4.0


#### installation guide
1. Open a terminal window (windows and search for `cmd`)
2. Install uv following the [documentation](https://docs.astral.sh/uv/getting-started/installation/) with `curl 
-LsSf https://astral.sh/uv/install.sh | sh` on macOS/Linux or `powershell -c "irm https://astral.sh/uv/install.ps1 | 
iex"` on Windows. `uv` is an awesome tool for running python scripts and handles all dependencies for you, including 
   python itself.
3. Download the code by clicking [here](https://github.com/doluk/us3utils/archive/refs/heads/main.zip) or executing 
   `git clone https://github.com/doluk/us3utils` if you have git installed
4. Extract the files to a directory of your choice (doesn't matter) in case you didn't use the terminal command
5. Clone the .env.example file and rename it to .env. Afterwards fill it with your information.

#### user guide
After you navigated to the directory containing the scripts, you can use them in three ways:
- Double-clicking on them and entering needed values one after another
- Execute the scripts via commandline with `uv run script_name` without further arguments, which results in entering 
them one after another
- Execute the scripts via commandline with `uv run script_name arg1 arg2` specifying the needed arguments all by one

## fetch_model_xmls.py
Utils program for fetching model xmls for a given search string from the database. Usable directly from the 
commandline, but supports also input.
Necessary input values, if you haven't setup the .env file: GUID of the person, password of the person, ID of the 
person and search string.
```bash
uv run fetch_model_xmls.py [GUID] [passwort] [ID] search_string
```

Before using the database connection values have to be changed!

## merge_model_xmls.py

Utils program for merging multiple model xmls in a given directory and creating a new model xml. Usable directly from
the commandline, but supports also input. Necessary input values: directory

```bash
uv run merge_model_xmls.py directory
```

## generate_3Dmodelmesh.py

Utils program for generating point-meshes for plotting the model data. Be careful without specified dimensions the
program generates 18 meshes, which could take some time. Usable directly from the commandline, but supports also input.

Necessary input values: modelfile_location experimental_temperature experimental_viscosity experimental_density

Optional input values: dimension1 dimension2

```bash
uv run generate_3Dmodelmesh.py modelfilelocation temperature viscosity density [dimension1] [dimension2]
```

## calc_core_shell.py

Utils program for calculating the core-shell model properties according Carney et al. and Gonzalez-Rubio et al. based on
a folder containing the statistics files of the ultrascan tool "Initialize Generic Algorithm". Usable directly from the
commandline, but supports also input. Necessary input values: directory

```bash
uv run calc_core_shell.py
```

