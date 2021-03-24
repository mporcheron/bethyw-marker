#!/usr/bin/env python3

import collections
import math
import os
import pandas as pd
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

student_id = sys.argv[1]
autograder_id = student_id + "@Swansea.ac.uk"



def __unittest_compile(unittest):
  cmd = ["g++",
         "--std=c++14",
         "-Wall",
         "./bethyw.cpp",
         "./input.cpp",
         "./areas.cpp",
         "./area.cpp",
         "./measure.cpp",
         "./tests/" + unittest + ".cpp",
         "../_bin/catch.o",
          "-o",
          "./bethyw-" + unittest]
  res = subprocess.run(cmd, cwd=os.getcwd() + "/_tempsrc", capture_output=True)

  if res.returncode == 0:
    return True
  else:
    return res.stderr.decode("utf-8") 

catch2_tests = {
  "testus10" : 2,
  "testus10a": 2
}
  
catch2_results = {}
failed_tests = {}

for catch2_test in iter(catch2_tests):
  catch2_results[catch2_test] = 0

for catch2_test in iter(catch2_tests):
  print("Compiling " + catch2_test)
  compile_result = __unittest_compile(catch2_test)

  if compile_result is not True:
    with open("./_marks/manualtest-" + student_id + '-catch2-' + catch2_test +'.txt', 'w') as file:
      file.write("Could not compile:\n" + compile_result)
    continue

  print("Running " + catch2_test)
  cmd = ["./bethyw-" + catch2_test, "-r", "xml"]
  res = subprocess.run(cmd, cwd=os.getcwd() + "/_tempsrc", capture_output=True)

  catch2xml  = res.stdout.decode("utf-8")
  with open("./_marks/manualtest-" + student_id + '-catch2-' + catch2_test +'.xml', 'w') as file:
    file.write(catch2xml)

  # Parse Catch2 unit tests outcomes
  try:
    root = ET.XML(catch2xml)
    for overall_result in root.iter("OverallResults"):
      if overall_result.get("failures") == "0":
        catch2_results[catch2_test] = catch2_tests[catch2_test]
      break
  except ET.ParseError:
    print("Error with " + catch2_test)




output_tests = {
  "nowarnings"      : (2, []),
  "outputus2.txt"   : (1, ["-a", "swan", "-m", "rail"]),
  "outputus2a.txt"  : (1, ["-a", "swan", "-m", "rail"]),
  "outputus5.json"  : (1, ["-a", "swan,card", "-m", "pop,rail", "-y", "2010-2018", "-j"]),
  "outputus5a.json" : (1, ["-a", "swan,card", "-m", "pop,rail", "-y", "2010-2018", "-j"]),
  "outputus6.json"  : (1, ["-a", "W06000015,W06000011", "-y", "2015", "-j"]),
  "outputus6a.json" : (1, ["-a", "W06000015,W06000011", "-y", "2015", "-j"])
}

output_results = {}

print("Compiling application")
for output_test in iter(output_tests):
  output_results[output_test] = 0

cmd = ["g++",
       "--std=c++14",
       "-Wall",
       "-pedantic",
       "./bethyw.cpp",
       "./input.cpp",
       "./areas.cpp",
       "./area.cpp",
       "./measure.cpp",
       "./main.cpp",
        "-o",
        "./bethyw"]
res = subprocess.run(cmd, cwd=os.getcwd() + "/_tempsrc", capture_output=True)

if res.returncode != 0:
  print("Compilation failed!")
  exit()

whitespace_pattern = re.compile(r'\s+')
for output_test in iter(output_tests):
  cmd = ["./bethyw"]
  args = output_tests[output_test][1]
  if len(args) == 0:
    continue
  cmd = cmd + args

  print("Comparing output to " + output_test)
  res = subprocess.run(cmd, cwd=os.getcwd() + "/_tempsrc", capture_output=True)

  with open(os.getcwd() + "/_tempsrc/tests/" + output_test) as f:
    match_to = re.sub(whitespace_pattern, '', f.read())

    output = re.sub(whitespace_pattern, '', res.stdout.decode("utf-8"))
    if output == match_to:
      output_results[output_test] = output_tests[output_test][0]
    else:
      output = re.sub(whitespace_pattern, '', res.stderr.decode("utf-8"))
      if output == match_to:
        output_results[output_test] = output_tests[output_test][0]


df = pd.read_csv("_marks/autograder.csv")
df = df.set_index('Username')

student = df.loc[autograder_id].copy()

original = {}
original['outputus2']  = student['Extended output tests - Unseen output 2: bethyw -a swan -m rail']
original['outputus2a'] = student['Extended output tests - Unseen output 2a: bethyw -a swan -m rail']
original['outputus5']  = student['Extended output tests - Unseen output 5: bethyw -a swan,card -m pop,rail -y 2010-2018 -j']
original['outputus5a'] = student['Extended output tests - Unseen output 5a: bethyw -a swan,card -m pop,rail -y 2010-2018 -j']
original['outputus6']  = student['Extended output tests - Unseen output 6: bethyw -a W06000015,W06000011 -y 2015 -j']
original['outputus6a'] = student['Extended output tests - Unseen output 6a: bethyw -a W06000015,W06000011 -y 2015 -j']

original['testus10']   = student['Extended Catch2 unit tests - Unseen test 10: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()']
original['testus10a']  = student['Extended Catch2 unit tests - Unseen test 10a: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()']


if original['outputus2'] > output_results["outputus2.txt"]:
  print("outputus2: original mark is higher (" + str(original['outputus2']) + " -> " + str(output_results["outputus2.txt"]) + ")")
elif original['outputus2'] == output_results["outputus2.txt"]:
  print("outputus2: original mark is equal (" + str(original['outputus2']) + " -> " + str(output_results["outputus2.txt"]) + ")")
else:
  print("outputus2: original mark is lower (" + str(original['outputus2']) + " -> " + str(output_results["outputus2.txt"]) + ")")
  student['Extended output tests - Unseen output 2: bethyw -a swan -m rail'] = output_results["outputus2.txt"]
  student['Extended output tests Total'] += output_results["outputus2.txt"]

if original['outputus2a'] > output_results["outputus2a.txt"]:
  print("outputus2a: original mark is higher (" + str(original['outputus2a']) + " -> " + str(output_results["outputus2a.txt"]) + ")")
elif original['outputus2a'] == output_results["outputus2a.txt"]:
  print("outputus2a: original mark is equal (" + str(original['outputus2a']) + " -> " + str(output_results["outputus2a.txt"]) + ")")
else:
  print("outputus2a: original mark is lower (" + str(original['outputus2a']) + " -> " + str(output_results["outputus2a.txt"]) + ")")
  student['Extended output tests - Unseen output 2a: bethyw -a swan -m rail'] = output_results["outputus2a.txt"]
  student['Extended output tests Total'] += output_results["outputus2a.txt"]


if original['outputus5'] > output_results["outputus5.json"]:
  print("outputus5: original mark is higher (" + str(original['outputus5']) + " -> " + str(output_results["outputus5.json"]) + ")")
elif original['outputus5'] == output_results["outputus5.json"]:
  print("outputus5: original mark is equal (" + str(original['outputus5']) + " -> " + str(output_results["outputus5.json"]) + ")")
else:
  print("outputus5: original mark is lower (" + str(original['outputus5']) + " -> " + str(output_results["outputus5.json"]) + ")")
  student['Extended output tests - Unseen output 5: bethyw -a swan,card -m pop,rail -y 2010-2018 -j'] = output_results["outputus5.json"]
  student['Extended output tests Total'] += output_results["outputus5.json"]
  
if original['outputus5a'] > output_results["outputus5a.json"]:
  print("outputus5a: original mark is higher (" + str(original['outputus5a']) + " -> " + str(output_results["outputus5a.json"]) + ")")
elif original['outputus5a'] == output_results["outputus5a.json"]:
  print("outputus5a: original mark is equal (" + str(original['outputus5a']) + " -> " + str(output_results["outputus5a.json"]) + ")")
else:
  print("outputus5a: original mark is lower (" + str(original['outputus5a']) + " -> " + str(output_results["outputus5a.json"]) + ")")
  student['Extended output tests - Unseen output 5a: bethyw -a swan,card -m pop,rail -y 2010-2018 -j'] = output_results["outputus5a.json"]
  student['Extended output tests Total'] += output_results["outputus5a.json"]


if original['outputus6'] > output_results["outputus6.json"]:
  print("outputus6: original mark is higher (" + str(original['outputus6']) + " -> " + str(output_results["outputus6.json"]) + ")")
elif original['outputus6'] == output_results["outputus6.json"]:
  print("outputus6: original mark is equal (" + str(original['outputus6']) + " -> " + str(output_results["outputus6.json"]) + ")")
else:
  print("outputus6: original mark is lower (" + str(original['outputus6']) + " -> " + str(output_results["outputus6.json"]) + ")")
  student['Extended output tests - Unseen output 6: bethyw -a W06000015,W06000011 -y 2015 -j'] = output_results["outputus6.json"]
  student['Extended output tests Total'] += output_results["outputus6.json"]

if original['outputus6a'] > output_results["outputus6a.json"]:
  print("outputus6a: original mark is higher (" + str(original['outputus6a']) + " -> " + str(output_results["outputus6a.json"]) + ")")
elif original['outputus6a'] == output_results["outputus6a.json"]:
  print("outputus6a: original mark is equal (" + str(original['outputus6a']) + " -> " + str(output_results["outputus6a.json"]) + ")")
else:
  print("outputus6a: original mark is lower (" + str(original['outputus6a']) + " -> " + str(output_results["outputus6a.json"]) + ")")
  student['Extended output tests - Unseen output 6a: bethyw -a W06000015,W06000011 -y 2015 -j'] = output_results["outputus6a.json"]
  student['Extended output tests Total'] += output_results["outputus6a.json"]


if original['testus10'] > catch2_results["testus10"]:
  print("testus10: original mark is higher (" + str(original['testus10']) + " -> " + str(catch2_results["testus10"]) + ")")
elif original['testus10'] == catch2_results["testus10"]:
  print("testus10: original mark is equal (" + str(original['testus10']) + " -> " + str(catch2_results["testus10"]) + ")")
else:
  print("testus10: original mark is lower (" + str(original['testus10']) + " -> " + str(catch2_results["testus10"]) + ")")
  student['Extended Catch2 unit tests - Unseen test 10: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()'] = catch2_results["testus10"]
  student['Extended Catch2 unit tests Total'] += catch2_results["testus10"]

if original['testus10a'] > catch2_results["testus10a"]:
  print("testus10a: original mark is higher (" + str(original['testus10a']) + " -> " + str(catch2_results["testus10a"]) + ")")
elif original['testus10a'] == catch2_results["testus10a"]:
  print("testus10a: original mark is equal (" + str(original['testus10a']) + " -> " + str(catch2_results["testus10a"]) + ")")
else:
  print("testus10a: original mark is lower (" + str(original['testus10a']) + " -> " + str(catch2_results["testus10a"]) + ")")
  student['Extended Catch2 unit tests - Unseen test 10a: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()'] = catch2_results["testus10a"]
  student['Extended Catch2 unit tests Total'] += catch2_results["testus10a"]

df.update(student)
df.loc[autograder_id] = student
# print(df.loc[autograder_id])
df.to_csv('_marks/autograder.csv', index=True)