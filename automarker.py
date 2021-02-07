
import curses
import collections
import emoji
import math
import os
import pandas as pd
import re
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

# curses implementation based on PyRadio: in

class marker:
  MARKS_DIR       = os.getcwd() + "/_marks"
  AUTOGRADER_FILE = MARKS_DIR + "/autograder.csv"

  def __init__(self, autograder_file, student_id):
    self.stdscr        = None
    self.start_pos     = 0
    self.auto_progress = True
    
    marker.AUTOGRADER_FILE = autograder_file
    
    # student's detail)
    self.student_id      = student_id
    self.marks           = 0
    self.total_marks     = 100
    self.max_marks       = self.total_marks
    self.marks_breakdown = collections.OrderedDict()
    self.feedback        = ""

    # The busy timer shows an animated ellipsis while computation is happening
    self.busy_dots       = 0
    self.busy_timer      = None
    self.busy_timer_stop = False

    # The various marking stages
    self.status = "Initialise marker system"

    self.progress = collections.OrderedDict()
    self.progress["setup"]            = stage("Copy student's submission into temporary marking directory", coursework.setup)
    self.progress["autograder"]       = stage("Parse autograder output",                                    coursework.autograder)
    self.progress["readme"]           = stage("Read the student's README",                                  coursework.readme)
    self.progress["opensrc"]          = stage("Begin reading through the student's code",                   coursework.opensrc)
    self.progress["memtest"]          = stage("Run the coursework with Valgrind",                           coursework.memtest)
    self.progress["function_ordering"]= stage("Check that they have retained the ordering of functions",    coursework.function_ordering)
    self.progress["quality"]          = stage("Evaluate the coding quality",                                coursework.quality)
    #self.progress["feedback"]         = stage("Modify the feedback",                                        coursework.feedback)

    self.current_stage = "setup"

  def run(self, stdscr):
    self.stdscr = stdscr

    curses.noecho()
    self.stdscr.keypad(True)
    curses.cbreak()

    try:
        curses.curs_set(0)
    except:
        pass

    curses.start_color()
    
    # default
    curses.init_pair(1, curses.COLOR_WHITE,   curses.COLOR_BLACK)

    # title
    curses.init_pair(2, curses.COLOR_WHITE,   curses.COLOR_BLUE)

    # command
    curses.init_pair(3, curses.COLOR_CYAN,    curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    
    # error popup windows
    curses.init_pair(5, curses.COLOR_RED,     curses.COLOR_BLACK)
    
    # non-error popup windows
    curses.init_pair(6, curses.COLOR_GREEN,   curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_GREEN,   curses.COLOR_BLACK)

    self.setup()
    self.refresh_command()
    self.make_progress()

    while True:
      try:
        if self.current_stage != None and self.auto_progress:
          self.make_progress()
          time.sleep(1)
          continue

        c = self.win_command.getch()
        if self.current_stage != None and c == ord('y'):
          self.make_progress()
        elif c == ord('q'):
          break
      except KeyboardInterrupt:
          break

    self.write_feedback()


  def write_feedback(self):
    with open(self.MARKS_DIR + "/marks.csv", "a") as f:
      f.write(self.student_id + "," + str(min(self.marks, self.max_marks)))
      for key, marks in self.marks_breakdown.items():
        f.write("," + str(marks))
      f.write("\n")

    with open(self.MARKS_DIR + "/" + self.student_id + "-feedback.txt", "a") as f:
      f.write("Feedback for {0} ({1}/{2})\n\n".format(self.student_id, min(self.marks, self.max_marks), self.total_marks))
      f.write(self.feedback)


  def setup(self):
    self.max_y, self.max_x = self.stdscr.getmaxyx()

    self.win_title   = curses.newwin(3, self.max_x, 0, 0)
    self.win_body    = curses.newwin(self.max_y - 6, self.max_x, 3, 0)
    self.win_command = curses.newwin(3, self.max_x, self.max_y - 3, 0)

    self.setup_title()
    self.setup_body()
    self.setup_command()

    self.win_body.keypad(1)
    curses.doupdate()


  def setup_title(self):
    self.win_title.bkgd(' ', curses.color_pair(2) | curses.A_BOLD)
    self.win_title.addstr(1, 2, "CSC371 20/21 Marker", curses.color_pair(2))

    self.refresh_marks()
    self.win_title.noutrefresh()


  def setup_body(self):
    self.max_y_body, self.max_x_body = self.win_body.getmaxyx()
    self.win_body.noutrefresh()
    self.refresh_body()


  def setup_command(self):
    self.win_command.noutrefresh()
    self.refresh_command()


  def setup_decision(self, decision):
    start_y = 10
    start_x = 10
    height  = len(decision) + 5
    width   = self.max_x - 20

    self.win_decision = curses.newwin(height, width, start_y, start_x)
    self.win_decision.box()

    title = " MAKE A DECISION "
    self.win_decision.addstr(0, int((width - len(title)) / 2), title, curses.color_pair(6) | curses.A_BOLD | curses.A_BLINK)

    self.win_decision.refresh()
    curses.doupdate()

    return self.refresh_decision(decision, 0)


  def refresh_marks(self):
    marks = min(self.marks, self.max_marks)

    text = "{0} ({1}/{2})".format(self.student_id, marks, self.total_marks)
    student_id_x = self.max_x - len(text) - 2

    self.win_title.addstr(1, student_id_x, text, curses.color_pair(2))
    self.win_title.refresh()


  def refresh_body(self):
    self.win_body.erase()
    self.win_body.move(3, 1)

    max_display = self.max_y_body - 1

    self.show_progress(max_display)
    self.win_body.refresh()


  def refresh_command(self, awaiting_input=True):
    try:
      self.busy_timer_stop = True
    except AttributeError:
      pass

    self.win_command.erase()
    self.win_command.box()

    self.win_command.addstr(1, 2, "Current stage:", curses.color_pair(3))
    self.win_command.addstr(1, 17, self.status, curses.color_pair(3) | curses.A_BOLD)

    if self.current_stage == None:
      text = "Completed [q]"
      progress_x = self.max_x - len(text) - 2
      self.win_command.addstr(1, progress_x, text, curses.color_pair(4) | curses.A_BOLD)
      self.win_command.refresh()
    else:
      if awaiting_input:
        text = "Progress? [y/n]"
        progress_x = self.max_x - len(text) - 2
        self.win_command.addstr(1, progress_x, text, curses.color_pair(4) | curses.A_BOLD | curses.A_BLINK)
        self.win_command.refresh()
      else:
        self.busy_timer_stop = False
        self.busy_timer = threading.Timer(0, self.refresh_command_ticker)
        self.busy_timer.daemon = True
        self.busy_timer.start()


  def refresh_command_ticker(self):
    """Shows the busy ellipsis in the command area"""
    while not self.busy_timer_stop:
      text = "             "
      progress_x = self.max_x - len(text) - 5
      busy_dots = 1 + self.busy_dots
      for i in range(0, 3):
        text += "." if i < busy_dots else " "

      self.busy_dots = ((self.busy_dots + 1) % 3)
      self.win_command.addstr(1, progress_x, text, curses.color_pair(7) | curses.A_BOLD)
      self.win_command.refresh()
      time.sleep(.6)


  def refresh_decision(self, decision, selected_option):
    for i, option in enumerate(decision):
      text = "["
      text += "X" if selected_option == i else " "
      text += "] " + decision[option][0]
      self.win_decision.addstr(i+2, 2, text, curses.color_pair(6))

    self.win_decision.refresh()

    while True:
      char =  self.win_decision.getch()
      if char == 65: # up arrow
        selected_option = (selected_option - 1) % len(decision)
        return self.refresh_decision(decision, selected_option)
      elif char == 66: # down arrow
        selected_option = (selected_option + 1) % len(decision)
        return self.refresh_decision(decision, selected_option)
      elif char == 10: # enter
        keys = list(decision.keys())
        return decision[keys[selected_option]]


  def setup_viewtext(self, title, contents, is_error=False):
    colour = curses.color_pair(5) if is_error else curses.color_pair(6)
      
    start_y = 4
    start_x = 10
    height = self.max_y - 7
    width = self.max_x - 20

    self.win_viewtext = curses.newwin(height, width, start_y, start_x)
    self.win_viewtext.box()

    title = " " + title + " (enter to close) "
    self.win_viewtext.addstr(0, int((width - len(title)) / 2), title, colour | curses.A_BOLD)

    self.win_viewtext.refresh()
    curses.doupdate()
    
    max_visible_columns = self.max_x - 24
    init_contents_by_line = contents.split('\n')
    formatted_contents_by_line = []
    arr_pos = 0
    file_ended = False
    while not file_ended:
      while True:
        try:
          line = init_contents_by_line[arr_pos]
        except IndexError:
          file_ended = True
          break
      
        if len(line) > 0 and line[0] == ' ':
          line = line[1:]

        if len(line) <= max_visible_columns:
          formatted_contents_by_line.append(line)
          break
        else:
          for split_proposal in reversed(range(max_visible_columns+1)):
            if line[split_proposal] == ' ':
              break

          if split_proposal == 0:
            split_proposal = max_visible_columns

          head = line[:split_proposal]
          indent_by = len(head) - len(head.lstrip('* -1234567890#'))
          tail = line[split_proposal:]
          tail = tail.rjust(len(tail) + indent_by, ' ')
      
          formatted_contents_by_line.append(head)      
          init_contents_by_line[arr_pos] = tail

      arr_pos += 1

    for num, line in enumerate(formatted_contents_by_line):
      formatted_contents_by_line[num] = line.ljust(max_visible_columns, ' ')

    self.refresh_viewtext(formatted_contents_by_line, 0, is_error)


  def refresh_viewtext(self, contents_by_line, current_starting_line = 0, is_error=False):
    colour = curses.color_pair(1) if is_error else curses.color_pair(6)
    total_lines = len(contents_by_line)
    
    start_printing_at = 1
    max_visible_lines = self.max_y - 10
    at_start_of_text = True if current_starting_line == 0 else False
    at_end_of_text = False
    wrapped_lines = 0
    num_printed_lines = 0
    
    for actual_line in range(current_starting_line, total_lines):
      y_pos = start_printing_at + num_printed_lines
      self.win_viewtext.addstr(y_pos, 2, contents_by_line[actual_line], colour)
      
      if actual_line == 0:
        at_start_of_text = True
      elif actual_line + 1 == total_lines:
        at_end_of_text = True

      num_printed_lines += 1
      if y_pos > max_visible_lines:
        break
    
    self.win_viewtext.refresh()
    
    while True:
      char =  self.win_viewtext.getch()
      if char == 65 and not at_start_of_text: # up arrow
        self.refresh_viewtext(contents_by_line, current_starting_line - 1, is_error)
        break
      elif char == 66 and not at_end_of_text: # down arrow
        self.refresh_viewtext(contents_by_line, current_starting_line + 1, is_error)
        break
      elif char == 10: # enter
        return
      
      self.win_viewtext.refresh()


  def show_progress(self, max_display):
    colour = curses.color_pair(1)
    self.win_body.addstr(self.start_pos + 1, 2, "MARKING PROGRESS", colour)
    i = 1
    for key, stage in self.progress.items():
      line_num = i + self.start_pos + 2
      if stage.completed == -1:
        task_str = " " + emoji.emojize(":thumbs_down:")
      elif stage.completed == 0:
        task_str =  " " + emoji.emojize(":SOON_arrow:")
      elif stage.completed == 1:
        task_str = " " + emoji.emojize(":check_box_with_check:") + " "

      task_str += "  " + stage.label
      self.win_body.addstr(line_num, 1, task_str, colour)
      i += 1


  def make_progress(self):
    if self.current_stage != -1:
      pass

    # update the UI
    next_stage         = self.progress[self.current_stage]
    self.status        = next_stage.label
    self.refresh_command(False)

    # compute the marking
    stage_result       = next_stage.function(self.student_id,
                                             self.marks,
                                             self.feedback)

    self.status        = stage_result.updated_label
    
    if stage_result.stderr is not None:
      self.setup_viewtext("ERROR: " + self.status.upper(), stage_result.stderr, True)

    if stage_result.view_text != None:
      self.setup_viewtext(stage_result.view_text[0], stage_result.view_text[1])

    if stage_result.decision != None:
      if isinstance(stage_result.decision, list):
        feedback = ""
        marks = 0
        for d in iter(stage_result.decision):
          decision_result                        = self.setup_decision(d)
          marks                                 += decision_result[1]
          feedback                              += decision_result[2]
        self.marks                              += marks
        self.marks_breakdown[self.current_stage] = marks
        self.feedback                           += feedback
      else:
        decision_result                          = self.setup_decision(stage_result.decision)
        self.status                              = decision_result[0]
        self.marks                              += decision_result[1]
        self.marks_breakdown[self.current_stage] = decision_result[1]
        self.feedback                           += decision_result[2]
    else:
      self.marks                                += stage_result.student_marks
      self.marks_breakdown[self.current_stage]   = stage_result.student_marks
      self.feedback                             += stage_result.student_feedback

    if stage_result.student_max_marks is not None:
      self.max_marks  = stage_result.student_max_marks

    # update the existing stage's information
    next_stage.label = stage_result.updated_label
    next_stage.completed = -1 if stage_result.next_stage == -1 else 1

    # progress onto next stage
    self.current_stage = stage_result.next_stage
    self.refresh_marks()
    self.refresh_body()
    self.refresh_command(True)





class stage:
  def __init__(self,
               label,
               function):
    self.label = label
    self.function = function
    self.completed = 0





class stage_result:
  def __init__(self,
               updated_label,            # updated stage label
               next_stage,               # set to None if we cannot continue
               student_feedback = "",    # append student feedback with this
               student_marks = 0,        # append student marks with this
               student_max_marks = None, # set the maximum number of marks
               decision = None,          # if we need the human to decide
               view_text = None,         # if we want to show a document
               details = None):          # if there is an error
    self.updated_label = updated_label
    self.next_stage = next_stage
    self.student_feedback = student_feedback
    self.student_marks = student_marks
    self.student_max_marks = student_max_marks
    self.decision = decision
    self.view_text = view_text
    self.stderr = details





class coursework:
  CATCH2_EXE    = os.getcwd() + "/_bin/catch.o"
  MARKS_DIR     = os.getcwd() + "/_marks"
  ORIG_SRC_DIR  = os.getcwd() + "/_origsrc"
  TEST_SRC_DIR  = os.getcwd() + "/_tempsrc"

  CMD_OPEN_GIT      = ["open","-a","Sourcetree"]
  CMD_OPEN_README   = ["open","-a","TextMate"]
  CMD_OPEN_CODE     = ["open","-a","TextMate"]
  CMD_OPEN_FEEDBACK = ["open","-a","TextMate"]


  def __rmdir(directory):
    if os.path.isdir(directory):
      for root, dirs, files in os.walk(directory):
        for file in files:
          os.remove(os.path.join(root, file))

      shutil.rmtree(directory)
    os.rmdir(directory)


  def setup(student_id, marks, feedback):
    try:
      coursework.__rmdir(coursework.TEST_SRC_DIR)
    except FileNotFoundError:
      pass
      
    shutil.copytree(coursework.ORIG_SRC_DIR, coursework.TEST_SRC_DIR)

    try:
      coursework.__rmdir(student_id + "/bin")
    except FileNotFoundError:
      pass

    # try:
    for src_dir, dirs, files in os.walk(student_id):
      dst_dir = src_dir.replace(student_id, coursework.TEST_SRC_DIR, 1)
      
      if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
      
      for file in files:
        src_file = os.path.join(src_dir, file)
        dst_file = os.path.join(dst_dir, file)
        shutil.copy(src_file, dst_file)

    return stage_result(
      updated_label = "Student files successfully copied into temporary marking directory",
      next_stage    = "autograder")


  def autograder(student_id, marks, feedback):
    if not os.path.isfile(marker.AUTOGRADER_FILE):
      return stage_result(
        updated_label = "Could not load autograder results from " + marker.AUTOGRADER_FILE,
        next_stage    = None)

    key = student_id + "@Swansea.ac.uk"

    df = pd.read_csv(marker.AUTOGRADER_FILE)
    df = df.set_index('Username')

    try:
      autograder_marks = df.loc[key]

      feedback = "COMPILATION\n"
      if autograder_marks['Output tests - Compilation completed without warnings'] == 0:
        feedback += "It looks like your code has some warnings or errors from the compiler? You should aim to always produce code that has no warnings or errors, even if it is incomplete and does not implement all the functionality. This was a relatively easy area to pick up some marks (i.e. the code you were given compiles without warnings already). You were able to test your output using the CS Autograder, which displayed this feedback to you.\n\n"
      else:
        feedback += "Your code compiled without issuing any warnings, even with all the extra options enabled—this is great! You should never be submitting code with errors or warnings, even if the code is incomplete.\n\n"

      feedback = "PROGRAM OUTPUT\n"

      # Output tests
      if autograder_marks['Output tests Total'] == 0:
        feedback += "It seems your code failed to pass any of the output tests. For this coursework you were given a specification and expected to program towards it. These tests were all available on the CS Autograder. The system was configured to provide the output of your program and the expected output to help you with your development. You were advised to make sure you passed these tests. "
      elif autograder_marks['Output tests Total'] < 5:
        feedback += "You code passed less than 50% of the provided output tests on the CS Autograder. The system was configured to provide the output of your program and the expected output to help you with your developed. You were advised to make sure you passed these tests, and so it is a shame to see that you did not manage to score well in this section. "
      elif autograder_marks['Output tests Total'] < 10:
        feedback += "You code passed most of the provided output tests on CS Autograder. These were designed to test the basic output of your program in response to the commands, and the CS Autograder was configured to provide you with the expected output as well as the output from your program. These were easy points to score, so it is a shame you didn't quite get full marks here. "
      else:
        feedback += "You passed all the provided output tests, scoring all 10 mars possible. These were designed to test the basic output of your program in response to the commands. "

      temp_failed = []
      temp_passed = []

      if autograder_marks['Output tests - Output 1: bethyw -d invalidataset'] == 0:
        temp_failed.append("Your code did not output 'No dataset matches key: <invalid dataset>' to standard error (stderr) when given an invalid dataset as a program argument. This was stated in the block comment for BethYw::parseDatasetsArg() in bethyw.cpp.")
      else:
        temp_passed.append("Your code did output 'No dataset matches key: <invalid dataset>' to standard error (stderr) when given an invalid dataset as a program argument.")

      if autograder_marks['Output tests - Output 2: bethyw --dir invalidir'] == 0:
        temp_failed.append("Your code did not output 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets. This should have been a combination of the exception message thrown by InputFile::open() in input.cpp and the prepending error message as stated in BethYw::loadDatasets() in bethyw.cpp.")
      else:
        temp_passed.append("Your code did output 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets.")

      if autograder_marks['Output tests - Output 3: bethyw -a doesnotexist -j'] == 0:
        temp_failed.append("Your code when given an invalid area code with the JSON output flag should output an empty JSON object ({}), as stated in the block comment of Areas::toJSON() in areas.cpp.")
      else:
        temp_passed.append("Your code did output an empty JSON object when given a non-existant area.")

      if autograder_marks['Output tests - Output 4: bethyw -d popden'] == 0:
        if autograder_marks['Output tests - Output 5: bethyw -d popden -j'] == 0:
          temp_passed.append("Your code did not give the expected textual output for the popden dataset. We removed all whitepace and still your output did not match. You should check on Autograder to determine why (this was visible to you during the submission period too!). Perhaps you were imported data incorrectly as your JSON output was also invalid.")
        else:
          temp_passed.append("Your code did not give the expected textual output for the popden dataset. We removed all whitepace and still your output did not match. You should check on Autograder to determine why (this was visible to you during the submission period too!). Despite this, your JSON output was correct suggesting the issue is in one of your operator<< functions.")
      else:
        if autograder_marks['Output tests - Output 5: bethyw -d popden -j'] == 0:
          temp_failed.append("Your code had the correct textual output for the popden dataset, although curiously the JSON output does not seem to match what we expected?")
        else:
          temp_passed.append("Your code gave the correct textual/tables output and JSON output for the popden dataset.")

      if autograder_marks['Output tests - Output 6: bethyw -d biz -j'] == 0:
        temp_failed.append("Your code did not give the expected JSON output for the biz dataset. Perphaps this was because this dataset included additional areas—you were guided in Areas::populateFromWelshStatsJSON() in areas.cpp that if you encounter additional areas in a dataset, you should import them still.")
      else:
        temp_passed.append("Your code generated the expected JSON output for the biz dataset, creating the additional Area objects.")

      if autograder_marks['Output tests - Output 7: bethyw -d aqi -j'] == 0:
        temp_failed.append("Your code did not give the expected JSON output for the aqi dataset. Perhaps this was because the dataset's data column errornously stores its values as strings? You were forewarned about this in the coursework assignment sheet.")
      else:
        temp_passed.append("Your code generated the expected JSON output for the aqi dataset, handling the badly formatted StatsWales JSON files.")

      if autograder_marks['Output tests - Output 8: bethyw -d trains -j'] == 0:
        temp_failed.append("Your code did not give the expected JSON output for the trains dataset. This dataset only contained one measure, thus needed you to modify your populate functions for these sorts of files.")
      else:
        temp_passed.append("Your code generated the expected JSON output for the trains dataset, handling the fact that it was a single measure dataset.")

      if autograder_marks['Output tests - Output 9: bethyw -d complete-popden -j'] == 0:
        temp_failed.append("Your code did not give the expected JSON output for the complete-popden dataset. Either you didn't manage to implement the functionality to parse these CSV files, or your code failed to handle overwriting values and filling in the blanks of missing data.")
      else:
        temp_passed.append("Your code generated the expected JSON output for the complete-popden dataset, which was the specially-crafted CSV format. This means your code also correctly handled overwriting values and filling in the blanks of missing data.")

      if autograder_marks['Output tests - Output 10: bethyw -d complete-pop -a W06000024 -m area'] == 0:
        temp_failed.append("Your code did not give the expected textual output for the complete-popden dataset, when filtered for a specific area, and then a measure that was not contained in this file. You were guided how to do this in the block comment for operator<< in area.cpp.")
      else:
        temp_passed.append("Your code generated the expected textual output for the complete-popden dataset, when filtered for a specific area, and then a measure that was not contained in this file.")

      feedback += "Using the provided output tests in autograder, we can say that:\n"
      for temp in iter(temp_passed):
        feedback += '  - ' + temp + '\n'          
      for temp in iter(temp_passed):
        feedback += '  - ' + temp + '\n'
      feedback += '\n'
      #
      # if autograder_marks['Extended output tests Total'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended output tests Total Possible'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended output tests - Unseen output 1: bethyw -a W060000999 -y 0 -m rb,db,all -j'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended output tests - Unseen output 2: bethyw -a swan -m RAIL'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended output tests - Unseen output 3: bethyw -d popden -a swan -m RAIL'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended output tests - Unseen output 4: bethyw -d popden -a Abertawe,Swansea '] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended output tests - Unseen output 5: bethyw -a swan,card -m pop,rail -y 2010-2018 -j'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended output tests - Unseen outpout 6: bethyw -a W06000015,W06000011 -y 2015 -j'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      #
      #
      #
      #
      # if autograder_marks['Provided Catch2 unit tests Total'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests Total Possible'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 1: The --datasets program argument can be parsed as a list of datasets to import can be generated correctly'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 2: The --areas program argument can be parsed correctly, whether it is a single area's code, a comma-separated list of codes, contains 'all' as a value, or is missing; and a filter list can be generated correctly'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 3: The --measures  program argument can be parsed correctly, whether it is a single measure's codename, a comma-separated list of codenames, contains 'all' as a value, or is missing'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 4: The --years program argument can be parsed correctly, whether it is a equal to single four-digit year, two four-digit years separated by a hyphen, '0', '0-0', or invalid due to the presence of non-numerical values'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 5: When given a path to a dataset file, an InputFile object is constructed and can return a reference to a stream if it is a valid path'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 6: A Measure object can be constructed in your coursework, where the constructor is given an std::string codename (which is converted to lowercase) and label, with a default size of 0'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 7: A Measure object can be populated with values, with the Measure object not allowing more than one value per year, and retrieving a non-existant value will throw an exception'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 8: An Area instance can be constructed with a local authority code and contain multiple names in different languages, identified by three-letter code'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 9: An Area instance can contain Measure instances and return values, and cannot contain two Measure instances with the same codename'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 10: An Areas instance can be constructed populated with Area instances, and cannot contain two Area instances with the same local authority code'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 11: The dataset areas.csv can be correctly parsed by your code in Areas::populateFromAuthorityCodeCSV()'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Provided Catch2 unit tests - Test 12: The dataset popu1009.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests Total'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests Total Possible'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 1: The --years program argument throws the correct exception is an incorrect length (e.g. two digits)'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 2: A Measure object will replace an existing value when given a new value for an existing year'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 3: An Areas instance will merge two Area instances and the names of the second Area instances will overwrite the first'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 4: An Area instance will merge in values when given a Measure with the name matching the original'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 5: Measure codenames are imported and converted to lowercase when populated from a dataset stream'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 6: The requested statistics (difference, differance as percentage, and mean) can be correctly calculated from the imported data'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 7: The dataset econ0080.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 8: The dataset envi0201.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 9: The dataset tran0152.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      #
      # if autograder_marks['Extended Catch2 unit tests - Unseen test 10: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()'] == 0:
      #   temp_failed.append("explanation")
      # else:
      #   temp_passed.append("explanation")
      
      
      return stage_result(
        updated_label    = "Autograder marks imported and feedback generated",
        student_feedback = feedback,
        student_marks    = autograder_marks['Total Points'],
        next_stage       = "readme")
    except KeyError:
      return stage_result(
        updated_label = "Could not find student's marks in autograder export",
        next_stage    = None)
      


  def readme(student_id, marks, feedback):
    if not os.path.isfile(coursework.TEST_SRC_DIR + "/README.md"):
      return stage_result(
        updated_label = "No README.md included",
        next_stage    = "compile")

    with open(coursework.TEST_SRC_DIR + "/README.md", "r") as f:
      contents = f.read()

    return stage_result(
      updated_label = "README.md included and opened",
      view_text     = ("README.md", contents),
      next_stage    = "opensrc")



  def opensrc(student_id, marks, feedback):
    cmd = coursework.CMD_OPEN_CODE + [coursework.TEST_SRC_DIR]
    res = subprocess.run(cmd)
    return stage_result(
      updated_label     = "Source code opened in external application",
      next_stage        = "memtest")


  def memtest(student_id, marks, feedback):
    return stage_result(
        updated_label    = "Memory leak test skipped",
        next_stage       = "function_ordering")

    cmd = ["valgrind",
           "--leak-check=yes",
           "--show-leak-kinds=all",
           "--track-origins=yes",
           "./bin/bethyw"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

    if res.returncode != 0:
      # details = ' '.join(cmd) + "\n\n"
      details = res.stderr.decode("utf-8")

      return stage_result(
        updated_label = "Running with valgrind failed with result {0}".format(res.returncode),
        next_stage    = None,
        details       = details)

    feedback = "MEMORY LEAKS\n"
    valgrind_response = res.stderr.decode("utf-8")

    with open(coursework.MARKS_DIR + "/" + student_id + '-valgrind.txt', 'w') as file:
      file.write(valgrind_response)

    if valgrind_response.find("All heap blocks were freed") > 0:
      feedback += "Great work, your code has no memory leaks.\n\n"
      return stage_result(
          updated_label    = "Coursework passed memory leak test",
          next_stage       = "function_ordering",
          student_feedback = feedback,
          student_marks    = 5)
    else:
      feedback += "It seems that your code contains a one or more memory leaks. You should make sure you free any memory you allocate on the heap. In reality, you should have used good RAII principles taught in lectures and not needed to handle memory management at all.\n\n"
      return stage_result(
          updated_label    = "Coursework was found to contain memory leaks",
          next_stage       = "function_ordering",
          student_feedback = feedback)


  def function_ordering(student_id, marks, feedback):
    order = {"area.cpp": [
              "Area::Area",
              "Area::getLocalAuthorityCode",
              "Area::getName",
              "Area::setName",
              "Area::getMeasure",
              "Area::setMeasure",
              "Area::size"],

            "areas.cpp": [
              "Areas::Areas()",
              "Areas::setArea",
              "Areas::setArea",
              "Areas::getArea",
              "Areas::wildcardCountSet",
              "Areas::isLocalAuthorityFiltered",
              "Areas::size",
              "Areas::populateFromAuthorityCodeCSV",
              "Areas::populateFromWelshStatsJSON",
              "Areas::populateFromAuthorityByYearCSV",
              "Areas::populate",
              "Areas::populate",
              "Areas::toJSON"],

            "bethyw.cpp": [
              "BethYw::parseDatasetsArg",
              "BethYw::parseAreasArg",
              "BethYw::parseMeasuresArg",
              "BethYw::parseYearsArg",
              "BethYw::loadAreas",
              "BethYw::loadDatasets"],

            "input.cpp": [
              "InputSource::InputSource",
              "InputSource::getSource",
              "InputFile::open"],

            "measure.cpp": [
              "Measure::Measure",
              "Measure::getCodename",
              "Measure::getLabel",
              "Measure::setLabel",
              "Measure::getValue",
              "Measure::setValue",
              "Measure::size",
              "Measure::getDifference",
              "Measure::getDifferenceAsPercentage",
              "Measure::getAverage"]}

    whitespace_pattern = re.compile(r'\s|\n|\r+')

    in_order = True
    for filename, functions in order.items():
      with open(coursework.TEST_SRC_DIR + "/" + filename) as file:
        contents = re.sub(whitespace_pattern, '', file.read())
        prev_pos = -1
        for i, function in enumerate(functions):
          pos = contents.find(function)
          if pos > -1 and pos < prev_pos:
            in_order = False
            break;

        if not in_order:
          break

    if in_order:
      return stage_result(
        updated_label    = "The student has kept the functions in order",
        student_feedback = "CODE STYLE\nThank you for keeping the functions in the same order as in the provided code. This makes it easier to mark your work. ",
        student_marks    = 1,
        next_stage       = "quality")
    else:
      return stage_result(
        updated_label    = "The student didn't keep the functions in order",
        student_feedback = "CODE STYLE\nYou were asked to keep the functions in the same order as they were given to you in the block comments. Not doing this makes it significantly harder to mark your work. ",
        student_marks    = 0,
        next_stage       = "quality")


  def quality(student_id, marks, feedback):
    multidecision = [
        {"comments1": ("Good commenting in relevant places",                                                  3, "You have used commenting well throughout your coursework solution. Comments help readers of your code understand complex code blocks. "),
         "comments2": ("Could have included additional comments to explain complex chunks of code",           2, "You could have used some more comments in your coursework solution to help readers of your code understand complex code blocks. "),
         "comments3": ("Excessive commenting given the complexity of the code",                               2, "You have used a few too many comments in your coursework solution. Remember, you only need comments to explain complex chunks of code rather than individual lines. You were told to assume that the people marking your work know C++. "),
         "comments4": ("Alright commenting (i.e. have used them if needed)",                                  1, "Your use of commenting is OK. Remember, you only need comments to explain complex chunks of code rather than individual lines. You were told to assume that the people marking your work know C++. In future, focus on providing explanatory comments rather than comments that merely repeat what can be gleamed from code. "),
         "comments5": ("No commenting",                                                                       0, "You haven't really used any comments of note in your work. In future, you should use comments to explain complex chunks of code that may not be obvious at first glance. ")},

        {"naming1":   ("Consistently good naming of variables and functions",                                 2, "In terms of naming convention, you have consistently used good naming of variables etc. in your code. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments.\n\n", 3),
         "naming2":   ("Generally good naming of variables and functions",                                    1, "In terms of naming convention, you have used good naming of variables etc. in your code. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments.\n\n", 2),
         "naming3":   ("Alright naming of variables and functions (e.g. some variables are not descriptive)", 1, "In terms of naming convention, you could have shown greater care with naming your elements such as variables. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments. Remember, the names of variables if for humans reading your code and not the machine, so don't simply default to giving simplistic names, e.g., i, except in limited cased (e.g. iterators).\n\n", 1),
         "naming4":   ("Poor naming of variables ",                                                           0, "CODE EFFICIENCY\nYou don't seem to have adopted a convention when it comes to naming your elements such as variables. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments. Remember, the names of variables if for humans reading your code and not the machine, so don't simply default to giving simplistic names, e.g., i, except in limited cased (e.g. iterators).\n\n", 0)},

        {"except1":   ("Good use of exceptions throughout (caught with const ref)",                           4, "CODE EFFICIENCY\nWith respect to exceptions, you have used these very well in your coursework, including catching them as constant references. "),
         "except2":   ("Good use of exceptions throughout (not caught with const ref)",                       3, "CODE EFFICIENCY\nWith respect to exceptions, you have used these very well in your coursework. However, you did not always catch your references as constant references as your told to do in lectures. "),
         "except3":   ("Places where they should have caught exceptions",                                     2, "CODE EFFICIENCY\nWith respect to exceptions, there are places where you should have caught exceptions. You should have inspected a reference manual for the Standard Library functions you use to determine if they throw exceptions that may need catching. "),
         "except4":   ("Not really any exception handling in this coursework",                                1, "CODE EFFICIENCY\nWith respect to exceptions, you didn't seem to engage in the exception throwing/catching practice, as expected. You should have inspected a reference manual for the Standard Library functions you use to determine if they throw exceptions that may need catching.  "),
         "except5":   ("Use of wildcard catch (...)",                                                         0, "CODE EFFICIENCY\nFirstly, dissapointingly, despite being asked not to do so, you had a wildcard catch(...) in your code. ")},

        {"const1":    ("Good use of the const keyword for variables",                                         4, "In terms of using const for non-modifiable variables and references, you've used this well. "),
         "const2":    ("Could have used more instances of the const keyword with variables",                  2, "In terms of using const for non-modifiable variables and references, there are a few places where you could have used this where you did not. Using const whereever you will not be modifying a value or rely upon a variable to not change is good practice. "),
         "const3":    ("Little use of the const keyword with variables",                                      1, "In terms of using const for non-modifiable variables and references, there are a few places where you could have used this where you did not. Using const whereever you will not be modifying a value or rely upon a variable to not change is good practice. "),
         "const4":    ("No use of the const keyword with variables",                                          0, "You don't seem to have used const in any significant way in your coursework. Using const whereever you will not be modifying a value or rely upon a variable to not change is good practice. ")},

        {"ref1":      ("Pass-by-reference where appropriate",                                                 4, "You did use pass-by-reference in many of your functions, which means data is not needlessly copied around in your code. Keep it up :)\n\n"),
         "ref2":      ("Could have used more instances of pass-by-reference",                                 2, "You did use pass-by-reference in some of your functions, which means data is not needlessly copied around in your code. There are a few more places where you could have done this though.\n\n"),
         "ref3":      ("Little to no use of pass-by-reference",                                               0, "You didn't really use much pass-by-reference in your code, which means data ends up being needlessly copied around in your code. In future, think about whether a function needs a copy of a variable, or can rely upon a reference to the original variable.\n\n")},

        {"const1":    ("Function declarations are perfect (e.g. const, noexcept, reference)",                 4, "Your function declarations are perfect. Continue to always program with the use of const, noexcept, and reference/value types is needed. "),
         "const2":    ("Could have used more instances of the const keyword",                                 2, "Your function declarations are close to perfect, but you should always think about the use of const, noexcept, and reference/value types. "),
         "const3":    ("Little use of the const keyword in fuction declarations",                             0, "Quite a few of your function declarations have issues. You should always think about the use of const, noexcept, and reference/value types. ")},

        {"redund1":   ("No redundant or repeated code",                                                       3, "You've also managed to avoid redundant/repeated code, which is always a bonus.\n\n"),
         "redund2":   ("Some redundant or repeated code (e.g. could have been new functions)",                2, "You've included some instances of redundant/repeated code which could have been made more efficient (e.g. by moving them into separate functions).\n\n"),
         "redund3":   ("Quite a bit of redundant or repeated code",                                           0, "There's a fair few instances of redundant/repeated code which could have been made more efficient (e.g. by moving them into separate functions).\n\n")},

        {"overall1":  ("Overall, this is an excellent coursework (quality, not completeness)",                0, "SUMMARY\nOverall, this is an excellent coursework. You have produced some great code. Well done!"),
         "overall2":  ("Overall, this is a good coursework (quality, not completeness)",                      0, "SUMMARY\nOverall, this is an good coursework. You have produced some nice code, but there is some room for improvement. That said, you still did very well!"),
         "overall3":  ("Overall, this is an ok coursework (quality, not completeness)",                       0, "SUMMARY\nOverall, this is an good attempt. You have produced some OK code, but there a few areas where you could have improved. Use the feedback to re-examine and reflect upon your code."),
         "overall4":  ("Overall, this is a poor coursework (quality, not completeness)",                      0, "SUMMARY\nOverall, there is quite a bit of scope for improvement. Much of this coursework's marks were achievable without completing all the tasks. Focusing on delivering good, but perhaps, incomplete code would have helped you achieve a higher mark.")}]

    return stage_result(
      updated_label = "Marking finished",
      decision      = multidecision,
      next_stage    = None)


  def feedback(student_id, marks, feedback):
      pass