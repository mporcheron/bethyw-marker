#!/usr/bin/env python3

import argparse

from curses import wrapper
from automarker import marker

    
parser = argparse.ArgumentParser(description='Mark CSC371 20/21 Coursework')

parser.add_argument(
  '-a', '--autograder',
  type=str, 
  default='_marks/autograder.csv',
  help="Autograder grades export CSV")

parser.add_argument(
  '-sd', '--submissions-dir',
  type=str, 
  default='submissions/',
  help="Directory containing all submissions")
  
parser.add_argument(
  '-s', '--student',
  type=str, 
  required=True,
  help="Student submission directory")

args = parser.parse_args()
m = marker(args.autograder, args.submissions_dir, args.student)
wrapper(m.run)
