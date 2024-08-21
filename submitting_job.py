# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aiohttp",
#     "asyncio",
#     "python-dotenv",
# ]
# ///
import aiohttp
import argparse
import asyncio
import re
import os
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv('WEBSITE_URL')
creds = {
    'email'   : os.getenv('USER_EMAIL'),
    'password': os.getenv('USER_PASSWORD'),
    'Submit'  : 'Sign In',
}
# experiment ids, get it either from the database (table experiment/rawdata runID) or by inspecting
# https://ultrascan.chemie.uni-konstanz.de/uslims3_UKN//queue_setup_1.php and looking at the form to select experiments
experiment_ids = []  # list of integers for example [344]
# or if you are lazy, you can specify a list of strings to search for in the experiment name
search_experiment_ids = []  # list of strings for example ['43_v1']

# list of strings to cell rawDataID:filename with filename being RunID.Optic.Cell.Channel.Wavelength.auc
# Optic can be RA, IP, RI, FI, WA, WI
# Channel can be A, B
cells = []  # list of strings for example ['67989:43_v1.RI.1.A.520.auc']
# or if you are lazy, you can specify a list of strings to search for in the cell name
search_cells = []  # list of strings for example ['1.A.520']

# job parameters
s_min = 1
s_max = 10
s_grid_points = 64
ff0_min = 1.0
ff0_max = 4.0
ff0_grid_points = 64
mc_iterations = 1
tinoise = 0  # Fit time invariant noise 0 = no, 1 = yes
rinoise = 0  # Fit radially invariant noise 0 = no, 1 = yes
fit_mb = 0  # Fit meniscus and/or bottom: 0 = no, 1 = meniscus, 2 = bottom, 3 = both
meniscus_range = 0.03  # meniscus and bottom range
meniscus_points = 1  # meniscus and bottom points in the range
iterations_option = 0  # enable iterative method 0 = no, 1 = yes
max_iterations = 10  # set max iterations
debug_level = 0  # set debug level
debug_text = ''  # debug text
simpoints = 200  # set simulation points
band_volume = 0.015  # set band volume in mL
radial_grid = 0  # Radial grid 0 = ASTFEM /default), 1 = Claverie, 2 = Moving Hat, 3 = ASTFVM(not public yet)
time_grid = 0  # Time grid 0 = adaptive space time (default), 1 = Constant
cluster = os.getenv('CLUSTER_NODE')  # cluster node to use

cell_search_regex = re.compile(r"\d+:[\w\W]+?\.(?:RI|RA|IP|FI|WA|WI)\.\d+\.[AB]\.\d+\.auc")


# create command line interface, default to values specified above


async def main(parameters: dict = None,
               experiment_ids: list = None,
               cells: list = None,
               search_experiment_ids: list = None,
               search_cells: list = None):
    async with aiohttp.ClientSession(headers={'Connection': 'keep-alive'}) as session:
        # load login page
        cookies = {}
        async with session.get(f"{base_url}login.php") as response:
            cookies['PHPSESS_uslims3_UKN'] = response.cookies.get('PHPSESS_uslims3_UKN')
            cookies['path'] = response.cookies.get('path')
            # update session cookies
            session.cookie_jar.update_cookies(response.cookies)
        # login
        login_form_data = aiohttp.FormData(creds)
        async with session.post(f"{base_url}checkuser.php", data=login_form_data) as response:
            if response.status != 200:
                print(await response.text())
                print("Login failed")
                pass
        # initial queue page
        queue_setup_1 = aiohttp.FormData()
        queue_setup_1.add_field('submitter_email', creds['email'])
        if not experiment_ids:  # no experiment_ids, get them from the website
            async with session.get(f"{base_url}queue_setup_1.php") as response:
                if response.status != 200:
                    print(await response.text())
                    print("Failed to get experiment ids")
                    pass
                # parse experiment ids from the page
                site_content = await response.text()
                # parse experiment ids from the page with regex
                # example: <option value="344">2021-06-24 43_v1</option>
                items = re.findall(r"<option value='(\d+)'>\d\d\d\d-\d\d-\d\d ([\w\W]*?)</option>",
                                   site_content)
                for item in items:
                    for search_id in search_experiment_ids:
                        if str(search_id) in item[1]:
                            experiment_ids.append(item[0])
        if not experiment_ids:
            print("No experiment ids found")
            return
        for exp_id in experiment_ids:
            queue_setup_1.add_field('expIDs[]', exp_id)
        async with session.post(f"{base_url}queue_setup_1.php",
                                data=queue_setup_1) as response:
            if search_cells:
                site_content = await response.text()
                parsed_cells = cell_search_regex.findall(site_content)
                for parsed_cells in parsed_cells:
                    for search_cell in search_cells:
                        if search_cell in parsed_cells:
                            cells.append(parsed_cells)
            
            if response.status != 200:
                print(await response.text())
                print("Failed to setup queue")
                pass
        if not cells:
            print("No cells found")
            return
        # select triples
        for cell in cells:
            queue_setup_1.add_field('cells[]', cell)
        queue_setup_1.add_field('next', 'Add to Queue')
        async with session.post(f"{base_url}queue_setup_1.php",
                                data=queue_setup_1) as response:
            if response.status != 200:
                print(await response.text())
                print("Failed to add to queue")
                pass
        # use latest noise and edits
        queue_setup_2 = aiohttp.FormData()
        queue_setup_2.add_field('edit_select_type', 'autoedits')
        queue_setup_2.add_field('save', 'Save Queue Information')
        async with session.post(f"{base_url}queue_setup_2.php",
                                data=queue_setup_2) as response:
            if response.status != 200:
                print(await response.text())
                print("Failed to set edit and noise select")
                pass
        
        # start job
        job_parameters = aiohttp.FormData()
        for k, v in parameters.items():
            job_parameters.add_field(k, v)
        async with session.post(f"{base_url}2DSA_1.php",
                                data=job_parameters) as response:
            print(await response.text())
            if response.status != 302:
                print("Failed to start job")
                pass


if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Submit jobs to ultrascan')
    parser.add_argument('--experiment_ids',
                        metavar='ExpID',
                        type=int,
                        nargs='+',
                        default=experiment_ids,
                        required=False,
                        help='List of experiment ids to submit jobs for')
    parser.add_argument('--search_experiment_ids',
                        metavar='ExpSearchStr',
                        type=str,
                        nargs='+',
                        default=search_experiment_ids,
                        required=False,
                        help='List of strings to search for in the experiment name')
    parser.add_argument('--cells',
                        metavar='Cell',
                        type=str,
                        nargs='+',
                        default=cells,
                        required=False,
                        help='List of cell ids to submit jobs for')
    parser.add_argument('--search_cells',
                        metavar='CellSearchStr',
                        type=str,
                        nargs='+',
                        default=search_cells,
                        required=False,
                        help='List of strings to search for in the cell name')
    parser.add_argument('--s_min',
                        metavar='sMin',
                        type=int,
                        default=s_min,
                        required=False,
                        help='integer for s min (default: 1)')
    parser.add_argument('--s_max',
                        metavar='sMax',
                        type=int,
                        default=s_max,
                        required=False,
                        help='integer for s max (default: 10)')
    parser.add_argument('--s_grid_points',
                        metavar='sGP',
                        type=int,
                        default=s_grid_points,
                        required=False,
                        help='integer for s grid points (default: 64)')
    parser.add_argument('--ff0_min',
                        metavar='yMin',
                        type=float,
                        default=ff0_min,
                        required=False,
                        help='float for ff0 min (default: 1.0)')
    parser.add_argument('--ff0_max',
                        metavar='yMax',
                        type=float,
                        default=ff0_max,
                        required=False,
                        help='float for ff0 max (default: 4.0)')
    parser.add_argument('--ff0_grid_points',
                        metavar='yGP',
                        type=int,
                        default=ff0_grid_points,
                        required=False,
                        help='integer for ff0 grid points (default: 64)')
    parser.add_argument('--mc_iterations',
                        metavar='MC',
                        type=int,
                        default=mc_iterations,
                        required=False,
                        help='integer for monte carlo iterations (default: 1)')
    parser.add_argument('--tinoise',
                        metavar='TI',
                        type=int,
                        default=tinoise,
                        required=False,
                        help='Fit time invariant noise 0 = no, 1 = yes (default: 0)')
    parser.add_argument('--rinoise',
                        metavar='RI',
                        type=int,
                        default=rinoise,
                        required=False,
                        help='Fit radially invariant noise 0 = no, 1 = yes (default: 0)')
    parser.add_argument('--fit_mb',
                        metavar='FitMB',
                        type=int,
                        default=fit_mb,
                        required=False,
                        help='Fit meniscus and/or bottom: 0 = no, 1 = meniscus, 2 = bottom, 3 = both (default: 0)')
    parser.add_argument('--meniscus_range',
                        metavar='MenRange',
                        type=float,
                        default=meniscus_range,
                        required=False,
                        help='float for meniscus and bottom range (default: 0.03)')
    parser.add_argument('--meniscus_points',
                        metavar='MenP',
                        type=int,
                        default=meniscus_points,
                        required=False,
                        help='meniscus and bottom points in the range (default: 1)')
    parser.add_argument('--iterations_option',
                        metavar='IT',
                        type=int,
                        default=iterations_option,
                        required=False,
                        help='enable iterative method 0 = no, 1 = yes (default: 0)')
    parser.add_argument('--max_iterations',
                        metavar='MaxIT',
                        type=int,
                        default=max_iterations,
                        required=False,
                        help='integer limiting iterations (default: 10)')
    parser.add_argument('--debug_level',
                        metavar='DbgLv',
                        type=int,
                        default=debug_level,
                        required=False,
                        help='integer for debug level (default: 0)')
    parser.add_argument('--debug_text',
                        metavar='DbgTxt',
                        type=str,
                        default=debug_text,
                        required=False,
                        help='debug text (default: "")')
    parser.add_argument('--simpoints',
                        metavar='SP',
                        type=int,
                        default=simpoints,
                        required=False,
                        help='set simulation points (default: 200)')
    parser.add_argument('--band_volume',
                        metavar='BV',
                        type=float,
                        default=band_volume,
                        required=False,
                        help='float for band volume in mL (default: 0.015)')
    parser.add_argument('--radial_grid',
                        metavar='RG',
                        type=int,
                        default=radial_grid,
                        required=False,
                        help='Radial grid 0 = ASTFEM, 1 = Claverie, 2 = Moving Hat (default: 0)')
    parser.add_argument('--time_grid',
                        metavar='TG',
                        type=int,
                        default=time_grid,
                        required=False,
                        help='integer for time grid 0 = adaptive space time, 1 = Constant (default: 1)')
    parser.add_argument('--cluster',
                        metavar='c',
                        type=str,
                        default=cluster,
                        required=False,
                        help='cluster node to use (default: ultrascan.chemie.uni-konstanz.de:us3iab-node0:batch)')
    args = parser.parse_args()
    parameters = vars(args)
    job_parameters = {k: v for k, v in parameters.items() if
                      k not in ['experiment_ids', 'cells', 'search_experiment_ids', 'search_cells']}
    # map parameters to job_parameters
    job_parameters['tinoise_option'] = parameters['tinoise']
    job_parameters['rinoise_option'] = parameters['rinoise']
    job_parameters['fit_mb_select'] = parameters['fit_mb']
    if parameters['fit_mb'] == 0:
        job_parameters['meniscus_range'] = 0.0
        job_parameters['meniscus_points'] = 1
    job_parameters['cluster'] = parameters['clusternode']
    job_parameters['s_value_min'] = parameters['s_min']
    job_parameters['s_value_max'] = parameters['s_max']
    job_parameters['mc_iterations'] = parameters['mc_iterations']
    if parameters['iterations_option'] == 0:
        job_parameters['max_iterations'] = 1
    job_parameters['debug_level-value'] = parameters['debug_level']
    job_parameters['debug_text-value'] = parameters['debug_text']
    job_parameters['simpoints-value'] = parameters['simpoints']
    job_parameters['band_volume-value'] = parameters['band_volume']
    job_parameters['req_mgroupcount'] = 1  # number of groups
    job_parameters['uniform_grid'] = 8  # uniform grid repitions
    job_parameters['debug_timings'] = 1  # debug timings
    
    asyncio.run(main(job_parameters,
                     experiment_ids=args.experiment_ids,
                     cells=args.cells,
                     search_experiment_ids=args.search_experiment_ids,
                     search_cells=args.search_cells))
