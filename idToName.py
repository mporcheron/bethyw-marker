#!/usr/local/bin/python3

import re
import os
import pandas as pd
import shutil

canvas_file = "./_marks/canvas.csv"
dir_feedback = "./_marks/"
dir_feedback_for_canvas = "./_marks_final/"

df = pd.read_csv(canvas_file)
df = df.set_index('SIS Login ID')

id_pattern = re.compile(r'([0-9]+)-feedback.txt')

for filename in os.listdir(dir_feedback):
  if filename.endswith("-feedback.txt"):
    print(os.path.join(dir_feedback, filename))
    results = re.match(id_pattern, filename)
    if results:
      student_id = results.group(1)
      student_name = df.loc[student_id]['Student']
      shutil.copyfile(os.path.join(dir_feedback, filename),
                      os.path.join(dir_feedback_for_canvas, student_name + ".txt"))
  else:
    continue