
import json
import os
import pandas as pd
import sys
import webbrowser as wb

this_dir = os.path.dirname(os.path.abspath(__file__)) + "/"

with open(this_dir + 'popu1009.json') as data_file:    
    data = json.load(data_file)

df = pd.json_normalize(data, 'value', [])
df = df.sort_values(by=['Localauthority_Code', 'Measure_Code', 'Year_Code'])

for col, row in df.iterrows():
    print('REQUIRE( areas.getArea("' + str(row['Localauthority_Code']) + '").getMeasure("' + str(row['Measure_Code']) + '").getValue("' + str(row['Year_Code']) + '") == ' + str(row['Data']) + ' );')

# https://canvas.swansea.ac.uk/api/v1/groups/17533/users?per_page=300&include%5B%5D=sections&include%5B%5D=group_submissions&include%5B%5D=active_status&exclude%5B%5D=pseudonym