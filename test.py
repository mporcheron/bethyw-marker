#!/usr/bin/env python3

import collections
import math
import os
import pandas as pd
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

output_tests = {
  "nowarnings"     : (2, []),
  "output1.txt"    : (1, ["-d", "invalidataset"]),
  "output2.txt"    : (1, ["--dir", "invaliddir", "-d", "popden"]),
  "output3.json"   : (1, ["-a", "doesnotexist", "-j"]),
  "output4.txt"    : (1, ["-d", "popden"]),
  "output5.json"   : (1, ["-d", "popden", "-j"]),
  "output6.json"   : (1, ["-d", "biz", "-j"]),
  "output7.json"   : (1, ["-d", "aqi", "-j"]),
  "output8.json"   : (1, ["-d", "trains", "-j"]),
  "output9.json"   : (1, ["-d", "complete-popden", "-j"]),
  "output10.json"  : (1, ["-d", "complete-pop", "-a", "W06000024", "-m", "area"]),
  "outputus1.json" : (1, ["-a", "W060000999", "-y", "0", "-m", "rb,db,all", "-j"]),
  "outputus2.txt"  : (1, ["-a", "swan", "-m", "RAIL"]),
  "outputus3.txt"  : (1, ["-d", "popden", "-a", "swan", "-m", "RAIL"]),
  "outputus4.txt"  : (1, ["-d", "popden", "-a", "Abertawe,Swansea "]),
  "outputus5.json" : (1, ["-a", "swan,card", "-m", "pop,rail", "-y", "2010-2018", "-j"]),
  "outputus6.json" : (1, ["-a", "W06000015,W06000011", "-y", "2015", "-j"])
}
  
output_results = {}

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
    print("==== RECEIVED ====\n" + output + "\n==== EXPECTED ====\n" + match_to)
