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
  "test1"    : 1,
  "test2"    : 1,
  "test3"    : 1,
  "test4"    : 1,
  "test5"    : 2,
  "test6"    : 2,
  "test7"    : 2,
  "test8"    : 2,
  "test9"    : 2,
  "test10"   : 2,
  "test11"   : 2,
  "test12"   : 2,
  "testus1"  : 1,
  "testus2"  : 1,
  "testus3"  : 2,
  "testus4"  : 2,
  "testus5"  : 2,
  "testus6"  : 2,
  "testus7"  : 2,
  "testus8"  : 2,
  "testus9"  : 2,
  "testus10" : 2,
  "testus10a": 2,
  "testus11" : 2,
  "testus12" : 2,
}
  
catch2_results = {}
failed_tests = {}
total_points = 0
total_points_possible = 0

for catch2_test in iter(catch2_tests):
  catch2_results[catch2_test] = 0
  total_points_possible += catch2_tests[catch2_test]

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
        total_points += catch2_tests[catch2_test]
      break
  except ET.ParseError:
    print("Error with " + catch2_test)




output_tests = {
  "nowarnings"      : (2, []),
  "output1.txt"     : (1, ["-d", "invalidataset"]),
  "output2.txt"     : (1, ["--dir", "invaliddir", "-d", "popden"]),
  "output3.json"    : (1, ["-a", "doesnotexist", "-j"]),
  "output4.txt"     : (1, ["-d", "popden"]),
  "output5.json"    : (1, ["-d", "popden", "-j"]),
  "output6.json"    : (1, ["-d", "biz", "-j"]),
  "output7.json"    : (1, ["-d", "aqi", "-j"]),
  "output8.json"    : (1, ["-d", "trains", "-j"]),
  "output9.json"    : (1, ["-d", "complete-popden", "-j"]),
  "output10.json"   : (1, ["-d", "complete-pop", "-a", "W06000024", "-m", "area"]),
  "outputus1.json"  : (1, ["-a", "W060000999", "-y", "0", "-m", "rb,db,all", "-j"]),
  "outputus2.txt"   : (1, ["-a", "swan", "-m", "RAIL"]),
  "outputus2a.txt"  : (1, ["-a", "swan", "-m", "RAIL"]),
  "outputus3.txt"   : (1, ["-d", "popden", "-a", "swan", "-m", "RAIL"]),
  "outputus4.txt"   : (1, ["-d", "popden", "-a", "Abertawe,Swansea "]),
  "outputus5.json"  : (1, ["-a", "swan,card", "-m", "pop,rail", "-y", "2010-2018", "-j"]),
  "outputus5a.json" : (1, ["-a", "swan,card", "-m", "pop,rail", "-y", "2010-2018", "-j"]),
  "outputus6.json"  : (1, ["-a", "W06000015,W06000011", "-y", "2015", "-j"])
  "outputus6a.json" : (1, ["-a", "W06000015,W06000011", "-y", "2015", "-j"])
}
  
output_results = {}

print("Compiling application")
for output_test in iter(output_tests):
  output_results[output_test] = 0
  total_points_possible += output_tests[output_test][0]

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

if res.stdout.decode("utf-8") == "":
  output_results["nowarnings"] = output_tests["nowarnings"][0]
  total_points += output_tests["nowarnings"][0]

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
      total_points += output_tests[output_test][0]
    else:
      output = re.sub(whitespace_pattern, '', res.stderr.decode("utf-8"))
      if output == match_to:
        output_results[output_test] = output_tests[output_test][0]
        total_points += output_tests[output_test][0]




with open(os.getcwd() + "/_marks/autograder.csv", "a") as markscsv: 
  print("Saving results...")

  markscsv.write("\n")
  
  # Username
  markscsv.write(student_id + "@Swansea.ac.uk" + ",")

  # Group Members
  markscsv.write(student_id + "@Swansea.ac.uk" + ",")

  # Timestamp
  markscsv.write("manual" + ",")

  # Extension
  markscsv.write("" + ",")

  # Total Points
  markscsv.write(str(total_points) + ",")

  # Total Points Possible
  markscsv.write(str(total_points_possible) + ",")

  # Handgrading Total Points
  markscsv.write("" + ",")

  # Handgrading Total Points Possible
  markscsv.write("" + ",")


  # Output tests Total
  markscsv.write(
    str(output_results["nowarnings"]   +
        output_results["output1.txt"]  + output_results["output2.txt"]  + 
        output_results["output3.json"] + output_results["output4.txt"]  + 
        output_results["output5.json"] + output_results["output6.json"] + 
        output_results["output7.json"] + output_results["output8.json"] + 
        output_results["output9.json"] + output_results["output10.json"]) + ",")

  # Output tests Total Possible
  markscsv.write(str(12) + ",")

  # Output tests - Compilation completed without warnings
  markscsv.write(str(output_results["nowarnings"]) + ",")

  # Output tests - Output 1: bethyw -d invalidataset
  markscsv.write(str(output_results["output1.txt"]) + ",")

  # Output tests - Output 2: bethyw --dir invalidir
  markscsv.write(str(output_results["output2.txt"]) + ",")

  # Output tests - Output 3: bethyw -a doesnotexist -j
  markscsv.write(str(output_results["output3.json"]) + ",")

  # Output tests - Output 4: bethyw -d popden
  markscsv.write(str(output_results["output4.txt"]) + ",")

  # Output tests - Output 5: bethyw -d popden -j
  markscsv.write(str(output_results["output5.json"]) + ",")

  # Output tests - Output 6: bethyw -d biz -j
  markscsv.write(str(output_results["output6.json"]) + ",")

  # Output tests - Output 7: bethyw -d aqi -j
  markscsv.write(str(output_results["output7.json"]) + ",")

  # Output tests - Output 8: bethyw -d trains -j
  markscsv.write(str(output_results["output8.json"]) + ",")

  # Output tests - Output 9: bethyw -d complete-popden -j
  markscsv.write(str(output_results["output9.json"]) + ",")

  # Output tests - Output 10: bethyw -d complete-pop -a W06000024 -m area
  markscsv.write(str(output_results["output10.json"]) + ",")


  # Provided Catch2 unit tests Total
  markscsv.write(
    str(catch2_results["test1"]  + catch2_results["test2"]  + 
        catch2_results["test3"]  + catch2_results["test4"]  + 
        catch2_results["test5"]  + catch2_results["test6"]  + 
        catch2_results["test7"]  + catch2_results["test8"]  + 
        catch2_results["test9"]  + catch2_results["test10"] + 
        catch2_results["test11"] + catch2_results["test12"]) + ",")

  # Provided Catch2 unit tests Total Possible
  markscsv.write(str(20) + ",")

  # Provided Catch2 unit tests - Test 1: The --datasets program argument can be parsed as a list of datasets to import
  markscsv.write(str(catch2_results["test1"]) + ",")

  # Provided Catch2 unit tests - Test 2: The --areas program argument can be parsed correctly, whether it is a single area's code, a comma-separated list of codes, contains 'all' as a value, or is missing; and a filter list generated
  markscsv.write(str(catch2_results["test2"]) + ",")

  # Provided Catch2 unit tests - Test 3: The --measures program argument can be parsed correctly, whether it is a single measure's codename, a comma-separated list of codenames, contains 'all' as a value, or is missing
  markscsv.write(str(catch2_results["test3"]) + ",")

  # Provided Catch2 unit tests - Test 4: The --years program argument can be parsed correctly, whether it is a equal to single four-digit year, two four-digit years separated by a hyphen, '0', '0-0', or invalid due to the presence of non-numerical values
  markscsv.write(str(catch2_results["test4"]) + ",")

  # Provided Catch2 unit tests - Test 5: When given a path to a dataset file, an InputFile object is constructed and can return a reference to a stream if it is a valid path
  markscsv.write(str(catch2_results["test5"]) + ",")

  # Provided Catch2 unit tests - Test 6: A Measure object can be constructed in your coursework, where the constructor is given an std::string codename (which is converted to lowercase) and label, with a default size of 0
  markscsv.write(str(catch2_results["test6"]) + ",")

  # Provided Catch2 unit tests - Test 7: A Measure object can be populated with values, with the Measure object not allowing more than one value per year, and retrieving a non-existent value will throw an exception
  markscsv.write(str(catch2_results["test7"]) + ",")

  # Provided Catch2 unit tests - Test 8: An Area instance can be constructed with a local authority code and contain multiple names in different languages, identified by three-letter code
  markscsv.write(str(catch2_results["test8"]) + ",")

  # Provided Catch2 unit tests - Test 9: An Area instance can contain Measure instances and return values, and cannot contain two Measure instances with the same codename
  markscsv.write(str(catch2_results["test9"]) + ",")

  # Provided Catch2 unit tests - Test 10: An Areas instance can be constructed populated with Area instances, and cannot contain two Area instances with the same local authority code
  markscsv.write(str(catch2_results["test10"]) + ",")

  # Provided Catch2 unit tests - Test 11: The dataset areas.csv can be correctly parsed by your code in Areas::populateFromAuthorityCodeCSV()
  markscsv.write(str(catch2_results["test11"]) + ",")

  # Provided Catch2 unit tests - Test 12: The dataset popu1009.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()
  markscsv.write(str(catch2_results["test12"]) + ",")



  # Extended output tests Total
  markscsv.write(
    str(output_results["outputus1.json"]  + output_results["outputus2.txt"]  + 
        output_results["outputus3.txt"]  + output_results["outputus4.txt"]  + 
        output_results["outputus5.json"] + output_results["outputus6.json"]) + ",")

  # Extended output tests Total Possible
  markscsv.write(str(6) + ",")

  # Extended output tests - Unseen output 1: bethyw -a W060000999 -y 0 -m rb,db,all -j
  markscsv.write(str(output_results["outputus1.json"]) + ",")

  # Extended output tests - Unseen output 2: bethyw -a swan -m RAIL
  markscsv.write(str(output_results["outputus2.txt"]) + ",")

  # Extended output tests - Unseen output 2a: bethyw -a swan -m RAIL
  markscsv.write(str(output_results["outputus2a.txt"]) + ",")

  # Extended output tests - Unseen output 3: bethyw -d popden -a swan -m RAIL
  markscsv.write(str(output_results["outputus3.txt"]) + ",")

  # Extended output tests - Unseen output 4: bethyw -d popden -a Abertawe,Swansea
  markscsv.write(str(output_results["outputus4.txt"]) + ",")

  # Extended output tests - Unseen output 5: bethyw -a swan,card -m pop,rail -y 2010-2018 -j
  markscsv.write(str(output_results["outputus5.json"]) + ",")

  # Extended output tests - Unseen output 5a: bethyw -a swan,card -m pop,rail -y 2010-2018 -j
  markscsv.write(str(output_results["outputus5a.json"]) + ",")

  # Extended output tests - Unseen output 6: bethyw -a W06000015,W06000011 -y 2015 -j
  markscsv.write(str(output_results["outputus6.json"]) + ",")

  # Extended output tests - Unseen output 6a: bethyw -a W06000015,W06000011 -y 2015 -j
  markscsv.write(str(output_results["outputus6a.json"]) + ",")



  # Extended Catch2 unit tests Total
  markscsv.write(
    str(catch2_results["testus1"]  + catch2_results["testus2"]  + 
        catch2_results["testus3"]  + catch2_results["testus4"]  + 
        catch2_results["testus5"]  + catch2_results["testus6"]  + 
        catch2_results["testus7"]  + catch2_results["testus8"]  + 
        catch2_results["testus9"]  + catch2_results["testus10"] + 
        catch2_results["testus11"] + catch2_results["testus12"]) + ",")

  # Extended Catch2 unit tests Total Possible
  markscsv.write(str(22) + ",")

  # Extended Catch2 unit tests - Unseen test 1: The --years program argument throws the correct exception is an incorrect length (e.g. two digits)
  markscsv.write(str(catch2_results["testus1"]) + ",")

  # Extended Catch2 unit tests - Unseen test 2: A Measure object will replace an existing value when given a new value for an existing year
  markscsv.write(str(catch2_results["testus2"]) + ",")

  # Extended Catch2 unit tests - Unseen test 3: An Areas instance will merge two Area instances and the names of the second Area instances will overwrite the first
  markscsv.write(str(catch2_results["testus3"]) + ",")

  # Extended Catch2 unit tests - Unseen test 4: An Area instance will merge in values when given a Measure with the name matching the original
  markscsv.write(str(catch2_results["testus4"]) + ",")

  # Extended Catch2 unit tests - Unseen test 5: Measure codenames are imported and converted to lowercase when populated from a dataset stream
  markscsv.write(str(catch2_results["testus5"]) + ",")

  # Extended Catch2 unit tests - Unseen test 6: The requested statistics (difference, difference as percentage, and mean) can be correctly calculated from the imported data
  markscsv.write(str(catch2_results["testus6"]) + ",")

  # Extended Catch2 unit tests - Unseen test 7: The dataset econ0080.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()
  markscsv.write(str(catch2_results["testus7"]) + ",")

  # Extended Catch2 unit tests - Unseen test 8: The dataset envi0201.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()
  markscsv.write(str(catch2_results["testus8"]) + ",")

  # Extended Catch2 unit tests - Unseen test 9: The dataset tran0152.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()
  markscsv.write(str(catch2_results["testus9"]) + ",")

  # Extended Catch2 unit tests - Unseen test 10: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()
  markscsv.write(str(catch2_results["testus10"]) + ",")

  # Extended Catch2 unit tests - Unseen test 10a: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()
  markscsv.write(str(catch2_results["testus10a"]) + ",")

  # Extended Catch2 unit tests - Unseen test 11: An Area instance throws an exception when given a non-three alphabetical character language code
  markscsv.write(str(catch2_results["testus11"]) + ",")

  # Extended Catch2 unit tests - Unseen test 12: The program arugments work with a case-insensitive ALL value
  markscsv.write(str(catch2_results["testus12"]))
