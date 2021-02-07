import pandas as pd

key = "1m.a.w.porcheron@Swansea.ac.uk"

df = pd.read_csv('_marks/autograder.csv')
df = df.set_index('Username')

try:
  autograder_marks = df.loc[key]
  print(autograder_marks['Total Points'])
except KeyError:
  print('nope')