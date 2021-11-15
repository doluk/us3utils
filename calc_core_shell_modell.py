import pandas as pd
import os
import sys
import re
import math
attributes = ['Name','MW','s','D','ff0',
              'vbar','c_p']
lm_viscosity = 0.00891 * 0.1 # H2O Viskosity fix in kg/m/s
lm_density = 0.99704 * 1000 # H2O Density fix in kg/m^3
lig_density = 1.03 * 1000 # Ligand Density in kg/m^3
c_density = 4.82 * 1000 # core density in kg/m^3
lig_MW = 6.2 # MW lig in kDa
c_MW = 0.14446 # MW core in kDa
temp = 293.15 # temperatur fix
kb = 1.3806e-23 # boltzmann konstante
R = 8.314 # gas konstante
Na = 6.022e23 # avogadro zahl
package_factor = 0.34
# TODO Request non fixed values
if len(sys.argv) != 2:
    dir_input = input('Enter path to directory which should be read:')
else:
    dir_input = sys.argv[1]
    sys.environ
dir = os.path.dirname(__file__)
dirname = os.path.join(dir, dir_input)
dfs = []
header = ''
max_var = 0
print(f'{len(os.listdir(dirname))} files found, start reading')
for filename in os.listdir(dirname):
    with open(os.path.join(dirname,filename),'r',encoding='utf8') as file:
        text = file.read()
    solutes = text.split('Detailed Results')[0]
    numbers = re.findall(r'.+\:\s+([\d\.e+-]+)(?:\s\(.*\))?\n',solutes)
    numbers = [float(i) for i in numbers]
    data = [[filename] + numbers[i:i+6] for i in range(0,len(numbers),6)]
    dfs.append(pd.DataFrame(data,columns=attributes))
print('finished reading')
df = pd.concat(dfs,axis=0)
df['D'] *= 1e-4 # D unit from cm^2/s to m^2/s
# Carney
df['rho_p Carney'] = lm_density + 18*lm_viscosity*df['s'] * (kb*temp/3/math.pi/lm_viscosity/df['D'])**(-2)
df['dh Carney']=(18*lm_viscosity*df.s/(df['rho_p Carney']-lm_density))**0.5
df['d core Carney'] = df['dh Carney']*((df['rho_p Carney']-lig_density)/(c_density-lig_density))**(1/3)
df['MW_p Carney'] = df.s/df.D*R*temp/(1-lm_density/df['rho_p Carney'])
df['N_core Carney'] = df['MW_p Carney']/c_MW*(1/lig_density-1/df['rho_p Carney'])/(1/lig_density-1/c_density)
df['N_lig Carney'] = df['MW_p Carney']/lig_MW*(1/df['rho_p Carney']-1/c_density)/(1/lig_density-1/c_density)
df['N Cd Carney'] = -5967758160085733649901550489*package_factor*df['d core Carney']**3 +9.29404333232168*df['N_core Carney']*c_MW
df['N S Carney'] = 20887153560300067774655426711*package_factor*df['d core Carney']**3 - 1.279151663125876*df[
    'N_core Carney']*c_MW
# Gonzalez-Rubio
df['MW_c Gonzalez'] = df.s/df.D*R*temp/(1-lm_density/c_density)
df['d core Gonzalez'] = 2 * (3*df['MW_c Gonzalez']/Na/c_density/4/math.pi)**(1/3)
df['dh Gonzalez'] = kb*temp/3/math.pi/lm_viscosity/df.D
df['rho_p Gonzalez'] = df['d core Gonzalez']**3/df['dh Gonzalez']**3*(c_density-lig_density)+lig_density
df['MW_p Gonzalez'] = df.s/df.D*R*temp/(1-lm_density/df['rho_p Gonzalez'])
df['N_core Gonzalez'] = df['MW_p Gonzalez']/c_MW*(1/lig_density-1/df['rho_p Gonzalez'])/(1/lig_density-1/c_density)
df['N_lig Gonzalez'] = df['MW_p Gonzalez']/lig_MW*(1/df['rho_p Gonzalez']-1/c_density)/(1/lig_density-1/c_density)
df['N Cd Gonzalez'] = -5967758160085733649901550489*package_factor*df['d core Gonzalez']**3 +\
                      9.29404333232168*df['MW_c Gonzalez']
df['N S Gonzalez'] = 20887153560300067774655426711*package_factor*df['d core Gonzalez']**3 - \
                     1.279151663125876*df['MW_c Gonzalez']
df.sort_values(['Name','s','D']).reset_index()
df.to_csv(str(os.path.join(dirname,dir_input+'-core_shell.csv')),index=False)


