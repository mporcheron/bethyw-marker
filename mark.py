
import argparse

from curses import wrapper
from marker import marker

    
parser = argparse.ArgumentParser(description='Mark CSC371 20/21 Coursework')

parser.add_argument(
  '-s', '--student',
  type=str, 
  required=True,
  help="Student submission directory")

args = parser.parse_args()
m = marker(args.student)
wrapper(m.run)
