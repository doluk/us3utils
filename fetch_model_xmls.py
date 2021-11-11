import sys
import os

###############################################################################
# Imports
###############################################################################

from typing import Union
import mysql.connector


###############################################################################
# Constants
###############################################################################

DB_HOST = 'XXXXXXXXXXXXXXXXXXX'
DB_NAME = 'XXXXXXXXXXXXXXXXXXX'
DB_USR = 'XXXXXXXXXXXXXXXXXXX'
DB_PWD = 'XXXXXXXXXXXXXXXXXXX'


###############################################################################
# Classes
###############################################################################

class NotFoundException(Exception):
    '''class to signal empty responses from the database or google sheets
    '''

    def __init__(self, reason=None):
        self.reason = reason


class DBHandler:
    """class to handle database related tasks
    Methods
    -------
        create_connection
            create and return a connector to the database
        execute_sql
            execute an arbitrary SQL statement
    """

    def __init__(self):
        self.db_host = DB_HOST
        self.db_name = DB_NAME
        self.db_usr = DB_USR
        self.db_pwd = DB_PWD

    def create_connection(self):
        """
        create and return a connector to the database
        Returns
        -------
            the connector
        """
        # Use detect_types to receive parsed datetime objects
        conn = mysql.connector.connect(host=self.db_host, database=self.db_name, user=self.db_usr, password=self.db_pwd)

        return conn

    def call_proc(self,query,values,conn=None,close=True):
        res = None
        try:
            if not conn:
                conn = self.create_connection()
            c = conn.cursor()
            c.callproc(query,values)
            res = [r.fetchall() for r in c.stored_results()]
            if len(res) < 2:
                c.callproc(query,values)
                res = [r.fetchall() for r in c.stored_results()]
            if close:
                conn.close()
            return res
        except Exception as e:
            print(e)



###############################################################################
# Provide ready instances for importing
###############################################################################

handler = DBHandler()



def save_xml(model,p_search):
    with open(f'{p_search}/'+"#".join(model[1].split('.')[:-1])+'.xml', 'w',encoding='utf8') as f:
        f.write(model[2])
    f.close()
def fetch_model_ids(p_GUID,p_passwort,p_ID,p_search):
    # fetch all model IDs
    try:
        models = handler.call_proc("get_model_desc_by_runID",(p_GUID,p_passwort,p_ID,p_search),close=True)[1:]
    except NotFoundException:
        print(f'No models for the search input {p_search} found.')
        return
    except Exception as e:
        print(e)
        exit(1)
    ids = [m[0] for m in models[0]]
    return ids
def fetch_model_info(p_GUID,p_passwort,p_search,model_id):
    try:
        model_info = handler.call_proc("get_model_info",(p_GUID,p_passwort,model_id),
                                            close=True)[1:]
    except NotFoundException:
        print(f'No Model for model ID {model_id} found')
        exit(1)
    except Exception as e:
        print(e)
        exit(1)
    for mi in model_info[0]:
        save_xml(mi,p_search)


print("#".join(sys.argv))
if len(sys.argv) != 5:
    p_GUID = input('Enter GUID:')
    p_passwort = input('Enter passwort:')
    p_ID = input('Enter ID:')
    print('Example for a search string to fetch all data from the Run 2667 in Cell 3 Channel A at the wavelength 380 '
          'and only 2DSA-Monte Carlo Models:\n"2667.3A380%2DSA-MC"')
    p_search = input('Now you can enter your search input. It should contain at least the runID you set while '
                     'importing the data. If you want specify the Cell, Channel, Wavelength you can do this '
                     'too. Make sure you seperate the RunId from the other stuff with a dot and enter than Cell '
                     'Channel or wavelength information, percentage sign should seperate the model information '
                     'from the other stuff. If you want all Cells or all channels or all wavelengths replace the '
                     'regarding information with a percentage sign\n')
else:
    p_GUID,p_passwort,p_ID,p_search = sys.argv[1:]

model_ids = fetch_model_ids(p_GUID,p_passwort,p_ID,p_search)
if not model_ids:
    print('No models found.')
    exit(1)
try:
    dir = os.path.dirname(__file__)
    path_y = p_search.replace("/","").replace("\\","").replace(".","")
    filename = os.path.join(dir, f'{path_y}')
    os.mkdir(filename)
except Exception as e:
    print(e)
    pass
print(f'Starting exporting {len(model_ids)} xml files')
for mid in model_ids:
    fetch_model_info(p_GUID,p_passwort,filename,mid)
print('Finished')






