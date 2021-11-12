import pandas as pd
import os
import sys
import re
import math
attributes = ['Name','MW','s','D','ff0',
              'vbar','c_p']
lm_viscosity = 1.25 * 0.001 # D2O Viskosity
lm_density = 1.1056 * 1000 # D2O Density
lig_density = 1.03 * 1000 # Ligand Density
c_density = 4.82 * 1000 # core density
lig_MW = 6.2
c_MW = 0.14446
temp = 293.15 # temperatur
kb = 1.3806e-23 # boltzmann konstante
R = 8.314 # gas konstante
Na = 6.022e23 # avogadro zahl

if len(sys.argv) != 2:
    dir_input = input('Enter path to directory which should be read:')
else:
    dir_input = sys.argv[1]
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
# Carney
df['rho_p Carney'] = lm_density + 18*lm_viscosity*df['s'] * (kb*temp/3/math.pi/lm_viscosity/df['D'])**(-2)
df['dh Carney']=(18*lm_viscosity*df.s/(df['rho_p Carney']-lm_density))**0.5
df['d core Carney'] = df['dh Carney']*((df['rho_p Carney']-lig_density)/(c_density-lig_density))**(1/3)
df['MW_p Carney'] = df.s/df.D*R*temp/(1-lm_density/df['rho_p Carney'])
df['N_core Carney'] = df['MW_p Carney']/c_MW*(1/lig_density-1/df['rho_p Carney'])/(1/lig_density-1/c_density)
df['N_lig Carney'] = df['MW_p Carney']/lig_MW*(1/df['rho_p Carney']-1/c_density)/(1/lig_density-1/c_density)
# Gonzalez-Rubio
df['MW_c Gonzalez'] = df.s/df.D*R*temp/(1-lm_density/c_density)
df['d core Gonzalez'] = 2 * (3*df['MW_c Gonzalez']/Na/c_density/4/math.pi)**(1/3)
df['dh Gonzalez'] = kb*temp/3/math.pi/lm_viscosity/df.D
df['rho_p Gonzalez'] = df['d core Gonzalez']**3/df['dh Gonzalez']**3*(c_density-lig_density)+lig_density
df['MW_p Gonzalez'] = df.s/df.D*R*temp/(1-lm_density/df['rho_p Gonzalez'])
df['N_core Gonzalez'] = df['MW_p Gonzalez']/c_MW*(1/lig_density-1/df['rho_p Gonzalez'])/(1/lig_density-1/c_density)
df['N_lig Gonzalez'] = df['MW_p Gonzalez']/lig_MW*(1/df['rho_p Gonzalez']-1/c_density)/(1/lig_density-1/c_density)
df.sort_values(['Name','s','D']).reset_index()
df.to_csv(str(os.path.join(dirname,dir_input+'-core_shell.csv')),index=False)


