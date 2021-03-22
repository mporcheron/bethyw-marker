
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

  def __init__(self, autograder_file, submissions_dir, student_id):
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
    self.progress["setup"]                   = stage("Copy student's submission into temporary marking directory", coursework.setup)
    self.progress["readme"]                  = stage("Read the student's README",                                  coursework.readme)
    self.progress["autograder"]              = stage("Parse autograder output",                                    coursework.autograder)
    self.progress["opensrc"]                 = stage("Begin reading through the student's code",                   coursework.opensrc)
    self.progress["negative_marking_switch"] = stage("Swap to negative marking from here on in",                   coursework.negative_marking_switch)
    self.progress["tables_output"]           = stage("Check the tables output for style",                          coursework.tables_output)
    self.progress["memtest"]                 = stage("Run the coursework with Valgrind",                           coursework.memtest)
    self.progress["input_source"]            = stage("Check InputSource and InputFile have virtual functions",     coursework.input_source)
    self.progress["function_ordering"]       = stage("Check that they have retained the ordering of functions",    coursework.function_ordering)
    self.progress["not_const_functions"]     = stage("Check that the right functions are const",                   coursework.not_const_functions)
    self.progress["aggressive_warnings"]     = stage("Use GCC to test code quality with some aggressive warnings", coursework.aggressive_warnings)
    self.progress["code_style"]              = stage("Evaluate the coding style",                                  coursework.code_style)
    self.progress["extra_features"]          = stage("Add marks for extra features",                               coursework.extra_features)
    self.progress["exceptions"]              = stage("Check their exception handling",                             coursework.exceptions)
    self.progress["code_efficiency"]         = stage("Evaluate the coding style",                                  coursework.code_efficiency)
    self.progress["feedback"]                = stage("Modify the feedback",                                        coursework.feedback)

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
    self.refresh_body()

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
    # self.refresh_body()

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

    self.refresh_body()
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
      if stage_result.student_feedback is not None:
        self.feedback                              = stage_result.student_feedback

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
               student_feedback = None,  # replace student feedback with this
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
  GPP_COMMAND      = 'g++-10'
  CATCH2_EXE       = os.getcwd() + "/_bin/catch.o"
  MARKS_DIR        = os.getcwd() + "/_marks"
  ORIG_SRC_DIR     = os.getcwd() + "/_origsrc"
  TEST_SRC_DIR     = os.getcwd() + "/_tempsrc"
  SUBMISSIONS_DIR  = os.getcwd() + "/submissions"

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
    # delete any previous data from the temp directory and reset it
    try:
      coursework.__rmdir(coursework.TEST_SRC_DIR)
    except FileNotFoundError:
      pass

    shutil.copytree(coursework.ORIG_SRC_DIR, coursework.TEST_SRC_DIR)


    # copy files from student's source directory
    source_directory = coursework.SUBMISSIONS_DIR + "/" + student_id

    try:
      coursework.__rmdir(source_directory + "/bin")
    except FileNotFoundError:
      pass

    for src_dir, dirs, files in os.walk(source_directory):
      dst_dir = src_dir.replace(source_directory, coursework.TEST_SRC_DIR, 1)

      if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

      for file in files:
        src_file = os.path.join(src_dir, file)
        dst_file = os.path.join(dst_dir, file)
        shutil.copy(src_file, dst_file)

    return stage_result(
      updated_label = "Student files successfully copied into temporary marking directory",
      next_stage    = "readme")


  def readme(student_id, marks, feedback):
    if not os.path.isfile(coursework.TEST_SRC_DIR + "/README.md"):
      return stage_result(
        updated_label = "No README.md included",
        next_stage    = "autograder")

    with open(coursework.TEST_SRC_DIR + "/README.md", "r") as f:
      contents = f.read()

    return stage_result(
      updated_label = "README.md included and opened",
      view_text     = ("README.md", contents),
      next_stage    = "autograder")

        

  def autograder(student_id, marks, feedback):
    if not os.path.isfile(marker.AUTOGRADER_FILE):
      return stage_result(
        updated_label = "Could not load autograder results from " + marker.AUTOGRADER_FILE,
        next_stage    = None)

    key = student_id + "@Swansea.ac.uk"

    df = pd.read_csv(marker.AUTOGRADER_FILE)
    df = df.set_index('Username')
    
    output = "output"
    catch2 = "catch2"
    provided = "provided"
    extended = "extended"
    
    test = {"output": {"provided": {}, "extended" : {}}, "catch2" : {"provided": {}, "extended" : {}}}

    test[output][provided]["T"]  = "Output tests Total"
    test[output][provided]["W"]  = "Output tests - Compilation completed without warnings"
    test[output][provided]["01"] = "Output tests - Output 1: bethyw -d invalidataset"
    test[output][provided]["02"] = "Output tests - Output 2: bethyw --dir invalidir"
    test[output][provided]["03"] = "Output tests - Output 3: bethyw -a doesnotexist -j"
    test[output][provided]["04"] = "Output tests - Output 4: bethyw -d popden"
    test[output][provided]["05"] = "Output tests - Output 5: bethyw -d popden -j"
    test[output][provided]["06"] = "Output tests - Output 6: bethyw -d biz -j"
    test[output][provided]["07"] = "Output tests - Output 7: bethyw -d aqi -j"
    test[output][provided]["08"] = "Output tests - Output 8: bethyw -d trains -j"
    test[output][provided]["09"] = "Output tests - Output 9: bethyw -d complete-popden -j"
    test[output][provided]["10"] = "Output tests - Output 10: bethyw -d complete-pop -a W06000024 -m area"

    test[catch2][provided]["T"]  = "Provided Catch2 unit tests Total"
    test[catch2][provided]["01"] = "Provided Catch2 unit tests - Test 1: The --datasets program argument can be parsed as a list of datasets to import"
    test[catch2][provided]["02"] = "Provided Catch2 unit tests - Test 2: The --areas program argument can be parsed correctly, whether it is a single area's code, a comma-separated list of codes, contains 'all' as a value, or is missing; and a filter list generated"
    test[catch2][provided]["03"] = "Provided Catch2 unit tests - Test 3: The --measures program argument can be parsed correctly, whether it is a single measure's codename, a comma-separated list of codenames, contains 'all' as a value, or is missing"
    test[catch2][provided]["04"] = "Provided Catch2 unit tests - Test 4: The --years program argument can be parsed correctly, whether it is a equal to single four-digit year, two four-digit years separated by a hyphen, '0', '0-0', or invalid due to the presence of non-numerical values"
    test[catch2][provided]["05"] = "Provided Catch2 unit tests - Test 5: When given a path to a dataset file, an InputFile object is constructed and can return a reference to a stream if it is a valid path"
    test[catch2][provided]["06"] = "Provided Catch2 unit tests - Test 6: A Measure object can be constructed in your coursework, where the constructor is given an std::string codename (which is converted to lowercase) and label, with a default size of 0"
    test[catch2][provided]["07"] = "Provided Catch2 unit tests - Test 7: A Measure object can be populated with values, with the Measure object not allowing more than one value per year, and retrieving a non-existent value will throw an exception"
    test[catch2][provided]["08"] = "Provided Catch2 unit tests - Test 8: An Area instance can be constructed with a local authority code and contain multiple names in different languages, identified by three-letter code"
    test[catch2][provided]["09"] = "Provided Catch2 unit tests - Test 9: An Area instance can contain Measure instances and return values, and cannot contain two Measure instances with the same codename"
    test[catch2][provided]["10"] = "Provided Catch2 unit tests - Test 10: An Areas instance can be constructed populated with Area instances, and cannot contain two Area instances with the same local authority code"
    test[catch2][provided]["11"] = "Provided Catch2 unit tests - Test 11: The dataset areas.csv can be correctly parsed by your code in Areas::populateFromAuthorityCodeCSV()"
    test[catch2][provided]["12"] = "Provided Catch2 unit tests - Test 12: The dataset popu1009.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()"

    test[output][extended]["T"]   = "Extended output tests Total"
    test[output][extended]["01"]  = "Extended output tests - Unseen output 1: bethyw -a W060000999 -y 0 -m rb,db,all -j"
    test[output][extended]["02"]  = "Extended output tests - Unseen output 2: bethyw -a swan -m RAIL"
    test[output][extended]["02a"] = "Extended output tests - Unseen output 2a: bethyw -a swan -m RAIL"
    test[output][extended]["03"]  = "Extended output tests - Unseen output 3: bethyw -d popden -a swan -m RAIL"
    test[output][extended]["04"]  = "Extended output tests - Unseen output 4: bethyw -d popden -a Abertawe,Swansea "
    test[output][extended]["05"]  = "Extended output tests - Unseen output 5: bethyw -a swan,card -m pop,rail -y 2010-2018 -j"
    test[output][extended]["05a"] = "Extended output tests - Unseen output 5a: bethyw -a swan,card -m pop,rail -y 2010-2018 -j"
    test[output][extended]["06"]  = "Extended output tests - Unseen output 6: bethyw -a W06000015,W06000011 -y 2015 -j"
    test[output][extended]["06a"] = "Extended output tests - Unseen output 6a: bethyw -a W06000015,W06000011 -y 2015 -j"

    test[catch2][extended]["T"]   = "Extended Catch2 unit tests Total"
    test[catch2][extended]["01"]  = "Extended Catch2 unit tests - Unseen test 1: The --years program argument throws the correct exception is an incorrect length (e.g. two digits)"
    test[catch2][extended]["02"]  = "Extended Catch2 unit tests - Unseen test 2: A Measure object will replace an existing value when given a new value for an existing year"
    test[catch2][extended]["03"]  = "Extended Catch2 unit tests - Unseen test 3: An Areas instance will merge two Area instances and the names of the second Area instances will overwrite the first"
    test[catch2][extended]["04"]  = "Extended Catch2 unit tests - Unseen test 4: An Area instance will merge in values when given a Measure with the name matching the original"
    test[catch2][extended]["05"]  = "Extended Catch2 unit tests - Unseen test 5: Measure codenames are imported and converted to lowercase when populated from a dataset stream"
    test[catch2][extended]["06"]  = "Extended Catch2 unit tests - Unseen test 6: The requested statistics (difference, difference as percentage, and mean) can be correctly calculated from the imported data"
    test[catch2][extended]["07"]  = "Extended Catch2 unit tests - Unseen test 7: The dataset econ0080.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()"
    test[catch2][extended]["08"]  = "Extended Catch2 unit tests - Unseen test 8: The dataset envi0201.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()"
    test[catch2][extended]["09"]  = "Extended Catch2 unit tests - Unseen test 9: The dataset tran0152.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()"
    test[catch2][extended]["10"]  = "Extended Catch2 unit tests - Unseen test 10: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()"
    test[catch2][extended]["10a"] = "Extended Catch2 unit tests - Unseen test 10a: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()"
    test[catch2][extended]["11"]  = "Extended Catch2 unit tests - Unseen test 11: An Area instance throws an exception when given a non-three alphabetical character language code "
    test[catch2][extended]["12"]  = "Extended Catch2 unit tests - Unseen test 12: The program arugments work with a case-insensitive ALL value"



    try:
      autograder_marks = df.loc[key].copy()

      # FIX DUPLICATE TESTS (DUE TO POOR COURSEWORK DESIGN)
      autograder_marks["Total Points Possible"] = int(autograder_marks["Total Points Possible"]) - 5
      autograder_marks["Extended output tests Total Possible"] = int(autograder_marks["Extended output tests Total Possible"]) - 3
      autograder_marks["Extended Catch2 unit tests Total Possible"] = int(autograder_marks["Extended Catch2 unit tests Total Possible"]) - 2
    
      feedback += "1. SUMMARY OF AUTOMATED MARKING (" + str(autograder_marks["Total Points"]) + "/" + str(autograder_marks["Total Points Possible"]) + ")\n"
      if autograder_marks[test[output][provided]["W"]] == 0:
        feedback += "It looks like your code has some warnings or errors from the compiler (" + str(autograder_marks[test[output][provided]["W"]]) + "/2)? You should aim to always produce code that has no warnings or errors, even if it is incomplete and does not implement all the functionality. This was a relatively easy area to pick up 2 marks (i.e. the code you were given compiles without warnings already). You were able to test your output using the CS Autograder, which displayed this feedback to you.\n\n"
      else:
        feedback += "Your code compiled without issuing any warnings (" + str(autograder_marks[test[output][provided]["W"]]) + "/2), even with all the extra options enabled—this is great! You should never be submitting code with errors or warnings, even if the code is incomplete.\n\n"

      if autograder_marks[test[catch2][provided]["T"]] == 0:
        feedback += "It seems your code failed to pass any of the provided Catch2 tests (" + str(autograder_marks["Provided Catch2 unit tests Total"]) + "/" + str(autograder_marks["Provided Catch2 unit tests Total Possible"]) + "). You were advised to make sure you passed these tests. "
        if autograder_marks[test[catch2][extended]["T"]] == 0:
          feedback += "Your also scored " + str(autograder_marks["Extended Catch2 unit tests Total"]) + "/" + str(autograder_marks["Extended Catch2 unit tests Total Possible"]) + " on the additional Catch2 tests I performed, testing many more edge cases in your code. "
        feedback += "Although there are an infinite number of ways to implement this coursework, you were specifically asked to implement functions in a given way. In future, I recommend you read coursework specifications more closely to understand what is asked of you.  "
      elif autograder_marks[test[catch2][provided]["T"]] < 10:
        feedback += "You code passed less than 50% of the provided Catch2 tests  (" + str(autograder_marks["Provided Catch2 unit tests Total"]) + "/" + str(autograder_marks["Provided Catch2 unit tests Total Possible"]) + "). You were advised to make sure you passed these tests, and so it is a shame to see that you did not manage to score well here. You had local copies of these tests and could have examined their source closely to work out how to make sure your code complied with them. "
      elif autograder_marks[test[catch2][provided]["T"]] < 20:
        feedback += "You code passed most of the provided Catch2 tests  (" + str(autograder_marks["Provided Catch2 unit tests Total"]) + "/" + str(autograder_marks["Provided Catch2 unit tests Total Possible"]) + "). These were designed to test the basic implementation of your program in response to the test files. These were easy points to score, so it is a shame you didn't quite get full marks here. "
      else:
        feedback += "You passed all the provided Catch2 tests, scoring all " + str(autograder_marks["Provided Catch2 unit tests Total"]) + " marks possible. "

      if autograder_marks[test[catch2][extended]["T"]] < 11:
        feedback += "With the additional Catch2 tests designed to test the edge cases and advanced parts of the coursework, your code scored less than 50% of the marks (" + str(autograder_marks["Extended Catch2 unit tests Total"]) + "/" + str(autograder_marks["Extended Catch2 unit tests Total Possible"]) + "). These tests were designed to be challenging, so this is still a good result.\n\n"
      elif autograder_marks[test[catch2][extended]["T"]] < 22:
        feedback += "With the additional Catch2 tests designed to test the edge cases and advanced parts of the coursework, your code passed most of the tests (" + str(autograder_marks["Extended Catch2 unit tests Total"]) + "/" + str(autograder_marks["Extended Catch2 unit tests Total Possible"]) + "), which given these tests were designed to be challenging, is a great result.\n\n"
      elif autograder_marks[test[catch2][extended]["T"]] == 22:
        feedback += "Your code passed ALL of the additional Catch2 tests (" + str(autograder_marks["Extended Catch2 unit tests Total"]) + "/" + str(autograder_marks["Extended Catch2 unit tests Total Possible"]) + ") designed to test the edge cases and advanced parts of the coursework, which is an excellent outcome and demonstrates some fantastic programming skills.\n\n"
        
      if autograder_marks['Output tests Total'] == 0:
        feedback += "It seems your code failed to pass any of the output tests (" + str(autograder_marks["Output tests Total"] - autograder_marks[test[output][provided]["W"]]) + "/" + str(autograder_marks["Output tests Total Possible"] - autograder_marks[test[output][provided]["W"]]) + "). For this coursework you were given a specification and expected to program towards it. These tests were all available on the CS Autograder. The system was configured to provide the output of your program and the expected output to help you with your development. You were advised to make sure you passed these tests. "
      elif autograder_marks['Output tests Total'] - autograder_marks['Output tests - Compilation completed without warnings'] < 5:
        feedback += "You code passed less than 50% of the provided output tests (" + str(autograder_marks["Output tests Total"] - autograder_marks[test[output][provided]["W"]]) + "/" + str(autograder_marks["Output tests Total Possible"] - autograder_marks[test[output][provided]["W"]]) + "). The system was configured to provide the output of your program and the expected output to help you with your developed. You were advised to make sure you passed these tests, and so it is a shame to see that you did not manage to score well in this section. "
      elif autograder_marks['Output tests Total'] - autograder_marks['Output tests - Compilation completed without warnings'] < 10:
        feedback += "You code passed most of the provided output tests (" + str(autograder_marks["Output tests Total"] - autograder_marks[test[output][provided]["W"]]) + "/" + str(autograder_marks["Output tests Total Possible"] - autograder_marks[test[output][provided]["W"]]) + "). These were designed to test the basic output of your program in response to the commands, and the CS Autograder was configured to provide you with the expected output as well as the output from your program. These were easy points to score, so it is a shame you didn't quite get full marks here. "
      else:
        feedback += "You passed all the provided output tests, scoring " + str(autograder_marks["Output tests Total"] - autograder_marks[test[output][provided]["W"]]) + "/" + str(autograder_marks["Output tests Total Possible"] - autograder_marks[test[output][provided]["W"]]) + " marks possible. These were designed to test the basic output of your program in response to the commands. "

      if autograder_marks['Extended output tests Total'] == 0:
        feedback += "I also ran your code against some additional output tests, although your program sadly scored " + str(autograder_marks["Extended output tests Total"]) + "/" + str(autograder_marks["Extended output tests Total Possible"]) + " against these tests.\n\n"
      elif autograder_marks['Extended output tests Total'] < 3:
        feedback += "I also ran your code against some additional output tests. Your code passed less than 50% of these tests (" + str(autograder_marks["Extended output tests Total"]) + "/" + str(autograder_marks["Extended output tests Total Possible"]) + "), which is a little disappointing although these tests were designed to exploit the edge cases that you may not have considered thus scoring high here was challenging. To score better marks here, you should have attempted to run your program various different arguments and reasoned about the outputs of your program.\n\n"
      elif autograder_marks['Extended output tests Total'] < 6:
        feedback += "I also ran your code against some additional output tests. Your code passed most of these tests (" + str(autograder_marks["Extended output tests Total"]) + "/" + str(autograder_marks["Extended output tests Total Possible"]) + "), which is a great outcome as these tests were designed to exploit the edge cases in your data thus scoring high here was challenging.\n\n"
      else:
        feedback += "I also ran your code against some additional output tests and your code passed all of these (" + str(autograder_marks["Extended output tests Total"]) + "/" + str(autograder_marks["Extended output tests Total Possible"]) + "), which is a fantastic outcome, and showed that you did a very thorough job following the coursework specification.\n\n"




      # TASK 2
      task2marks    = int(autograder_marks[test[catch2][provided]["01"]] + autograder_marks[test[catch2][provided]["02"]] + autograder_marks[test[catch2][provided]["03"]] + autograder_marks[test[catch2][provided]["04"]] + autograder_marks[test[catch2][extended]["12"]] + autograder_marks[test[output][provided]["01"]] + autograder_marks[test[output][provided]["02"]])
      task2possible =                                                  1 +                                              1 +                                              1 +                                              1 +                                              2 +                                              1 +                                              1 
      feedback += "Below is a summary of the various tasks, as organised by the coursework worksheet. Note that the marks given below are the same marks as given above but categorised by task rather than test type. For deciding the weighting of each test (i.e., number of marks), each test was assessed for its relative difficulty based on the module content and how much work was involved.\n\n1.1. TASK 2: IMPLEMENT PROGRAM ARGUMENT PARSING FUNCTIONS (" + str(task2marks) + "/" + str(task2possible) + ")\n"
      if autograder_marks[test[catch2][provided]["01"]] > 0 and \
         autograder_marks[test[catch2][provided]["02"]] > 0 and \
         autograder_marks[test[catch2][provided]["03"]] > 0 and \
         autograder_marks[test[catch2][provided]["04"]] > 0:

          feedback += "Your code correctly passed all four of the provided test suites (tests 1–4) that covered the four program arguments: datasets, areas, measures, and years. "

          if autograder_marks[test[catch2][extended]["01"]] > 0:
            feedback += "As a sign of your good programming, your code also correctly throws an exception when a provided with numbers of an incorrect length—this wasn't covered in the provided unit tests, although was expected as per the description of the function in bethyw.cpp.\n\n"
          else:
            feedback += "However, your code sadly does not throw an exception when a provided with year values of an incorrect length (e.g., 20). This wasn't covered in the provided unit tests, although was expected as per the description of the function.\n\n"
      else:
        if autograder_marks[test[catch2][provided]["01"]] > 0:
          feedback += "Your code correctly parses the datasets program argument in the BethYw::parseDatasetsArg() function, as per the test suite in test1.cpp. "

          if autograder_marks[test[catch2][provided]["02"]] > 0:
            feedback += "Likewise, it also parses the areas argument correctly, whether it is a single area\'s code, a comma-separated list of codes, contains \'all\' as a value, or is missing; and a filter list generated (test2.cpp). "

            if autograder_marks[test[catch2][provided]["03"]] > 0:
              feedback += "The measures program argument is parsed correctly in the BethYw::parseMeasuresArg() function, whether it is a single measure\'s codename, a comma-separated list of codenames, contains \'all\' as a value, or is missing (test3.cpp). "
            else:
              feedback += "However, your code doesn't seem to work properly with the measures program argument in the BethYw::parseMeasuresArg() function (test3.cpp). "
            
          else:
            feedback += "Sadly, though, it does not correctly parse the areas program argument in the BethYw::parseAreasArg() function "

          if autograder_marks[test[catch2][provided]["03"]] > 0:
            feedback += "as covered in test2.cpp. The measures program argument is parsed correctly in the BethYw::parseMeasuresArg() function though, whether it is a single measure\'s codename, a comma-separated list of codenames, contains \'all\' as a value, or is missing (test3.cpp). "
          else:
            feedback += "or the measures program argument in the BethYw::parseMeasuresArg() function. These were covered in test2.cpp and test3.cpp. "
          
        else:

          feedback += "Your code does not seem to correctly parse the datasets program argument in the BethYw::parseDatasetsArg() function, as per the test suite in test1.cpp. "

          if autograder_marks[test[catch2][provided]["02"]] > 0:
            feedback += "However, it does parse the areas argument correctly, whether it is a single area\'s code, a comma-separated list of codes, contains \'all\' as a value, or is missing; and a filter list generated (test2.cpp). "

            if autograder_marks[test[catch2][provided]["03"]] > 0:
              feedback += "The measures program argument is also parsed correctly in the BethYw::parseMeasuresArg() function, whether it is a single measure\'s codename, a comma-separated list of codenames, contains \'all\' as a value, or is missing (test3.cpp) "
            else:
              feedback += "It seems though that it doesn't work properly with the measures program argument in the BethYw::parseMeasuresArg() function (test3.cpp). "
            
          else:
            feedback += "Sadly, it also does not correctly parse the areas program argument in the BethYw::parseAreasArg() function "

          if autograder_marks[test[catch2][provided]["03"]] > 0:
            feedback += "as covered in test2.cpp. The measures program argument is parsed correctly in the BethYw::parseMeasuresArg() function though, whether it is a single measure\'s codename, a comma-separated list of codenames, contains \'all\' as a value, or is missing (test3.cpp). "
          else:
            feedback += "or the measures program argument in the BethYw::parseMeasuresArg() function. These were covered in test2.cpp and test3.cpp. "
          
        if autograder_marks[test[catch2][provided]["04"]] > 0:
          feedback += "Your code correctly parses the years program argument in the BethYw::parseYearsArg() function, whether it is a equal to single four-digit year, two four-digit years separated by a hyphen, \'0\', \'0-0\', or invalid due to the presence of non-numerical values (test4.cpp). "
          if autograder_marks[test[catch2][extended]["01"]] > 0:
            feedback += "Your code even threw an exception when the years argument was a number but was not four digits long, which was specified in the block comment but no provided test covered this edge case. "
          else:
            feedback += "That said, your code didn't seem to throw the correct exception when the years argument was a number of incorrect length (this was described as the expected outcome in the block comment, but was not an edge case covered in the provided test suite). "
        else:
          if autograder_marks[test[catch2][extended]["01"]] > 0:
            feedback += "Your code did not seem to correctly parse the years program argument in the BethYw::parseYearsArg() function (test4.cpp), although it did throw an exception when the years argument was a number of incorrect length (which was one of the hidden tests). "
          else:
            feedback += "Your code did not seem to correctly parse the years program argument in the BethYw::parseYearsArg() function (test4.cpp)—additionally one the hidden tests covered whether it threw an exception when given a non-four digit number (which your code also did not pass). "

      if autograder_marks[test[catch2][extended]["12"]] > 0:
        feedback += "Your code also allowed for the 'all' value in any case with the datasets, areas, and measures program argument—there was a hidden test to determine this."
      else:
        feedback += "The various block comments in bethyw.cpp for processing the datasets, areas, and measures program argument required that you to look for the 'all' value in a case-insensitive way, but your code did not seemingly do this for all four of the arguments (a single test covered all four here so you may have to inspect your code to determine why you failed this test)."

      feedback += "\n\nI also tested your code with some outputs, corresponding to this task. "

      if autograder_marks[test[output][provided]["01"]] > 0:
        feedback += "Your compiled program produced the output 'No dataset matches key: <invalid dataset>' to standard error (stderr) when given an invalid dataset as a program argument. "

        if autograder_marks[test[output][provided]["02"]] > 0:
          feedback += "Your program also produced the correct output of 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets.\n\n"
        else:
          feedback += "However, your program did not output 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets. This should have been a combination of the exception message thrown by InputFile::open() in input.cpp and the prepending error message as stated in BethYw::loadDatasets() in bethyw.cpp. When working in large systems with multiple teams, it may be necessary for your code to give exact outputs to support system interoperability. You could have verified this by checking your program against the sample output in the second output file.\n\n"
        
      else:
        feedback += "Your code did not output 'No dataset matches key: <invalid dataset>' to standard error (stderr) when given an invalid dataset as a program argument. This was stated in the block comment for BethYw::parseDatasetsArg() in bethyw.cpp and was shown in the output 1 test file. "

        if autograder_marks[test[output][provided]["02"]] > 0:
          feedback += "However, it did correctly output 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets.\n\n"
        else:
          feedback += "It also did not output 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets. This should have been a combination of the exception message thrown by InputFile::open() in input.cpp and the prepending error message as stated in BethYw::loadDatasets() in bethyw.cpp. When working in large systems with multiple teams, it may be necessary for your code to give exact outputs to support system interoperability. You could have verified this by checking your program against the sample output in the second output file.\n\n"





      # TASK 3
      task3marks    = int(autograder_marks[test[catch2][provided]["05"]] + autograder_marks[test[catch2][provided]["08"]] + autograder_marks[test[catch2][extended]["11"]] + autograder_marks[test[catch2][provided]["10"]] + autograder_marks[test[catch2][provided]["11"]])
      task3possible =                                                  2 +                                              2 +                                              2 +                                              2 +                                              2

      feedback += "1.2. TASK 3: IMPLEMENT populateFromAuthorityCodeCSV PARSING (" + str(task3marks) + "/" + str(task3possible) + ")\n"
      if autograder_marks[test[catch2][provided]["05"]] > 0:
        feedback += "Firstly, your InputSource and InputFile classes work as expected according to the test suite (test5.cpp). "
      else:
        feedback += "Firstly, your InputSource and InputFile classes don't seem to work fully—either not returning a stream when given a valid filepath or not throwing an exception when given an invalid filepath (this was tested in test5.cpp). "

      if autograder_marks[test[catch2][provided]["08"]] > 0:
        feedback += "For this task, you had to implement the Area class to support names in multiple languages and local authority codes. Here your code passed the tests (test8.cpp). "
        if autograder_marks[test[catch2][extended]["11"]] > 0:
          feedback += "A hidden test verified that your code also threw an exception when given an invalid language code for a name. "
        else:
          feedback += "However, your code failed a hidden test to determine if your program throws an exception when given an invalid language code for a name, as requested in the provided framework. "
      else:
        feedback += "For this task, you had to implement the Area class to support names in multiple languages and local authority codes but it seems your code does not pass the basic tests for this class (test8.cpp). "
        if autograder_marks[test[catch2][extended]["11"]] > 0:
          feedback += "However, a hidden test verified that your code threw an exception when given an invalid language code for a name. "
        else:
          feedback += "Additionally, your code failed a hidden test to determine if your program throws an exception when given an invalid language code for a name, as requested in the provided framework. "

      if autograder_marks[test[catch2][provided]["10"]] > 0:
        feedback += "\n\nYou also had to implement—at least partially—the Areas class to allow it to contain Area instances and here your code passed the tests (test10.cpp). "
      else:
        feedback += "\n\nYou also had to implement—at least partially—the Areas class to allow it to contain Area instances, but sadly your code did not pass the requisite tests (test10.cpp). "

      if autograder_marks[test[catch2][provided]["11"]] > 0:
        feedback += "When testing your code with a fresh copy of areas.csv, everything seemed to work nicely (test11.cpp).\n\n"
      else:
        feedback += "When testing your code with a fresh copy of areas.csv, the data did not get imported correctly as I expected (test11.cpp). Did you verify if this worked correctly on your local machine?\n\n"


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

  def __init__(self, autograder_file, submissions_dir, student_id):
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
    self.progress["setup"]                   = stage("Copy student's submission into temporary marking directory", coursework.setup)
    self.progress["readme"]                  = stage("Read the student's README",                                  coursework.readme)
    self.progress["autograder"]              = stage("Parse autograder output",                                    coursework.autograder)
    self.progress["opensrc"]                 = stage("Begin reading through the student's code",                   coursework.opensrc)
    self.progress["negative_marking_switch"] = stage("Swap to negative marking from here on in",                   coursework.negative_marking_switch)
    self.progress["tables_output"]           = stage("Check the tables output for style",                          coursework.tables_output)
    self.progress["memtest"]                 = stage("Run the coursework with Valgrind",                           coursework.memtest)
    self.progress["input_source"]            = stage("Check InputSource and InputFile have virtual functions",     coursework.input_source)
    self.progress["function_ordering"]       = stage("Check that they have retained the ordering of functions",    coursework.function_ordering)
    self.progress["not_const_functions"]     = stage("Check that the right functions are const",                   coursework.not_const_functions)
    self.progress["aggressive_warnings"]     = stage("Use GCC to test code quality with some aggressive warnings", coursework.aggressive_warnings)
    self.progress["code_style"]              = stage("Evaluate the coding style",                                  coursework.code_style)
    self.progress["extra_features"]          = stage("Add marks for extra features",                               coursework.extra_features)
    self.progress["exceptions"]              = stage("Check their exception handling",                             coursework.exceptions)
    self.progress["code_efficiency"]         = stage("Evaluate the coding style",                                  coursework.code_efficiency)
    self.progress["feedback"]                = stage("Modify the feedback",                                        coursework.feedback)

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
    self.refresh_body()

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
    # self.refresh_body()

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

    self.refresh_body()
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
      if stage_result.student_feedback is not None:
        self.feedback                              = stage_result.student_feedback

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
               student_feedback = None,  # replace student feedback with this
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
  GPP_COMMAND      = 'g++-10'
  CATCH2_EXE       = os.getcwd() + "/_bin/catch.o"
  MARKS_DIR        = os.getcwd() + "/_marks"
  ORIG_SRC_DIR     = os.getcwd() + "/_origsrc"
  TEST_SRC_DIR     = os.getcwd() + "/_tempsrc"
  SUBMISSIONS_DIR  = os.getcwd() + "/submissions"

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
    # delete any previous data from the temp directory and reset it
    try:
      coursework.__rmdir(coursework.TEST_SRC_DIR)
    except FileNotFoundError:
      pass

    shutil.copytree(coursework.ORIG_SRC_DIR, coursework.TEST_SRC_DIR)


    # copy files from student's source directory
    source_directory = coursework.SUBMISSIONS_DIR + "/" + student_id

    try:
      coursework.__rmdir(source_directory + "/bin")
    except FileNotFoundError:
      pass

    for src_dir, dirs, files in os.walk(source_directory):
      dst_dir = src_dir.replace(source_directory, coursework.TEST_SRC_DIR, 1)

      if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

      for file in files:
        src_file = os.path.join(src_dir, file)
        dst_file = os.path.join(dst_dir, file)
        shutil.copy(src_file, dst_file)

    return stage_result(
      updated_label = "Student files successfully copied into temporary marking directory",
      next_stage    = "readme")


  def readme(student_id, marks, feedback):
    if not os.path.isfile(coursework.TEST_SRC_DIR + "/README.md"):
      return stage_result(
        updated_label = "No README.md included",
        next_stage    = "autograder")

    with open(coursework.TEST_SRC_DIR + "/README.md", "r") as f:
      contents = f.read()

    return stage_result(
      updated_label = "README.md included and opened",
      view_text     = ("README.md", contents),
      next_stage    = "autograder")

        

  def autograder(student_id, marks, feedback):
    if not os.path.isfile(marker.AUTOGRADER_FILE):
      return stage_result(
        updated_label = "Could not load autograder results from " + marker.AUTOGRADER_FILE,
        next_stage    = None)

    key = student_id + "@Swansea.ac.uk"

    df = pd.read_csv(marker.AUTOGRADER_FILE)
    df = df.set_index('Username')
    
    output = "output"
    catch2 = "catch2"
    provided = "provided"
    extended = "extended"
    
    test = {"output": {"provided": {}, "extended" : {}}, "catch2" : {"provided": {}, "extended" : {}}}

    test[output][provided]["T"]  = "Output tests Total"
    test[output][provided]["W"]  = "Output tests - Compilation completed without warnings"
    test[output][provided]["01"] = "Output tests - Output 1: bethyw -d invalidataset"
    test[output][provided]["02"] = "Output tests - Output 2: bethyw --dir invalidir"
    test[output][provided]["03"] = "Output tests - Output 3: bethyw -a doesnotexist -j"
    test[output][provided]["04"] = "Output tests - Output 4: bethyw -d popden"
    test[output][provided]["05"] = "Output tests - Output 5: bethyw -d popden -j"
    test[output][provided]["06"] = "Output tests - Output 6: bethyw -d biz -j"
    test[output][provided]["07"] = "Output tests - Output 7: bethyw -d aqi -j"
    test[output][provided]["08"] = "Output tests - Output 8: bethyw -d trains -j"
    test[output][provided]["09"] = "Output tests - Output 9: bethyw -d complete-popden -j"
    test[output][provided]["10"] = "Output tests - Output 10: bethyw -d complete-pop -a W06000024 -m area"

    test[catch2][provided]["T"]  = "Provided Catch2 unit tests Total"
    test[catch2][provided]["01"] = "Provided Catch2 unit tests - Test 1: The --datasets program argument can be parsed as a list of datasets to import"
    test[catch2][provided]["02"] = "Provided Catch2 unit tests - Test 2: The --areas program argument can be parsed correctly, whether it is a single area's code, a comma-separated list of codes, contains 'all' as a value, or is missing; and a filter list generated"
    test[catch2][provided]["03"] = "Provided Catch2 unit tests - Test 3: The --measures program argument can be parsed correctly, whether it is a single measure's codename, a comma-separated list of codenames, contains 'all' as a value, or is missing"
    test[catch2][provided]["04"] = "Provided Catch2 unit tests - Test 4: The --years program argument can be parsed correctly, whether it is a equal to single four-digit year, two four-digit years separated by a hyphen, '0', '0-0', or invalid due to the presence of non-numerical values"
    test[catch2][provided]["05"] = "Provided Catch2 unit tests - Test 5: When given a path to a dataset file, an InputFile object is constructed and can return a reference to a stream if it is a valid path"
    test[catch2][provided]["06"] = "Provided Catch2 unit tests - Test 6: A Measure object can be constructed in your coursework, where the constructor is given an std::string codename (which is converted to lowercase) and label, with a default size of 0"
    test[catch2][provided]["07"] = "Provided Catch2 unit tests - Test 7: A Measure object can be populated with values, with the Measure object not allowing more than one value per year, and retrieving a non-existent value will throw an exception"
    test[catch2][provided]["08"] = "Provided Catch2 unit tests - Test 8: An Area instance can be constructed with a local authority code and contain multiple names in different languages, identified by three-letter code"
    test[catch2][provided]["09"] = "Provided Catch2 unit tests - Test 9: An Area instance can contain Measure instances and return values, and cannot contain two Measure instances with the same codename"
    test[catch2][provided]["10"] = "Provided Catch2 unit tests - Test 10: An Areas instance can be constructed populated with Area instances, and cannot contain two Area instances with the same local authority code"
    test[catch2][provided]["11"] = "Provided Catch2 unit tests - Test 11: The dataset areas.csv can be correctly parsed by your code in Areas::populateFromAuthorityCodeCSV()"
    test[catch2][provided]["12"] = "Provided Catch2 unit tests - Test 12: The dataset popu1009.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()"

    test[output][extended]["T"]   = "Extended output tests Total"
    test[output][extended]["01"]  = "Extended output tests - Unseen output 1: bethyw -a W060000999 -y 0 -m rb,db,all -j"
    test[output][extended]["02"]  = "Extended output tests - Unseen output 2: bethyw -a swan -m RAIL"
    test[output][extended]["02a"] = "Extended output tests - Unseen output 2a: bethyw -a swan -m RAIL"
    test[output][extended]["03"]  = "Extended output tests - Unseen output 3: bethyw -d popden -a swan -m RAIL"
    test[output][extended]["04"]  = "Extended output tests - Unseen output 4: bethyw -d popden -a Abertawe,Swansea "
    test[output][extended]["05"]  = "Extended output tests - Unseen output 5: bethyw -a swan,card -m pop,rail -y 2010-2018 -j"
    test[output][extended]["05a"] = "Extended output tests - Unseen output 5a: bethyw -a swan,card -m pop,rail -y 2010-2018 -j"
    test[output][extended]["06"]  = "Extended output tests - Unseen output 6: bethyw -a W06000015,W06000011 -y 2015 -j"
    test[output][extended]["06a"] = "Extended output tests - Unseen output 6a: bethyw -a W06000015,W06000011 -y 2015 -j"

    test[catch2][extended]["T"]   = "Extended Catch2 unit tests Total"
    test[catch2][extended]["01"]  = "Extended Catch2 unit tests - Unseen test 1: The --years program argument throws the correct exception is an incorrect length (e.g. two digits)"
    test[catch2][extended]["02"]  = "Extended Catch2 unit tests - Unseen test 2: A Measure object will replace an existing value when given a new value for an existing year"
    test[catch2][extended]["03"]  = "Extended Catch2 unit tests - Unseen test 3: An Areas instance will merge two Area instances and the names of the second Area instances will overwrite the first"
    test[catch2][extended]["04"]  = "Extended Catch2 unit tests - Unseen test 4: An Area instance will merge in values when given a Measure with the name matching the original"
    test[catch2][extended]["05"]  = "Extended Catch2 unit tests - Unseen test 5: Measure codenames are imported and converted to lowercase when populated from a dataset stream"
    test[catch2][extended]["06"]  = "Extended Catch2 unit tests - Unseen test 6: The requested statistics (difference, difference as percentage, and mean) can be correctly calculated from the imported data"
    test[catch2][extended]["07"]  = "Extended Catch2 unit tests - Unseen test 7: The dataset econ0080.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()"
    test[catch2][extended]["08"]  = "Extended Catch2 unit tests - Unseen test 8: The dataset envi0201.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()"
    test[catch2][extended]["09"]  = "Extended Catch2 unit tests - Unseen test 9: The dataset tran0152.json can be correctly parsed by your code in Areas::populateFromWelshStatsJSON()"
    test[catch2][extended]["10"]  = "Extended Catch2 unit tests - Unseen test 10: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()"
    test[catch2][extended]["10a"] = "Extended Catch2 unit tests - Unseen test 10a: The dataset complete-popu1009-popden.csv can be correctly parsed by your code in Areas::populateFromAuthorityByYearCSV()"
    test[catch2][extended]["11"]  = "Extended Catch2 unit tests - Unseen test 11: An Area instance throws an exception when given a non-three alphabetical character language code "
    test[catch2][extended]["12"]  = "Extended Catch2 unit tests - Unseen test 12: The program arugments work with a case-insensitive ALL value"



    try:
      autograder_marks = df.loc[key].copy()

      # FIX DUPLICATE TESTS (DUE TO POOR COURSEWORK DESIGN)
      autograder_marks["Total Points Possible"] = int(autograder_marks["Total Points Possible"]) - 5
      autograder_marks["Extended output tests Total Possible"] = int(autograder_marks["Extended output tests Total Possible"]) - 3
      autograder_marks["Extended Catch2 unit tests Total Possible"] = int(autograder_marks["Extended Catch2 unit tests Total Possible"]) - 2
    
      feedback += "1. SUMMARY OF AUTOMATED MARKING (" + str(autograder_marks["Total Points"]) + "/" + str(autograder_marks["Total Points Possible"]) + ")\n"
      if autograder_marks[test[output][provided]["W"]] == 0:
        feedback += "It looks like your code has some warnings or errors from the compiler (" + str(autograder_marks[test[output][provided]["W"]]) + "/2)? You should aim to always produce code that has no warnings or errors, even if it is incomplete and does not implement all the functionality. This was a relatively easy area to pick up 2 marks (i.e. the code you were given compiles without warnings already). You were able to test your output using the CS Autograder, which displayed this feedback to you.\n\n"
      else:
        feedback += "Your code compiled without issuing any warnings (" + str(autograder_marks[test[output][provided]["W"]]) + "/2), even with all the extra options enabled—this is great! You should never be submitting code with errors or warnings, even if the code is incomplete.\n\n"

      if autograder_marks[test[catch2][provided]["T"]] == 0:
        feedback += "It seems your code failed to pass any of the provided Catch2 tests (" + str(autograder_marks["Provided Catch2 unit tests Total"]) + "/" + str(autograder_marks["Provided Catch2 unit tests Total Possible"]) + "). You were advised to make sure you passed these tests. "
        if autograder_marks[test[catch2][extended]["T"]] == 0:
          feedback += "Your also scored " + str(autograder_marks["Extended Catch2 unit tests Total"]) + "/" + str(autograder_marks["Extended Catch2 unit tests Total Possible"]) + " on the additional Catch2 tests I performed, testing many more edge cases in your code. "
        feedback += "Although there are an infinite number of ways to implement this coursework, you were specifically asked to implement functions in a given way. In future, I recommend you read coursework specifications more closely to understand what is asked of you.  "
      elif autograder_marks[test[catch2][provided]["T"]] < 10:
        feedback += "You code passed less than 50% of the provided Catch2 tests  (" + str(autograder_marks["Provided Catch2 unit tests Total"]) + "/" + str(autograder_marks["Provided Catch2 unit tests Total Possible"]) + "). You were advised to make sure you passed these tests, and so it is a shame to see that you did not manage to score well here. You had local copies of these tests and could have examined their source closely to work out how to make sure your code complied with them. "
      elif autograder_marks[test[catch2][provided]["T"]] < 20:
        feedback += "You code passed most of the provided Catch2 tests  (" + str(autograder_marks["Provided Catch2 unit tests Total"]) + "/" + str(autograder_marks["Provided Catch2 unit tests Total Possible"]) + "). These were designed to test the basic implementation of your program in response to the test files. These were easy points to score, so it is a shame you didn't quite get full marks here. "
      else:
        feedback += "You passed all the provided Catch2 tests, scoring all " + str(autograder_marks["Provided Catch2 unit tests Total"]) + " marks possible. "

      if autograder_marks[test[catch2][extended]["T"]] < 11:
        feedback += "With the additional Catch2 tests designed to test the edge cases and advanced parts of the coursework, your code scored less than 50% of the marks (" + str(autograder_marks["Extended Catch2 unit tests Total"]) + "/" + str(autograder_marks["Extended Catch2 unit tests Total Possible"]) + "). These tests were designed to be challenging, so this is still a good result.\n\n"
      elif autograder_marks[test[catch2][extended]["T"]] < 22:
        feedback += "With the additional Catch2 tests designed to test the edge cases and advanced parts of the coursework, your code passed most of the tests (" + str(autograder_marks["Extended Catch2 unit tests Total"]) + "/" + str(autograder_marks["Extended Catch2 unit tests Total Possible"]) + "), which given these tests were designed to be challenging, is a great result.\n\n"
      elif autograder_marks[test[catch2][extended]["T"]] == 22:
        feedback += "Your code passed ALL of the additional Catch2 tests (" + str(autograder_marks["Extended Catch2 unit tests Total"]) + "/" + str(autograder_marks["Extended Catch2 unit tests Total Possible"]) + ") designed to test the edge cases and advanced parts of the coursework, which is an excellent outcome and demonstrates some fantastic programming skills.\n\n"
        
      if autograder_marks['Output tests Total'] == 0:
        feedback += "It seems your code failed to pass any of the output tests (" + str(autograder_marks["Output tests Total"] - autograder_marks[test[output][provided]["W"]]) + "/" + str(autograder_marks["Output tests Total Possible"] - autograder_marks[test[output][provided]["W"]]) + "). For this coursework you were given a specification and expected to program towards it. These tests were all available on the CS Autograder. The system was configured to provide the output of your program and the expected output to help you with your development. You were advised to make sure you passed these tests. "
      elif autograder_marks['Output tests Total'] - autograder_marks['Output tests - Compilation completed without warnings'] < 5:
        feedback += "You code passed less than 50% of the provided output tests (" + str(autograder_marks["Output tests Total"] - autograder_marks[test[output][provided]["W"]]) + "/" + str(autograder_marks["Output tests Total Possible"] - autograder_marks[test[output][provided]["W"]]) + "). The system was configured to provide the output of your program and the expected output to help you with your developed. You were advised to make sure you passed these tests, and so it is a shame to see that you did not manage to score well in this section. "
      elif autograder_marks['Output tests Total'] - autograder_marks['Output tests - Compilation completed without warnings'] < 10:
        feedback += "You code passed most of the provided output tests (" + str(autograder_marks["Output tests Total"] - autograder_marks[test[output][provided]["W"]]) + "/" + str(autograder_marks["Output tests Total Possible"] - autograder_marks[test[output][provided]["W"]]) + "). These were designed to test the basic output of your program in response to the commands, and the CS Autograder was configured to provide you with the expected output as well as the output from your program. These were easy points to score, so it is a shame you didn't quite get full marks here. "
      else:
        feedback += "You passed all the provided output tests, scoring " + str(autograder_marks["Output tests Total"] - autograder_marks[test[output][provided]["W"]]) + "/" + str(autograder_marks["Output tests Total Possible"] - autograder_marks[test[output][provided]["W"]]) + " marks possible. These were designed to test the basic output of your program in response to the commands. "

      if autograder_marks['Extended output tests Total'] == 0:
        feedback += "I also ran your code against some additional output tests, although your program sadly scored " + str(autograder_marks["Extended output tests Total"]) + "/" + str(autograder_marks["Extended output tests Total Possible"]) + " against these tests.\n\n"
      elif autograder_marks['Extended output tests Total'] < 3:
        feedback += "I also ran your code against some additional output tests. Your code passed less than 50% of these tests (" + str(autograder_marks["Extended output tests Total"]) + "/" + str(autograder_marks["Extended output tests Total Possible"]) + "), which is a little disappointing although these tests were designed to exploit the edge cases that you may not have considered thus scoring high here was challenging. To score better marks here, you should have attempted to run your program various different arguments and reasoned about the outputs of your program.\n\n"
      elif autograder_marks['Extended output tests Total'] < 6:
        feedback += "I also ran your code against some additional output tests. Your code passed most of these tests (" + str(autograder_marks["Extended output tests Total"]) + "/" + str(autograder_marks["Extended output tests Total Possible"]) + "), which is a great outcome as these tests were designed to exploit the edge cases in your data thus scoring high here was challenging.\n\n"
      else:
        feedback += "I also ran your code against some additional output tests and your code passed all of these (" + str(autograder_marks["Extended output tests Total"]) + "/" + str(autograder_marks["Extended output tests Total Possible"]) + "), which is a fantastic outcome, and showed that you did a very thorough job following the coursework specification.\n\n"




      # TASK 2
      task2marks    = int(autograder_marks[test[catch2][provided]["01"]] + autograder_marks[test[catch2][provided]["02"]] + autograder_marks[test[catch2][provided]["03"]] + autograder_marks[test[catch2][provided]["04"]] + autograder_marks[test[catch2][extended]["12"]] + autograder_marks[test[output][provided]["01"]] + autograder_marks[test[output][provided]["02"]])
      task2possible =                                                  1 +                                              1 +                                              1 +                                              1 +                                              2 +                                              1 +                                              1 
      feedback += "Below is a summary of the various tasks, as organised by the coursework worksheet. Note that the marks given below are the same marks as given above but categorised by task rather than test type. For deciding the weighting of each test (i.e., number of marks), each test was assessed for its relative difficulty based on the module content and how much work was involved.\n\n1.1. TASK 2: IMPLEMENT PROGRAM ARGUMENT PARSING FUNCTIONS (" + str(task2marks) + "/" + str(task2possible) + ")\n"
      if autograder_marks[test[catch2][provided]["01"]] > 0 and \
         autograder_marks[test[catch2][provided]["02"]] > 0 and \
         autograder_marks[test[catch2][provided]["03"]] > 0 and \
         autograder_marks[test[catch2][provided]["04"]] > 0:

          feedback += "Your code correctly passed all four of the provided test suites (tests 1–4) that covered the four program arguments: datasets, areas, measures, and years. "

          if autograder_marks[test[catch2][extended]["01"]] > 0:
            feedback += "As a sign of your good programming, your code also correctly throws an exception when a provided with numbers of an incorrect length—this wasn't covered in the provided unit tests, although was expected as per the description of the function in bethyw.cpp.\n\n"
          else:
            feedback += "However, your code sadly does not throw an exception when a provided with year values of an incorrect length (e.g., 20). This wasn't covered in the provided unit tests, although was expected as per the description of the function.\n\n"
      else:
        if autograder_marks[test[catch2][provided]["01"]] > 0:
          feedback += "Your code correctly parses the datasets program argument in the BethYw::parseDatasetsArg() function, as per the test suite in test1.cpp. "

          if autograder_marks[test[catch2][provided]["02"]] > 0:
            feedback += "Likewise, it also parses the areas argument correctly, whether it is a single area\'s code, a comma-separated list of codes, contains \'all\' as a value, or is missing; and a filter list generated (test2.cpp). "

            if autograder_marks[test[catch2][provided]["03"]] > 0:
              feedback += "The measures program argument is parsed correctly in the BethYw::parseMeasuresArg() function, whether it is a single measure\'s codename, a comma-separated list of codenames, contains \'all\' as a value, or is missing (test3.cpp). "
            else:
              feedback += "However, your code doesn't seem to work properly with the measures program argument in the BethYw::parseMeasuresArg() function (test3.cpp). "
            
          else:
            feedback += "Sadly, though, it does not correctly parse the areas program argument in the BethYw::parseAreasArg() function "

          if autograder_marks[test[catch2][provided]["03"]] > 0:
            feedback += "as covered in test2.cpp. The measures program argument is parsed correctly in the BethYw::parseMeasuresArg() function though, whether it is a single measure\'s codename, a comma-separated list of codenames, contains \'all\' as a value, or is missing (test3.cpp). "
          else:
            feedback += "or the measures program argument in the BethYw::parseMeasuresArg() function. These were covered in test2.cpp and test3.cpp. "
          
        else:

          feedback += "Your code does not seem to correctly parse the datasets program argument in the BethYw::parseDatasetsArg() function, as per the test suite in test1.cpp. "

          if autograder_marks[test[catch2][provided]["02"]] > 0:
            feedback += "However, it does parse the areas argument correctly, whether it is a single area\'s code, a comma-separated list of codes, contains \'all\' as a value, or is missing; and a filter list generated (test2.cpp). "

            if autograder_marks[test[catch2][provided]["03"]] > 0:
              feedback += "The measures program argument is also parsed correctly in the BethYw::parseMeasuresArg() function, whether it is a single measure\'s codename, a comma-separated list of codenames, contains \'all\' as a value, or is missing (test3.cpp) "
            else:
              feedback += "It seems though that it doesn't work properly with the measures program argument in the BethYw::parseMeasuresArg() function (test3.cpp). "
            
          else:
            feedback += "Sadly, it also does not correctly parse the areas program argument in the BethYw::parseAreasArg() function "

          if autograder_marks[test[catch2][provided]["03"]] > 0:
            feedback += "as covered in test2.cpp. The measures program argument is parsed correctly in the BethYw::parseMeasuresArg() function though, whether it is a single measure\'s codename, a comma-separated list of codenames, contains \'all\' as a value, or is missing (test3.cpp). "
          else:
            feedback += "or the measures program argument in the BethYw::parseMeasuresArg() function. These were covered in test2.cpp and test3.cpp. "
          
        if autograder_marks[test[catch2][provided]["04"]] > 0:
          feedback += "Your code correctly parses the years program argument in the BethYw::parseYearsArg() function, whether it is a equal to single four-digit year, two four-digit years separated by a hyphen, \'0\', \'0-0\', or invalid due to the presence of non-numerical values (test4.cpp). "
          if autograder_marks[test[catch2][extended]["01"]] > 0:
            feedback += "Your code even threw an exception when the years argument was a number but was not four digits long, which was specified in the block comment but no provided test covered this edge case. "
          else:
            feedback += "That said, your code didn't seem to throw the correct exception when the years argument was a number of incorrect length (this was described as the expected outcome in the block comment, but was not an edge case covered in the provided test suite). "
        else:
          if autograder_marks[test[catch2][extended]["01"]] > 0:
            feedback += "Your code did not seem to correctly parse the years program argument in the BethYw::parseYearsArg() function (test4.cpp), although it did throw an exception when the years argument was a number of incorrect length (which was one of the hidden tests). "
          else:
            feedback += "Your code did not seem to correctly parse the years program argument in the BethYw::parseYearsArg() function (test4.cpp)—additionally one the hidden tests covered whether it threw an exception when given a non-four digit number (which your code also did not pass). "

      if autograder_marks[test[catch2][extended]["12"]] > 0:
        feedback += "Your code also allowed for the 'all' value in any case with the datasets, areas, and measures program argument—there was a hidden test to determine this."
      else:
        feedback += "The various block comments in bethyw.cpp for processing the datasets, areas, and measures program argument required that you to look for the 'all' value in a case-insensitive way, but your code did not seemingly do this for all four of the arguments (a single test covered all four here so you may have to inspect your code to determine why you failed this test)."

      feedback += "\n\nI also tested your code with some outputs, corresponding to this task. "

      if autograder_marks[test[output][provided]["01"]] > 0:
        feedback += "Your compiled program produced the output 'No dataset matches key: <invalid dataset>' to standard error (stderr) when given an invalid dataset as a program argument. "

        if autograder_marks[test[output][provided]["02"]] > 0:
          feedback += "Your program also produced the correct output of 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets.\n\n"
        else:
          feedback += "However, your program did not output 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets. This should have been a combination of the exception message thrown by InputFile::open() in input.cpp and the prepending error message as stated in BethYw::loadDatasets() in bethyw.cpp. When working in large systems with multiple teams, it may be necessary for your code to give exact outputs to support system interoperability. You could have verified this by checking your program against the sample output in the second output file.\n\n"
        
      else:
        feedback += "Your code did not output 'No dataset matches key: <invalid dataset>' to standard error (stderr) when given an invalid dataset as a program argument. This was stated in the block comment for BethYw::parseDatasetsArg() in bethyw.cpp and was shown in the output 1 test file. "

        if autograder_marks[test[output][provided]["02"]] > 0:
          feedback += "However, it did correctly output 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets.\n\n"
        else:
          feedback += "It also did not output 'Error importing dataset:\\nInputFile::open: Failed to open file <invalid dir>/areas.csv' when given a path to an invalid directory for the datasets. This should have been a combination of the exception message thrown by InputFile::open() in input.cpp and the prepending error message as stated in BethYw::loadDatasets() in bethyw.cpp. When working in large systems with multiple teams, it may be necessary for your code to give exact outputs to support system interoperability. You could have verified this by checking your program against the sample output in the second output file.\n\n"





      # TASK 3
      task3marks    = int(autograder_marks[test[catch2][provided]["05"]] + autograder_marks[test[catch2][provided]["08"]] + autograder_marks[test[catch2][extended]["11"]] + autograder_marks[test[catch2][provided]["10"]] + autograder_marks[test[catch2][provided]["11"]])
      task3possible =                                                  2 +                                              2 +                                              2 +                                              2 +                                              2

      feedback += "1.2. TASK 3: IMPLEMENT populateFromAuthorityCodeCSV PARSING (" + str(task3marks) + "/" + str(task3possible) + ")\n"
      if autograder_marks[test[catch2][provided]["05"]] > 0:
        feedback += "Firstly, your InputSource and InputFile classes work as expected according to the test suite (test5.cpp). "
      else:
        feedback += "Firstly, your InputSource and InputFile classes don't seem to work fully—either not returning a stream when given a valid filepath or not throwing an exception when given an invalid filepath (this was tested in test5.cpp). "

      if autograder_marks[test[catch2][provided]["08"]] > 0:
        feedback += "For this task, you had to implement the Area class to support names in multiple languages and local authority codes. Here your code passed the tests (test8.cpp). "
        if autograder_marks[test[catch2][extended]["11"]] > 0:
          feedback += "A hidden test verified that your code also threw an exception when given an invalid language code for a name. "
        else:
          feedback += "However, your code failed a hidden test to determine if your program throws an exception when given an invalid language code for a name, as requested in the provided framework. "
      else:
        feedback += "For this task, you had to implement the Area class to support names in multiple languages and local authority codes but it seems your code does not pass the basic tests for this class (test8.cpp). "
        if autograder_marks[test[catch2][extended]["11"]] > 0:
          feedback += "However, a hidden test verified that your code threw an exception when given an invalid language code for a name. "
        else:
          feedback += "Additionally, your code failed a hidden test to determine if your program throws an exception when given an invalid language code for a name, as requested in the provided framework. "

      if autograder_marks[test[catch2][provided]["10"]] > 0:
        feedback += "\n\nYou also had to implement—at least partially—the Areas class to allow it to contain Area instances and here your code passed the tests (test10.cpp). "
      else:
        feedback += "\n\nYou also had to implement—at least partially—the Areas class to allow it to contain Area instances, but sadly your code did not pass the requisite tests (test10.cpp). "

      if autograder_marks[test[catch2][provided]["11"]] > 0:
        feedback += "When testing your code with a fresh copy of areas.csv, everything seemed to work nicely (test11.cpp).\n\n"
      else:
        feedback += "When testing your code with a fresh copy of areas.csv, the data did not get imported correctly as I expected (test11.cpp). Did you verify if this worked correctly on your local machine?\n\n"





      # TASK 4
      task4marks    = int(autograder_marks[test[catch2][provided]["06"]] + autograder_marks[test[catch2][provided]["07"]] + autograder_marks[test[catch2][extended]["05"]] + autograder_marks[test[catch2][extended]["02"]] + autograder_marks[test[catch2][provided]["09"]] + autograder_marks[test[catch2][extended]["04"]] + autograder_marks[test[catch2][extended]["03"]])
      task4possible =                                                  2 +                                              2 +                                              2 +                                              1 +                                              2 +                                              2 +                                              2
      
      feedback += "1.3. TASK 4: COMPLETE THE Measure AND Area CLASSES (" + str(task4marks) + "/" + str(task4possible) + ")\n"

      if autograder_marks[test[catch2][provided]["06"]] > 0:
        feedback += "Your Measure object can be instantiated as expected (test6.cpp), "

        if autograder_marks[test[catch2][provided]["07"]] > 0:
          feedback += "and also passes the second set of tests to verify that it can store data correctly (test7.cpp). "
        else:
          feedback += "however, it doesn't seem to manage storing data as expected according to the test suite in test7.cpp. "
      else:
        feedback += "Your Measure object doesn't seem to work as expected according to the test suite in test6.cpp "

        if autograder_marks[test[catch2][provided]["07"]] > 0:
          feedback += "but does at least store data correctly (test7.cpp). "
        else:
          feedback += "and also doesn't seem to manage storing data as expected according to the test suite in test7.cpp. "

      if autograder_marks[test[catch2][extended]["05"]] > 0:
        if autograder_marks[test[catch2][extended]["02"]] > 0:
          feedback += "Hidden tests confirm your Measure object converts codenames to lowercase and also handles the insert-and-merge functionality correctly.\n\n"
        else:
          feedback += "Hidden tests confirm your Measure object converts codenames to lowercase, but it the expected insert-and-merge functionality described in the block comments doesn't seem to work quite as expected.\n\n"
      else:
        if autograder_marks[test[catch2][extended]["02"]] > 0:
          feedback += "A hidden test shows that your Measure object doesn't convert codenames to lowercase as required. A second hidden test though does show that the insert-and-merge functionality works as expected.\n\n"
        else:
          feedback += "Hidden tests show that your Measure object doesn't convert codenames to lowercase as required or implement the object to handle insert-and-merging of values correctly. You should have paid closer attention to the block comments here.\n\n"

      if autograder_marks[test[catch2][provided]["09"]] > 0:
        if autograder_marks[test[catch2][extended]["04"]] > 0:
          feedback += "Your Area class can successfully contain Measure instances and cannot contain two Measure instances with the same codename (test9.cpp). When given two Measure instances with the same codename, your Area instance will merge them correctly. "

          if autograder_marks[test[catch2][extended]["03"]] > 0:
            feedback += "Also, your Areas instance will merge two Area instances correctly when they have the same local authority code.\n\n"
          else:
            feedback += "However, this merging functionality also doesn't work in the Areas class, which was meant to merge Area instances together when encountering two with the same local authority code.\n\n"
        else:
          feedback += "Your Area class can successfully contain Measure instances and cannot contain two Measure instances with the same codename (test9.cpp). Sadly, though, a hidden test confirms that when given two Measure instances with the same codename, your Area instance does not merge them correctly as described in the block comments in area.cpp. "

          if autograder_marks[test[catch2][extended]["03"]] > 0:
            feedback += "Despite that, your Areas instance will merge two Area instances correctly when they have the same local authority code.\n\n"
          else:
            feedback += "In line with this, this merging functionality also doesn't work in the Areas class, which was meant to merge Area instances together when encountering two with the same local authority code.\n\n"
      else:
        if autograder_marks[test[catch2][extended]["04"]] > 0:
          feedback += "Your Area class seems to have issues with containing Measure instances, ensuring that two Measure instances with the same codename can't co-exist (test9.cpp). However, when given two Measure instances with the same codename, your Area instance will merge them correctly as per the block comment in area.cpp. "

          if autograder_marks[test[catch2][extended]["03"]] > 0:
            feedback += "Equally, your Areas instance will merge two Area instances correctly when they have the same local authority code.\n\n"
          else:
            feedback += "Sadly, however, this functionality doesn't work in the Areas class, which was meant to merge Area instances together when encountering two with the same local authority code.\n\n"

        else:
          feedback += "Your Area class seems to have issues with containing Measure instances, ensuring that two Measure instances with the same codename can't co-exist (test9.cpp). Additionally, when given two Measure instances with the same codename, your Area instance does not merge them correctly as described in the block comments in area.cpp. "

          if autograder_marks[test[catch2][extended]["03"]] > 0:
            feedback += "However, your Areas instance will merge two Area instances correctly when they have the same local authority code.\n\n"
          else:
            feedback += "In line with this, this merging functionality also doesn't work in the Areas class, which was meant to merge Area instances together when encountering two with the same local authority code.\n\n"





      # TASK 5
      task5marks    = int(autograder_marks[test[output][provided]["03"]] + autograder_marks[test[output][extended]["01"]])
      task5possible =                                                  1 +                                              1
      
      feedback += "1.4. TASK 5: IMPLEMENT OUTPUT (" + str(task5marks) + "/" + str(task5possible) + ")\n"

      if autograder_marks[test[output][provided]["03"]] > 0:
        feedback += "When testing your code for outputs based on the areas argument, your program produced an empty JSON object when given a non-existent area (output test 3). "
      else:
        feedback += "When testing your code for outputs based on the areas argument, your code did not output an empty JSON object ({}) when given a non-existent area as had been asked (output test 3). This was stated in the block comment of Areas::toJSON() in areas.cpp. "

      if autograder_marks[test[output][extended]["01"]] > 0:
        feedback += "In testing this with other program arguments and requesting JSON output, your program also returned an empty JSON object.\n\n"
      else:
        feedback += "However, when testing this with other program arguments and requesting JSON output, your program did not return an empty JSON object as expected (we ran this with command bethyw -a W060000999 -y 0 -m rb,db,all -j).\n\n"





      # TASK 6
      task6marks    = int(autograder_marks[test[catch2][provided]["12"]] + autograder_marks[test[output][provided]["04"]] + autograder_marks[test[output][provided]["05"]] + autograder_marks[test[catch2][extended]["06"]] + autograder_marks[test[catch2][extended]["07"]] + autograder_marks[test[output][provided]["06"]] + autograder_marks[test[catch2][extended]["08"]] + autograder_marks[test[output][provided]["07"]] + autograder_marks[test[catch2][extended]["09"]] + autograder_marks[test[output][provided]["08"]])
      task6possible =                                                  2 +                                              1 +                                              1 +                                              2 +                                              2 +                                              1 +                                              2 +                                              1 +                                              2 +                                              1
      
      feedback += "1.5. TASK 6: IMPLEMENT WelshStatsJSON PARSING (" + str(task6marks) + "/" + str(task6possible) + ")\n"

      if autograder_marks[test[catch2][provided]["12"]] > 0:
        if autograder_marks[test[output][provided]["04"]] > 0:
          if autograder_marks[test[output][provided]["05"]] > 0:
            feedback += "Your program correctly imported and produced output for the dataset popu1009.json in both the tables and JSON output (test12.cpp and provided output tests 4 and 5). "
          else:
            feedback += "Your program correctly imported and produced output for the dataset popu1009.json in the tables output, although its JSON output didn't match what I was expecting (test12.cpp and provided output tests 4 and 5). "
        else:
          if autograder_marks[test[output][provided]["05"]] > 0:
            feedback += "Your program correctly imported and produced output for the dataset popu1009.json in the JSON output, but its tables output doesn't seem correct; note that I tested your tables output without spaces and line breaks to avoid this being an issue (test12.cpp and provided output tests 4 and 5). "
          else:
            feedback += "Your program correctly imported the dataset popu1009.json, but both the tables and JSON output didn't match what I was expecting; note that I tested your output without spaces and line breaks to avoid this being an issue (test12.cpp and provided output tests 4 and 5). "
      else:
        feedback += "Your program didn't seem to import the dataset popu1009.json as expected (test12.cpp)"

        if autograder_marks[test[output][provided]["04"]] > 0:
          if autograder_marks[test[output][provided]["05"]] > 0:
            feedback += "; however your program produced valid output for both the tables and JSON format (provided output tests 4 and 5), suggesting some issues with ensuring your API was compatible with what was expected. "
          else:
            feedback += "; however your program correctly generated the tables output but not the JSON output (provided output tests 4 and 5), suggesting some issues with ensuring your API was compatible with what was expected. "
        else:
          if autograder_marks[test[output][provided]["05"]] > 0:
            feedback += "; however your program produced valid output for the JSON output, but not the tables output (provided output tests 5 and 4), suggesting some issues with your class. "
          else:
            feedback += " and correspondingly your code produced invalid output too (provided output tests 4 and 5). "

      if autograder_marks[test[catch2][extended]["06"]] > 0:
        feedback += "Your implementation of the three statistics functions passed my test for them.\n\nWith regards to the other JSON-based datasets:\n"
      else:
        feedback += "Your implementation of the three statistics functions don't seem to pass my test for them?\n\nWith regards to the other JSON-based datasets:\n"

      if autograder_marks[test[catch2][extended]["07"]] > 0:
        if autograder_marks[test[output][provided]["06"]] > 0:
          feedback += "- Your program parses and imports the econ0080.json file correctly, and its JSON output is also correct for this dataset (provided output 6)\n"
        else:
          feedback += "- Your program parses the econ0080.json file correctly, although its JSON output is not correct for this dataset (provided output 6)\n"
      else:
        if autograder_marks[test[output][provided]["06"]] > 0:
          feedback += "- Your program doesn't parse the econ0080.json file correctly, although its JSON output is correct for this dataset (provided output 6)\n"
        else:
          feedback += "- Your program doesn't parse the econ0080.json file correctly and as a result its JSON output is incorrect c(provided output 6)\n"

      if autograder_marks[test[catch2][extended]["08"]] > 0:
        if autograder_marks[test[output][provided]["07"]] > 0:
          feedback += "- Your program parses and imports the envi0201.json file correctly, and its JSON output is also correct for this dataset (provided output 7)\n"
        else:
          feedback += "- Your program parses the envi0201.json file correctly, although its JSON output is not correct for this dataset (provided output 7)\n"
      else:
        if autograder_marks[test[output][provided]["07"]] > 0:
          feedback += "- Your program doesn't parse the envi0201.json file correctly, although its JSON output is correct for this dataset (provided output 7)\n"
        else:
          feedback += "- Your program doesn't parse the envi0201.json file correctly and as a result its JSON output is incorrect c(provided output 7)\n"

      if autograder_marks[test[catch2][extended]["09"]] > 0:
        if autograder_marks[test[output][provided]["08"]] > 0:
          feedback += "- Your program parses and imports the tran0152.json file correctly, and its JSON output is also correct for this dataset (provided output 8)\n"
        else:
          feedback += "- Your program parses the tran0152.json file correctly, although its JSON output is not correct for this dataset (provided output 8)\n"
      else:
        if autograder_marks[test[output][provided]["08"]] > 0:
          feedback += "- Your program doesn't parse the tran0152.json file correctly, although its JSON output is correct for this dataset (provided output 8)\n"
        else:
          feedback += "- Your program doesn't parse the tran0152.json file correctly and as a result its JSON output is incorrect c(provided output 8)\n"






      # TASK 7
      task7marks    = int(autograder_marks[test[catch2][extended]["10"]] + autograder_marks[test[catch2][extended]["10a"]] + autograder_marks[test[output][provided]["09"]] + autograder_marks[test[output][provided]["10"]] + autograder_marks[test[output][extended]["06"]] + autograder_marks[test[output][extended]["06a"]])
      task7possible =                                                  2 +                                               0 +                                               1 +                                              1 +                                              1 +                                               0
      
      feedback += "\n1.6. TASK 7: IMPLEMENT AuthorityByYearCSV PARSING (" + str(task7marks) + "/" + str(task7possible) + ")\n"

      if autograder_marks[test[catch2][extended]["10"]] > 0:
        feedback += "A hidden Catch2 test confirmed that your program parses the complete-popu1009-popden.csv file correctly. "

        if autograder_marks[test[output][provided]["09"]] > 0:
          feedback += "Likewise, the output matched the expected output for this dataset (provided output 9). "
        else:
          feedback += "However, the output did not match the expected output for this dataset (provided output 9). "

      else:
        feedback += "A hidden Catch2 test indicates that your program does not parse the complete-popu1009-popden.csv as expected. "

        if autograder_marks[test[output][provided]["09"]] > 0:
          feedback += "However, the output matched the expected output for this dataset (provided output 9). "
        else:
          feedback += "Likewise, the output did not match the expected output for this dataset (provided output 9). "

      if autograder_marks[test[output][provided]["10"]] > 0:
        feedback += "The output for the complete-popu1009-pop.csv dataset was correct (provided output 9).\n\n"
      else:
        feedback += "The output for the complete-popu1009-pop.csv dataset didn't match what I expected (provided output 9).\n\n"

      if autograder_marks[test[output][provided]["06"]] > 0 or autograder_marks[test[output][provided]["06a"]] > 0:
        feedback += "When looking at the output for the command bethyw -a W06000015,W06000011 -y 2015 -j, your program gave an expected output. Note that there were two possible outputs expected here depending on how you interpreted the requirement to add Area and Measures instances for previously un-encountered areas/measures (i.e., you could have decided to always create an Area/Measure instance for a previously un-encountered area/measure and then apply the filtering to decide whether to import the data. Alternatively, you could have applied the filter first before deciding to create the Area/Measure instances). I initially intended the former but encountered both during marking and its clear the initial requirements were ambiguous (demonstrating the difficulty in writing precise specifications!).\n"
      else:
        feedback += "When looking at the output for the command bethyw -a W06000015,W06000011 -y 2015 -j, it looks like your program doesn't have an expected output. Note that there were two possible outputs expected here depending on how you interpreted the requirement to add Area and Measures instances for previously un-encountered areas/measures (i.e., you could have decided to always create an Area/Measure instance for a previously un-encountered area/measure and then apply the filtering to decide whether to import the data. Alternatively, you could have applied the filter first before deciding to create the Area/Measure instances). I initially intended the former but encountered both during marking and its clear the initial requirements were ambiguous (demonstrating the difficulty in writing precise specifications!).\n"






      # TASK 8
      task8marks    = int(autograder_marks[test[output][extended]["02"]] + autograder_marks[test[output][extended]["02a"]] + autograder_marks[test[output][provided]["10"]] + autograder_marks[test[output][extended]["03"]] + autograder_marks[test[output][extended]["04"]] + autograder_marks[test[output][extended]["05"]] + autograder_marks[test[output][extended]["05a"]])
      task8possible =                                                  1 +                                               0 +                                              1 +                                              1 +                                              1 +                                              1 +                                              0
      
      feedback += "\n1.7. TASK 8: IMPLEMENT EXTENDED ARGUMENT FILTERING (" + str(task8marks) + "/" + str(task8possible) + ")\nFor this task, there were a variety of different output tests:\n"

      if autograder_marks[test[output][provided]["02"]] > 0 or autograder_marks[test[output][provided]["02a"]] > 0:
        feedback += "- The output for the command bethyw -a swan -m RAIL was exactly as I expected\n"
      else:
        feedback += "- The output for the command bethyw -a swan -m RAIL didn't seem to match what was expected (even accounting for the two interpretations of the filtering)\n"

      if autograder_marks[test[output][provided]["03"]] > 0:
        feedback += "- The output for the command bethyw -d popden -a swan -m RAIL was exactly as I expected\n"
      else:
        feedback += "- The output for the command bethyw -d popden -a swan -m RAIL didn't seem to match what was expected\n"

      if autograder_marks[test[output][provided]["04"]] > 0:
        feedback += "- The output for the command bethyw -d popden -a Abertawe,Swansea was exactly as I expected\n"
      else:
        feedback += "- The output for the command bethyw -d popden -a Abertawe,Swansea didn't seem to match what was expected\n"

      if autograder_marks[test[output][provided]["05"]] > 0 or autograder_marks[test[output][provided]["05a"]] > 0:
        feedback += "- The output for the command bethyw -a swan,card -m pop,rail -y 2010-2018 -j was exactly as I expected\n"
      else:
        feedback += "- The output for the command bethyw -a swan,card -m pop,rail -y 2010-2018 -j didn't seem to match what was expected (even accounting for the two interpretations of the filtering)\n"

      return stage_result(
        updated_label    = "Autograder marks imported and feedback generated",
        student_feedback = feedback,
        student_marks    = int(autograder_marks['Total Points']),
        next_stage       = "opensrc")
    except KeyError as e:
      return stage_result(
        updated_label = "Error with autograder import:" + str(e),
        next_stage    = None)


  def opensrc(student_id, marks, feedback):
    cmd = coursework.CMD_OPEN_CODE + [coursework.TEST_SRC_DIR]
    res = subprocess.run(cmd)
    return stage_result(
      updated_label     = "Source code opened in external application",
      next_stage        = "negative_marking_switch")



  def negative_marking_switch(student_id, marks, feedback):
      return stage_result(
          updated_label    = "Added 40 marks, remaining parts are negative marked... (" + str(marks) + " marks were for tests)",
          next_stage       = "tables_output",
          student_marks    = 40)


  def tables_output(student_id, marks, feedback): # max: -2 marks
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "bethyw.cpp",
           "input.cpp",
           "areas.cpp",
           "area.cpp",
           "measure.cpp",
           "main.cpp",
           "-o",
           "./bin/bethyw"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

    if res.returncode == 0:
      cmd = ["./bin/bethyw",
             "popden"]
      res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)
    
      stdout = res.stdout.decode("utf-8")
      stderr = res.stderr.decode("utf-8")

      if res.returncode == 0 and stderr == "":
        preamble = "\n2.0 GOODNESS (//goodness_total///40)\nThe marking for this section is based on a qualitative assessment of the code you produced for this assignment. This has been broken out, for clarity, over a number of subsections below.\n\n"
        multidecision = [
            {
             "out4":      ("Output is wrong",                         -2, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting doesn't seem right. Perhaps something went wrong somewhere? For this I looked at the 'popden' and compared it to what I expected."),
             "out3":      ("Output is very messy",                    -2, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting is a messy. You were given sample outputs and it was also explained that this should be human-readable, formatted in a table-like manner where all the values were aligned. "),
             "out2":      ("Output is messy",                         -1, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting is a bit messy, and could have been clearer. "),
             "out1":      ("Output is not quite perfect",              0, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting is neat and readable. "),
             "out0":      ("Output is perfect",                        0, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting is very neat and readable. ")
            },
            {
             "stats2":    ("<skip stats point>",                       0, ""),
             "stats1":    ("Statistics NOT included",                  0, "You did not include the required statistics in your output. "),
             "stats0":    ("Statistics included",                      0, "You did included the required statistics in your output, which is great. ")
            },
            {
             "noareas3":  ("<skip areas with no data point>",          0, ""),
             "noareas2":  ("Areas with no data missing",               0, "When an area has no measures or data, I was expecting something like <no measures> or <no data> to be printed to signify this.\n\n"),
             "noareas1":  ("Areas with no data messy",                 0, "When an area has no measures, I was expecting something like <no measures> or <no data> to be printed to signify this, and for this to be clear to the user.\n\n"),
             "noareas0":  ("Areas with no data fine",                  0, "You did include areas which had no data given the current filters, clearly denoting this.\n\n")
            },
        ]
        
        return stage_result(
          updated_label    = "Sample tables output generated",
          view_text        = ("Output from ./bin/bethyw -d popden -m area -y 1992-1995", stdout),
          decision         = multidecision,
          next_stage       = "memtest")

    return stage_result(
      updated_label    = "Couldn't compile and run coursework with tables table",
      next_stage       = "memtest",
      student_marks    = -2)
        

    if not os.path.isfile(coursework.TEST_SRC_DIR + "/README.md"):
      return stage_result(
        updated_label = "Tables output checked",
        next_stage    = "memtest")

    with open(coursework.TEST_SRC_DIR + "/README.md", "r") as f:
      contents = f.read()

    return stage_result(
      updated_label = "README.md included and opened",
      view_text     = ("README.md", contents),
      next_stage    = "memtest")


  def memtest(student_id, marks, feedback): # max: 0 marks
    return stage_result(
      updated_label = "Skipping Valgrind",
      next_stage    = "input_source")

    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "bethyw.cpp",
           "input.cpp",
           "areas.cpp",
           "area.cpp",
           "measure.cpp",
           "main.cpp",
           "-ggdb3",
           "-o",
           "./bin/bethyw"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

    if res.returncode != 0:
      # details = ' '.join(cmd) + "\n\n"
      details = res.stderr.decode("utf-8")

      return stage_result(
        updated_label = "Could not compile the coursework with GCC {0}".format(res.returncode),
        next_stage    = None,
        details       = details)

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

    feedback += "MEMORY LEAKS\n"
    valgrind_response = res.stderr.decode("utf-8")

    with open(coursework.MARKS_DIR + "/" + student_id + '-valgrind.txt', 'w') as file:
      file.write(valgrind_response)

    if valgrind_response.find("All heap blocks were freed") > 0:
      feedback += "Great work, your code has no memory leaks.\n\n"
      return stage_result(
          updated_label    = "Coursework passed memory leak test",
          next_stage       = "input_source",
          student_feedback = feedback,
          student_marks    = 0)
    else:
      feedback += "It seems that your code contains a one or more memory leaks. You should make sure you free any memory you allocate on the heap. In reality, you should have used good RAII principles taught in lectures and not needed to handle memory management at all.\n\n"
      return stage_result(
          updated_label    = "Coursework was found to contain memory leaks",
          next_stage       = "input_source",
          student_marks    = -2,
          student_feedback = feedback)


  def input_source(student_id, marks, feedback): # max -1
    multidecision = [
        {
         "inpt2":     ("InputSource and InputFile functions + destructor aren't virtual",                     -1, "\n\n2.2. INHERITANCE\nYou didn't make the InputSource and InputFile functions and destructor all virtual, as required. "),
         "inpt1":     ("InputSource and InputFile functions + destructor are virtual",                         0, "\n\n2.2. INHERITANCE\nIn InputSource and InputFile, you correctly used virtual functions, including with a virtual destructor."),
        },
      ]

    return stage_result(
      updated_label = "InputSource and InputFile functions checked",
      decision      = multidecision,
      next_stage    = "function_ordering")



  def function_ordering(student_id, marks, feedback): # max -.5 marks
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
        student_feedback = feedback + "\n\n2.3. CODE STYLE\nThank you for keeping the functions in the same order as in the provided code. This makes it easier to mark your work. ",
        student_marks    = 0,
        next_stage       = "not_const_functions")
    else:
      return stage_result(
        updated_label    = "The student didn't keep the functions in order",
        student_feedback = feedback + "\n\n2.3. CODE STYLE\nYou were asked to keep the functions in the same order as they were given to you in the block comments. Not doing this makes it significantly harder to mark your work. ",
        student_marks    = -.5,
        next_stage       = "not_const_functions")



  def not_const_functions(student_id, marks, feedback): # max -2 marks
    marks = 0
    not_consty = []

    # test area for const
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "area.cpp",
           "-o",
           "area"]
    res = subprocess.run(cmd, cwd='./_constcheck', capture_output=True)
    if res.returncode != 0:
      marks = -.6
    else:
      res = subprocess.run(["./area"], cwd='./_constcheck', capture_output=True)
      stdout = res.stdout.decode("utf-8")

      if "getLocalAuthorityCode() = 0" in stdout:
        marks -= .2
        not_consty.append("Area::getLocalAuthorityCode()")
      if "getName() = 0" in stdout:
        marks -= .2
        not_consty.append("Area::getName()")
      if "size() = 0" in stdout:
        marks -= .2
        not_consty.append("Area::size()")

    # test areas for const
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "areas.cpp",
           "-o",
           "areas"]
    res = subprocess.run(cmd, cwd='./_constcheck', capture_output=True)
    if res.returncode != 0:
      marks = -.2
    else:
      res = subprocess.run(["./areas"], cwd='./_constcheck', capture_output=True)
      stdout = res.stdout.decode("utf-8")

      if "size() = 0" in stdout:
        marks -= .2
        not_consty.append("Areas::size()")

    # test measure for const
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "measure.cpp",
           "-o",
           "measure"]
    res = subprocess.run(cmd, cwd='./_constcheck', capture_output=True)
    if res.returncode != 0:
      marks = -1.2
    else:
      res = subprocess.run(["./measure"], cwd='./_constcheck', capture_output=True)
      stdout = res.stdout.decode("utf-8")
      if "getCodename() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getCodename()")
      if "getLabel() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getLabel()")
      if "size() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::size()")
      if "getDifference() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getDifference()")
      if "getDifferenceAsPercentage() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getDifferenceAsPercentage()")
      if "getAverage() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getAverage()")

    if marks == -.2:
      feedback += "In the various block comments in the comment, I expected various class functions to be declared as const (i.e., to be callable in a constant context). You did this well, although missed this for "
      for function in not_consty:
        feedback += function + '. '
    elif marks < -.2:
      feedback += "\n\nIn the various block comments in the comment, I expected the following class functions to be declared as const (i.e., to be callable in a constant context):\n"
      for function in not_consty:
        feedback += '  - ' + function + '\n'
      feedback += '\n'
    else:
      feedback += 'Well done for also correctly declaring the various requested functions as const. '

    return stage_result(
      updated_label    = "Deducted %f marks for non-const functions" % marks,
      next_stage       = "aggressive_warnings",
      student_feedback = feedback,
      student_marks    = marks)



  def aggressive_warnings(student_id, marks, feedback): # max -5.5 marks
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "-pedantic",
           "-Wall",
           "-Wextra",
           "-Wcast-qual",
           "-Wctor-dtor-privacy",
           "-Wdisabled-optimization",
           "-Wformat=2",
           "-Winit-self",
           "-Wuninitialized",
           "-Wlogical-op",
           "-Wmissing-declarations",
           "-Wmissing-include-dirs",
           "-Wnoexcept",
           "-Woverloaded-virtual",
           "-Wredundant-decls",
           "-Wshadow",
           "-Wsign-promo",
           "-Wstrict-null-sentinel",
           "-Wstrict-overflow=5",
           "-Wswitch-default",
           "-Wundef",
           "-Werror",
           "-Wno-unused",
           "bethyw.cpp",
           "input.cpp",
           "areas.cpp",
           "area.cpp",
           "measure.cpp",
           "main.cpp",
           "-o",
           "./bin/bethyw"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)
    stdout = res.stdout.decode("utf-8")
    stderr = res.stderr.decode("utf-8")

    if res.returncode == 0 and stderr == "":
      return stage_result(
        updated_label    = "Coursework compiled without any warnings, despite all the extra flags",
        next_stage       = "code_style")

    else:
      quality_errors = {
        # string in gcc output : (marks to deduce, num regex matches, regex match, feedback, friends)
        'casts away qualifiers':                  (1, 2, r'([a-zA-Z.]*):([0-9]+)',            "It seems your code casts away some qualifiers (e.g. const) from variables, which is typically an indication of trouble in your code and bad practice. You should always work to honour qualifiers such as const rather than overriding them. The first occurence of this I spotted was in __ on line __."),

        'used uninitialized':                     (1, 2, r'([a-zA-Z.]*):([0-9]+)',            "You have used a variable that is uninitalised in your code, without initialising it. I discussed this in lectures and labs. This is incredibly easy to do as this is a case of 'undefined behaviour' (i.e., some compilers on some platforms will automatically initalise variables for you and some won't). However, I treated this as bad practice as you were advised in lectures to avoid doing this. The first occurence I spotted was in __ on line __."),

        'of equal expressions':                   (1, 2, r'([a-zA-Z.]*):([0-9]+)',            "There is some suspect logic in __ on line __—you seem testing the same thing twice in your logical test?"),

        'no previous declaration for':            (1, 2, r"([a-zA-Z.]*)[^']*'(.*)'",          "I asked you to always declare functions in header files before implementing them, but it seems you didn't always manage this, as in __ with the free function __.", ['no declaration matches']),
        'no declaration matches':                 (1, 2, r"([a-zA-Z.]*)[^']*'(.*)'",          "It seems that the although you provided an implementation in __ for the function __, there isn't a matching declaration of it?. I asked to you make sure you always included declarations for your functions in the appropriate header files.", ['no previous declaration for']),

        'shadows a parameter':                    (1, 3, r"([a-zA-Z.]*):([0-9]+)[^']*'(.*)'", "You've inadvertently shadowed a variable. This is where you create a variable inside a given scope, when it has been always declared in a higher scope or as a parameter (as in this case). The first place I spotted this was in __ on line __ with the __.", ['shadows a local', 'shadows a previous local', 'shadows a member']),
        'shadows a local':                        (1, 3, r"([a-zA-Z.]*):([0-9]+)[^']*'(.*)'", "You've inadvertently shadowed a variable. This is where you create a variable inside a given scope, when it has been always declared in a higher scope (as in this case) or where you declare a variable with the same name as a parameter. The first place I spotted this was in __ on line __ with the __.", ['shadows a member', 'shadows a previous local', 'shadows a parameter']),
        'shadows a previous local':               (1, 3, r"([a-zA-Z.]*):([0-9]+)[^']*'(.*)'", "You've inadvertently shadowed a variable. This is where you create a variable inside a given scope, when it has been always declared in a higher scope (as in this case) or where you declare a variable with the same name as a parameter. The first place I spotted this was in __ on line __ with the __.", ['shadows a member', 'shadows a local', 'shadows a parameter']),
          'shadows a member':                       (1, 3, r"([a-zA-Z.]*):([0-9]+)[^']*'(.*)'", "You've inadvertently shadowed a member variable. This is where you create a variable inside a given scope, when it has been always declared in a higher scope (a member variable in this case) or where you declare a variable with the same name as a parameter. The first place I spotted this was in __ on line __.", ['shadows a local', 'shadows a previous local', 'shadows a parameter']),

        'switch missing default case':            (.5, 2, r'([a-zA-Z.]*):([0-9]+)',            "You seem to have a switch statement in __ on __ that doesn't have a default value. This may be OK in this case, but typically one would be expected (e.g., to catch unexpected values).")
      }
      feedback_list = []
      found_quality_errors = []
      marks_subtraction = 0

      for line in stderr.split("\n"):
        for gcc_str, parse in quality_errors.items():
          if gcc_str not in found_quality_errors:
            if gcc_str in line:
              stderr = ("!! Found '%s'\n" % gcc_str) + stderr
              re_position_in_code = re.compile(parse[2])
              match = re.search(re_position_in_code, line)
              if match is not None:
                temp_feedback = parse[3]
                for i in range(0, parse[1]):
                  temp_feedback = temp_feedback.replace("__", match.group(i+1), 1)
                feedback_list.append(temp_feedback)
                marks_subtraction -= parse[0]

                found_quality_errors.append(gcc_str)
                try:
                  for friend_match in parse[4]:
                    found_quality_errors.append(friend_match)
                except:
                  pass
              else:
                pass

      marks_subtraction = max(-5, marks_subtraction)

      if len(feedback_list) == 0:
        return stage_result(
          updated_label    = "Deducted %d marks for warnings" % -(marks_subtraction),
          details          = "No automatically detected issues thus no marks could be automatically deducted. Please read the output below and prepare to modify the students feedback to include the issues highlighted!\n\n" + stderr,
          next_stage       = "code_style")

      elif len(feedback_list) == 1:
        lower = lambda s: s[:1].lower() + s[1:] if s else ''
        feedback += "While reviewing your code, I noticed the following that " + lower(feedback_list[0]) + "\n"

      elif len(feedback_list) > 1:
        feedback += "\n\nWhile reviewing your code, I noticed the following that:\n"
        for i, feedback_item in enumerate(feedback_list):
          feedback += '  ' + str(i+1) + ". " + feedback_item + "\n"

      return stage_result(
        updated_label    = "Deducted %f marks for warnings" % (-marks_subtraction),
        details          = stderr,
        next_stage       = "code_style",
        student_feedback = feedback + "\n",
        student_marks    = marks_subtraction)



  def code_style(student_id, marks, feedback): # max -16
    multidecision = [
        {
         "messy1":    ("Indentation/code style is very messy or inconsistent",                                 -2, "Your use of indentation and general code style seems somewhat inconsistent and messy. "),
         "messy2":    ("Indentation/code style is a little messy/mostly OK",                                   -1, "Your use of indentation and general code style seems occasionally inconsistent and messy. "),
         "messy3":    ("Indentation is perfect",                                                                0, "Your use of indentation and general code style is consistent. "),
        },

        {
         "comments5": ("No commenting",                                                                        -2, "You haven't really used any comments of note in your work. In future, you should use comments to explain complex chunks of code that may not be obvious at first glance. "),
         "comments4": ("Alright commenting (i.e. have used them if needed)",                                 -1.5, "Your use of commenting is OK. Remember, you only need comments to explain complex chunks of code rather than individual lines. You were told to assume that the people marking your work know C++. In future, focus on providing explanatory comments rather than comments that merely repeat what can be gleamed from code. "),
         "comments3": ("Excessive commenting given the complexity of the code",                                -1, "You have used a few too many comments in your coursework solution. Remember, you only need comments to explain complex chunks of code rather than individual lines. You were told to assume that the people marking your work know C++. "),
         "comments2": ("Could have included additional comments to explain complex chunks of code",            -1, "You could have used some more comments in your coursework solution to help readers of your code understand complex code blocks. "),
         "comments1": ("Good commenting in relevant places",                                                    0, "You have used commenting well throughout your coursework solution. Comments help readers of your code understand complex code blocks. ")
        },
        
        {
         "naming4":   ("Poor naming of variables ",                                                            -1, "You don't seem to have adopted a convention when it comes to naming your elements such as variables. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments. Remember, the names of variables if for humans reading your code and not the machine, so don't simply default to giving simplistic names, e.g., i, except in limited cased (e.g., iterators).\n\n", 0),
         "naming3":   ("OK naming of variables and functions (e.g. some variables are not descriptive)",      -.5, "In terms of naming convention, you could have shown greater care with naming your elements such as variables. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments. Remember, the names of variables if for humans reading your code and not the machine, so don't simply default to giving simplistic names, e.g., i, except in limited cased (e.g. iterators).\n\n", 1),
         "naming2":   ("Generally good naming of variables and functions",                                    -.5, "In terms of naming convention, you have used good naming of variables etc. in your code. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments.\n\n", 2),
         "naming1":   ("Consistently excellent naming of variables and functions",                              0, "In terms of naming convention, you have consistently used good naming of variables etc. in your code. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments.\n\n", 3)
        },
        
        {
         "const5":    ("No use of the const keyword with variables",                                           -2, "You don't seem to have used const in any significant way in your coursework. Using const wherever you will not be modifying a value or rely upon a variable to not change is good practice.\n\n"),
         "const4":    ("Little use of the const keyword with variables",                                       -2, "In terms of using const for non-modifiable variables and references, there are a few places where you could have used this where you did not. Using const wherever you will not be modifying a value or rely upon a variable to not change is good practice.\n\n"),
         "const3":    ("Could have used more instances of the const keyword with variables",                 -1.5, "In terms of using const for non-modifiable variables and references, there are a few places where you could have used this where you did not. Using const wherever you will not be modifying a value or rely upon a variable to not change is good practice.\n\n"),
         "const2":    ("Good use of the const keyword for variables",                                          -1, "In terms of using const for non-modifiable variables and references, you've used this well. Using const wherever you will not be modifying a value or rely upon a variable to not change is good practice.\n\n"),
         "const1":    ("Perfect use of the const keyword for variables",                                        0, "In terms of using const for non-modifiable variables and references, you've used this very well.\n\n"),
        },
        
        {
         "nd2":       ("Missing delete/delete [] for a new/new []",                                            -2, "There are a few places where you should have used delete/delete [] to ensure you have deallocated memory on the heap that you allocated with the new/new [] keywords. I covered this quite a few times in lectures that with C and C++, memory management is still the responsibility of the developer. "),
         "nd0":       ("delete/delete []'d everything they have new/new []'d",                               -0.5, "You used the new/new [] keywords in your code to allocate data on the heap, but also used the delete/delete [] keywords to free this memory. This is good, although generally speaking we should try to avoid newing and deleting as much as possible. "),
         "nd1":       ("No use of new/delete",                                                                  0, "You haven't used new/delete anywhere, which is great. As I covered in lectures, this introduces challenges, e.g., when we start to also mix in things like exceptions which sidestep the typical flow of execution. "),
        },
        
        {
         "if3":       ("Missing delete/delete [] with stream in InputFile",                                    -2, "It seems your InputSource/InputFile instances store a pointer but it's not clear where this is deleted. Remember, whenever we new, we must delete. This is also complicated by exceptions, which sidestep the normal flow of execution.  You could have used something like std::unique_ptr here, storing the stream as a member variable, or put more code in try...catch blocks to avoid this. "),
         "if2":       ("delete with stream in InputFile, but what about exceptions?",                          -1, "It seems your InputSource/InputFile instances store a pointer that gets deleted in the destructor, although it's not clear if this would get cleaned up if an exception was thrown in your code. You could have used something like std::unique_ptr here, storing the stream as a member variable, or put more code in try...catch blocks to avoid this."),
         "if1":       ("Use of std::unique_ptr or equivalent in InputFile",                                     0, "You have used a Standard Library RAII function, which is excellent practice and demonstrates great engagement with the topics discussed in lectures. Great work!"),
         "if0":       ("Stored the stream as a member variable",                                                0, "You have avoided using new/delete inside InputFile, which given we want to avoid this as much as possible, is good practice to keep up."),
        },
        
        {
         "div1":      ("Measure::getAverage/Difference/DifferenceAsPercentage() susceptible to div/0",         -2, "\n\nIn your implementation of the statistics functions in the Measure class, your code seems to be susceptible to a division by 0 error, which would have crashed your application. You should make sure you are not dividing by zero ever in code. This is a runtime error and hard to catch, but a common source of issues."),
         "div0":      ("Measure::getAverage/Difference/DifferenceAsPercentage() protected against size() = 0",  0, "")
        },
        
        {
         "pop2":      ("No populate functions handle nullptr",                                                 -2, "\n\nYour populate…() functions in areas.cpp don't seem to look for/check for nullptr being passed in with the filter arguments. You should always check parameter inputs in your functions, especially if they are pointers, before trying to do anything with them."),
         "pop1":      ("Some populate functions handle nullptr",                                               -1, "\n\nIn seems some your populate…() functions in areas.cpp don't seem to look for/check for nullptr being passed in in with the filter arguments. You should always check parameter inputs in your functions, especially if they are pointers, before trying to do anything with them."),
         "pop0":      ("All populate functions handle nullptr",                                                 0, "\n\nYour populate…() functions in areas.cpp are checking for nullptr on the filter arguments! This was an area where it was incredibly easy to forget to do this.")
        },
      ]

    return stage_result(
      updated_label = "Code style checking finished",
      decision      = multidecision,
      next_stage    = "extra_features")



  def extra_features(student_id, marks, feedback): # max +3
    multidecision = [
        {
         "pa2":       ("No extra program arguments",                                                           0, "\n\n2.4. EXTRA FEATURES\n"),
         "pa1":       ("Good extra program arugments",                                                         1, "\n\n2.4. EXTRA FEATURES\nThe extra features, including program arguments, you added are nice. "),
         "pa0":       ("Redundant extra program arguments",                                                    0, "\n\n2.4. EXTRA FEATURES\n"),
        },
        
        {
         "oo2":       ("No operator overloading",                                                               0, "You didn't seem to overload any operators except for what was explicitly asked. This is fine as you weren't expected to, but you could look into this in the future. "),
         "oo1":       ("Sensible operator overloading",                                                         1, "You overloaded some additional operators too, which was great. Operator overloading is a nice feature in C++ we should try to use it as much as we can (where it makes sense). "),
         "oo0":       ("Redundant operator overloading",                                                        0, "You overloaded some additional operators too, which was great. Operator overloading is a nice feature in C++ we should try to use it as much as we can (where it makes sense). I can't see much use of it in your coursework, but that's fine. "),
        },

        {
         "tests2":    ("No extra tests",                                                                       0, "You could have written some extra tests for catching edge cases, if you wanted. "),
         "tests1":    ("Sensible extra tests",                                                                 1, "Adding extra test cases was a nice touch! "),
         "tests0":    ("Redundant extra tests",                                                                0, "Adding extra test cases was a good idea, although the tests provided seem redundant? "),
        },
        
        {
         "x1":        ("No extra features",                                                                     0, "You didn't include any extra features, which was fine. You weren't asked too."),
         "x0":        ("They had extra features",                                                               0, ""),
        },
    ]

    return stage_result(
      updated_label = "Extra features checking finished",
      decision      = multidecision,
      next_stage    = "exceptions")



  def exceptions(student_id, marks, feedback): # max -4
    # Wildcard catch test
    files = ["bethyw.cpp",
             "bethyw.h",
             "input.cpp",
             "input.h",
             "areas.cpp",
             "areas.h",
             "area.cpp",
             "area.h",
             "measure.cpp",
             "measure.h"]
    found_in = []

    for file in files:
      with open(coursework.TEST_SRC_DIR + "/" + file, 'r') as f:
        all_lines = ''.join(f.readlines())
        wildcard_catch = re.compile(r'catch\s*\(\s*...\s*\)')
        match = re.search(wildcard_catch, all_lines)
        if match is not None:
          found_in.append(file)
          break

    if len(found_in) > 0:
      mark = -2
      feedback += "\n\n2.5. EXCEPTIONS\nFirstly, disappointingly, despite being asked not to do so, you had a wildcard catch(...) in your code. I found this in "
      for i, filename in enumerate(found_in):
        feedback += filename
        if i + 2 == len(found_in):
          feedback += ' and '
        elif i + 1 < len(found_in):
          feedback += ', '
      feedback += '.'
    else:
      feedback += "\n\n2.5. EXCEPTIONS\n"
      marks = 0

    # Const reference catch check
    files = ["bethyw.cpp",
             "bethyw.h",
             "input.cpp",
             "input.h",
             "areas.cpp",
             "areas.h",
             "area.cpp",
             "area.h",
             "measure.cpp",
             "measure.h"]
    found_in = []

    num_exceptions = 0
    num_const = 0
    num_ref = 0
    non_constref_exceptions = []
    re_catch = re.compile(r'catch\s*\(\s*([^)]*)\s*\)')
    for file in files:
      identified_catch_statements = []

      with open("_tempsrc/" + file, 'r') as f:
        for no, line in enumerate(f.readlines()):
          matches = re.findall(re_catch, line)  

          for match in matches:
            num_exceptions += 1
            identified_catch_statement = ''.join(match)

            if 'const ' in identified_catch_statement:
              num_const += 1
              if '&' in identified_catch_statement:
                num_ref += 1
            else:
              non_constref_exceptions.append(match + " (" + file + ", line " + str(no+1) + ")")

              if '&' in identified_catch_statement:
                num_ref += 1
    
    if num_const == num_exceptions:
      feedback += "You consistently used const when catching exceptions, which is good practice that I covered in lectures. "
    elif num_const == 0:
      feedback += "When catching exceptions, you never caught your exception objects as const, which I covered in lectures as something you should be doing (no marks were deducted for this). An exception should not be changed once it has been thrown, thus we should always catch them using the const keyword. "
    elif num_const/num_exceptions > .75:
      feedback += "When catching exceptions, you caught nearly all of your exception objects as const, although you missed the const keyword a few times (no marks were deducted for this). "
    elif num_const/num_exceptions > .5:
      feedback += "When catching exceptions, you caught most of your exception objects as const, which I covered in lectures as something you should be doing (no marks were deducted for this). "
    elif num_const/num_exceptions > .25:
      feedback += "When catching exceptions, most of your exception objects weren't caught as const, which I covered in lectures as something you should be doing. An exception should not be changed once it has been thrown, thus we should always catch them using the const keyword (no marks were deducted for this in this case). "
    else:
      feedback += "When catching exceptions, the majority of your exception objects weren't caught as const, which I covered in lectures as something you should be doing. An exception should not be changed once it has been thrown, thus we should always catch them using the const keyword (no marks were deducted for this in this case). "

    if num_ref == num_exceptions:
      feedback += "You did catch them all as references, which means you avoided copies of the exception objects being made when they are thrown. "
    elif num_ref == 0:
      feedback += "Sadly, you didn't catch them as references, which means when an exception was thrown a copy of the exception object was made. "
      marks += -2
    elif num_ref/num_exceptions > .75:
      feedback += "You caught nearly all of the exceptions as references, but at times caught exceptions by value. This means that a copy of an exception object would be made when an exception is made. "
      marks += -1.25
    elif num_const/num_exceptions > .5:
      feedback += "You caught most of the exceptions as references, but at times caught exceptions by value. This means that a copy of an exception object would be made when an exception is made. "
      marks += -1.5
    elif num_const/num_exceptions > .25:
      feedback += "Sadly, you failed to catch most of the exceptions as references. This means that a copy of an exception object would be made when an exception is made. "
      marks += -1.75
    else:
      feedback += "Sadly, pretty much all of your exceptions were not caught as references. This means that a copy of an exception object would be made when an exception is made. "
      marks += -2
      
    feedback += "\n"
    if len(non_constref_exceptions) > 0:
      feedback += "\nThe places I noticed you failed to fully use constant references are:\n"
      for non_constref_exception in non_constref_exceptions:
        feedback += "  - " + non_constref_exception + "\n"
    feedback += "\n"

    return stage_result(
      updated_label    = "Exceptions checked (%d total, %d const, %d ref)" % (num_exceptions, num_const, num_ref),
      student_feedback = feedback,
      student_marks    = marks,
      next_stage       = "code_efficiency")



  def code_efficiency(student_id, marks, feedback): # max -13
    multidecision = [
        {
         "ref4":      ("Little to no use of pass-by-reference",                                                -2, "2.6. CODE EFFICIENCY\nYou didn't really use much pass-by-reference in your code, which means data ends up being needlessly copied around in your code. In future, think about whether a function needs a copy of a variable, or can rely upon a reference to the original variable.\n\n"),
         "ref3":      ("Could have used more instances of pass-by-reference",                                -1.5, "2.6. CODE EFFICIENCY\nYou did use pass-by-reference in some of your functions, which means data is not needlessly copied around in your code. There are a few more places where you could have done this though.\n\n"),
         "ref2":      ("Good coverage of pass-by-reference where appropriate",                                 -1, "2.6. CODE EFFICIENCY\nYou did use pass-by-reference in many of your functions, which means data is not needlessly copied around in your code. There are a few more places where you could have done this though. Keep it up :)\n\n"),
         "ref1":      ("Excellent use of pass-by-reference where appropriate",                                  0, "2.6. CODE EFFICIENCY\nYou did use pass-by-reference pretty much everywhere I expected it, which means data is not needlessly copied around in your code. Keep it up :)\n\n")
        },
        
        {
         "std1":      ("Used 'using namespace std;",                                                           -1, "You used 'using namespace std' in your code, which I strongly discouraged in lectures. "),
         "std0":      ("Did not use 'using namespace std'",                                                     0, ""),
        },
        
        {
         "nul1":      ("Used NULL instead of nullptr",                                                          0, "You should also watch for using NULL in C++ vs. nullptr. nullptr is always a null pointer type, whereas the definition of NULL is 0 (practically there is no difference but syntactically it is clearer—I haven't deducted any marks here for it—it is merely a recommendation). "),
         "nul0":      ("Did not use NULL instead of nullptr",                                                   0, "You used 'using namespace std' in your code, which I strongly discouraged in lectures. "),
        },

        {
         "redund4":   ("Quite a bit of redundant or repeated code",                                            -3, "There's a fair few instances of redundant/repeated code which could have been made more efficient (e.g., by moving them into separate functions).\n\n"),
         "redund3":   ("Some redundant or repeated code (e.g. could have been new functions)",                 -2, "You've included some instances of redundant/repeated code which could have been made more efficient (e.g.,  by moving them into separate functions).\n\n"),
         "redund2":   ("Maybe some redundant or repeated code",                                                -1, "Generally speaking, your solution avoids redundant/repeated code. Don't be afraid of refactoring code into separate functions to enhance readability and clarity of your code.\n\n"),
         "redund1":   ("No redundant or repeated code",                                                         0, "You've also managed to avoid redundant/repeated code throughout, for example, by adding in extra functions.\n\n")
        },
        
        {
         "hc2":       ("Multiple instances of hardcoded values",                                               -3, "There were a few places where you have hardcoded values/conditions etc. to pass unit tests. While this might seem to work and pass the tests, it means your code is not as generic as possible. We should always try to write functions that conform to a standard rather than for specific instances of data, as expected in industry.\n\n"),
         "hc1":       ("One instance of hardcoded values",                                                   -1.5, "It looks like you have hardcoded values/conditions etc. in your code to pass unit tests. While this might seem to work and pass the tests, it means your code is not as generic as possible. We should always try to write functions that conform to a standard rather than for specific instances of data, as expected in industry.\n\n"),
         "hc0":       ("Avoided hardcoding values",                                                             0, "Looking at your code, it's great to see that you avoided hardcoding values in conditions etc, meaning your code could also work with different datasets, for example. Writing generic functions is key in software development.\n\n"),
        },

        {
         "attempt0":  ("Attempted nothing",                                                                    -2, "3. SUMMARY\nSadly, you attempted very little of this coursework and "),
         "attempt1":  ("Attempted some things (and did not so well)",                                          -1, "3. SUMMARY\nAlthough you only attempted some of the tasks in this coursework, "),
         "attempt2":  ("Attempted some things (and did well)",                                                  0, "3. SUMMARY\nYou only attempted some of the tasks in this courserwork but "),
         "attempt3":  ("Attempted most things (and did not so well)",                                         -.5, "3. SUMMARY\nAlthough you attempted most of the tasks in this coursework, "),
         "attempt4":  ("Attempted most things (and did well)",                                                  0, "3. SUMMARY\nYou attempted most of the tasks in this coursework and "),
         "attempt5":  ("Attempted everything (and did not so well)",                                          -.5, "3. SUMMARY\nAlthough You attempted everything in this coursework, "),
         "attempt6":  ("Attempted everything (and did well)",                                                   0, "3. SUMMARY\nYou attempted everything in this coursework and "),
        },
        
        {
         "overall8":  ("  0/4, this is a very poor coursework (quality, not completeness)",                    -4, "there is a lot of scope for improvement. Much of this coursework's marks were achievable without completing all the tasks. Focusing on delivering good, but perhaps, incomplete code would have helped you achieve a higher mark. You must focus on revising this module now in preparation for the exam."),
         "overall7":  ("  1/4, this is a poor coursework (quality, not completeness)",                         -3, "this is an OK coursework, although there is a quite a bit of scope for improvement. Much of this coursework's marks were achievable without completing all the tasks. Focusing on delivering good, but perhaps, incomplete code would have helped you achieve a higher mark. You must focus on revising this module now in preparation for the exam."),
         "overall6":  ("1.5/4, this is a OK coursework (quality, not completeness)",                        -2.5, "this is an OK coursework, although there is a scope for improvement. Much of this coursework's marks were achievable without completing all the tasks. Focusing on delivering good, but perhaps, incomplete code would have helped you achieve a higher mark."),
         "overall5":  ("  2/4, this is a good coursework (quality, not completeness)",                         -2, "this is an good attempt. You have produced some good code, but there a quite a few areas where you could have improved. Use the feedback to re-examine and reflect upon your code."),
         "overall4":  ("2.5/4, this is a very good coursework (quality, not completeness)",                  -1.5, "this is an great attempt. You have produced some OK code, but there a few areas where you could have improved. Use the feedback to re-examine and reflect upon your code."),
         "overall3":  ("  3/4, this is a great coursework (quality, not completeness)",                        -1, "this is an excellent coursework solution. You have produced some nice code, although there is, as always, a little room for improvement."),
         "overall2":  ("3.5/4, this is a excellent coursework (quality, not completeness)",                  -0.5, "this is an excellent coursework solution. You have produced some nice code, although there is, as always, a little room for improvement."),
         "overall1":  ("  4/4: this is a perfect coursework (quality, not completeness)",                       0, "this is a perfect coursework solution. You have produced some great code. Well done!")
        }
      ]

    return stage_result(
      updated_label = "Marking finished",
      decision      = multidecision,
      next_stage    = "feedback")


  def feedback(student_id, marks, feedback):
    mark_catch = re.compile(r'SUMMARY OF AUTOMATED MARKING \(([0-9]+)\/')
    match = re.search(mark_catch, feedback)

    if match is not None:
      autograder_mark = int(match.group(1))
      goodness_mark = marks - autograder_mark
    else:
      return stage_result(
        updated_label    = "Couldn't find Autograder mark in feedback",
        student_feedback = feedback,
        next_stage       = None)

    feedback = feedback.replace('//goodness_total//', str(goodness_mark))
    
    cmd = coursework.CMD_OPEN_CODE + [coursework.MARKS_DIR + "/" + student_id + "-feedback.txt"]
    res = subprocess.run(cmd)
    return stage_result(
      updated_label    = "Marking finished",
      student_feedback = feedback,
      next_stage       = None)





      # TASK 4
      task4marks    = int(autograder_marks[test[catch2][provided]["06"]] + autograder_marks[test[catch2][provided]["07"]] + autograder_marks[test[catch2][extended]["05"]] + autograder_marks[test[catch2][extended]["02"]] + autograder_marks[test[catch2][provided]["09"]] + autograder_marks[test[catch2][extended]["04"]] + autograder_marks[test[catch2][extended]["03"]])
      task4possible =                                                  2 +                                              2 +                                              2 +                                              1 +                                              2 +                                              2 +                                              2
      
      feedback += "1.3. TASK 4: COMPLETE THE Measure AND Area CLASSES (" + str(task4marks) + "/" + str(task4possible) + ")\n"

      if autograder_marks[test[catch2][provided]["06"]] > 0:
        feedback += "Your Measure object can be instantiated as expected (test6.cpp), "

        if autograder_marks[test[catch2][provided]["07"]] > 0:
          feedback += "and also passes the second set of tests to verify that it can store data correctly (test7.cpp). "
        else:
          feedback += "however, it doesn't seem to manage storing data as expected according to the test suite in test7.cpp. "
      else:
        feedback += "Your Measure object doesn't seem to work as expected according to the test suite in test6.cpp "

        if autograder_marks[test[catch2][provided]["07"]] > 0:
          feedback += "but does at least store data correctly (test7.cpp). "
        else:
          feedback += "and also doesn't seem to manage storing data as expected according to the test suite in test7.cpp. "

      if autograder_marks[test[catch2][extended]["05"]] > 0:
        if autograder_marks[test[catch2][extended]["02"]] > 0:
          feedback += "Hidden tests confirm your Measure object converts codenames to lowercase and also handles the insert-and-merge functionality correctly.\n\n"
        else:
          feedback += "Hidden tests confirm your Measure object converts codenames to lowercase, but it the expected insert-and-merge functionality described in the block comments doesn't seem to work quite as expected.\n\n"
      else:
        if autograder_marks[test[catch2][extended]["02"]] > 0:
          feedback += "A hidden test shows that your Measure object doesn't convert codenames to lowercase as required. A second hidden test though does show that the insert-and-merge functionality works as expected.\n\n"
        else:
          feedback += "Hidden tests show that your Measure object doesn't convert codenames to lowercase as required or implement the object to handle insert-and-merging of values correctly. You should have paid closer attention to the block comments here.\n\n"

      if autograder_marks[test[catch2][provided]["09"]] > 0:
        if autograder_marks[test[catch2][extended]["04"]] > 0:
          feedback += "Your Area class can successfully contain Measure instances and cannot contain two Measure instances with the same codename (test9.cpp). When given two Measure instances with the same codename, your Area instance will merge them correctly. "

          if autograder_marks[test[catch2][extended]["03"]] > 0:
            feedback += "Also, your Areas instance will merge two Area instances correctly when they have the same local authority code.\n\n"
          else:
            feedback += "However, this merging functionality also doesn't work in the Areas class, which was meant to merge Area instances together when encountering two with the same local authority code.\n\n"
        else:
          feedback += "Your Area class can successfully contain Measure instances and cannot contain two Measure instances with the same codename (test9.cpp). Sadly, though, a hidden test confirms that when given two Measure instances with the same codename, your Area instance does not merge them correctly as described in the block comments in area.cpp. "

          if autograder_marks[test[catch2][extended]["03"]] > 0:
            feedback += "Despite that, your Areas instance will merge two Area instances correctly when they have the same local authority code.\n\n"
          else:
            feedback += "In line with this, this merging functionality also doesn't work in the Areas class, which was meant to merge Area instances together when encountering two with the same local authority code.\n\n"
      else:
        if autograder_marks[test[catch2][extended]["04"]] > 0:
          feedback += "Your Area class seems to have issues with containing Measure instances, ensuring that two Measure instances with the same codename can't co-exist (test9.cpp). However, when given two Measure instances with the same codename, your Area instance will merge them correctly as per the block comment in area.cpp. "

          if autograder_marks[test[catch2][extended]["03"]] > 0:
            feedback += "Equally, your Areas instance will merge two Area instances correctly when they have the same local authority code.\n\n"
          else:
            feedback += "Sadly, however, this functionality doesn't work in the Areas class, which was meant to merge Area instances together when encountering two with the same local authority code.\n\n"

        else:
          feedback += "Your Area class seems to have issues with containing Measure instances, ensuring that two Measure instances with the same codename can't co-exist (test9.cpp). Additionally, when given two Measure instances with the same codename, your Area instance does not merge them correctly as described in the block comments in area.cpp. "

          if autograder_marks[test[catch2][extended]["03"]] > 0:
            feedback += "However, your Areas instance will merge two Area instances correctly when they have the same local authority code.\n\n"
          else:
            feedback += "In line with this, this merging functionality also doesn't work in the Areas class, which was meant to merge Area instances together when encountering two with the same local authority code.\n\n"





      # TASK 5
      task5marks    = int(autograder_marks[test[output][provided]["03"]] + autograder_marks[test[output][extended]["01"]])
      task5possible =                                                  1 +                                              1
      
      feedback += "1.4. TASK 5: IMPLEMENT OUTPUT (" + str(task5marks) + "/" + str(task5possible) + ")\n"

      if autograder_marks[test[output][provided]["03"]] > 0:
        feedback += "When testing your code for outputs based on the areas argument, your program produced an empty JSON object when given a non-existent area (output test 3). "
      else:
        feedback += "When testing your code for outputs based on the areas argument, your code did not output an empty JSON object ({}) when given a non-existent area as had been asked (output test 3). This was stated in the block comment of Areas::toJSON() in areas.cpp. "

      if autograder_marks[test[output][extended]["01"]] > 0:
        feedback += "In testing this with other program arguments and requesting JSON output, your program also returned an empty JSON object.\n\n"
      else:
        feedback += "However, when testing this with other program arguments and requesting JSON output, your program did not return an empty JSON object as expected (we ran this with command bethyw -a W060000999 -y 0 -m rb,db,all -j).\n\n"





      # TASK 6
      task6marks    = int(autograder_marks[test[catch2][provided]["12"]] + autograder_marks[test[output][provided]["04"]] + autograder_marks[test[output][provided]["05"]] + autograder_marks[test[catch2][extended]["06"]] + autograder_marks[test[catch2][extended]["07"]] + autograder_marks[test[output][provided]["06"]] + autograder_marks[test[catch2][extended]["08"]] + autograder_marks[test[output][provided]["07"]] + autograder_marks[test[catch2][extended]["09"]] + autograder_marks[test[output][provided]["08"]])
      task6possible =                                                  2 +                                              1 +                                              1 +                                              2 +                                              2 +                                              1 +                                              2 +                                              1 +                                              2 +                                              1
      
      feedback += "1.5. TASK 6: IMPLEMENT WelshStatsJSON PARSING (" + str(task6marks) + "/" + str(task6possible) + ")\n"

      if autograder_marks[test[catch2][provided]["12"]] > 0:
        if autograder_marks[test[output][provided]["04"]] > 0:
          if autograder_marks[test[output][provided]["05"]] > 0:
            feedback += "Your program correctly imported and produced output for the dataset popu1009.json in both the tables and JSON output (test12.cpp and provided output tests 4 and 5). "
          else:
            feedback += "Your program correctly imported and produced output for the dataset popu1009.json in the tables output, although its JSON output didn't match what I was expecting (test12.cpp and provided output tests 4 and 5). "
        else:
          if autograder_marks[test[output][provided]["05"]] > 0:
            feedback += "Your program correctly imported and produced output for the dataset popu1009.json in the JSON output, but its tables output doesn't seem correct; note that I tested your tables output without spaces and line breaks to avoid this being an issue (test12.cpp and provided output tests 4 and 5). "
          else:
            feedback += "Your program correctly imported the dataset popu1009.json, but both the tables and JSON output didn't match what I was expecting; note that I tested your output without spaces and line breaks to avoid this being an issue (test12.cpp and provided output tests 4 and 5). "
      else:
        feedback += "Your program didn't seem to import the dataset popu1009.json as expected (test12.cpp)"

        if autograder_marks[test[output][provided]["04"]] > 0:
          if autograder_marks[test[output][provided]["05"]] > 0:
            feedback += "; however your program produced valid output for both the tables and JSON format (provided output tests 4 and 5), suggesting some issues with ensuring your API was compatible with what was expected. "
          else:
            feedback += "; however your program correctly generated the tables output but not the JSON output (provided output tests 4 and 5), suggesting some issues with ensuring your API was compatible with what was expected. "
        else:
          if autograder_marks[test[output][provided]["05"]] > 0:
            feedback += "; however your program produced valid output for the JSON output, but not the tables output (provided output tests 5 and 4), suggesting some issues with your class. "
          else:
            feedback += " and correspondingly your code produced invalid output too (provided output tests 4 and 5). "

      if autograder_marks[test[catch2][extended]["06"]] > 0:
        feedback += "Your implementation of the three statistics functions passed my test for them.\n\nWith regards to the other JSON-based datasets:\n"
      else:
        feedback += "Your implementation of the three statistics functions don't seem to pass my test for them?\n\nWith regards to the other JSON-based datasets:\n"

      if autograder_marks[test[catch2][extended]["07"]] > 0:
        if autograder_marks[test[output][provided]["06"]] > 0:
          feedback += "- Your program parses and imports the econ0080.json file correctly, and its JSON output is also correct for this dataset (provided output 6)\n"
        else:
          feedback += "- Your program parses the econ0080.json file correctly, although its JSON output is not correct for this dataset (provided output 6)\n"
      else:
        if autograder_marks[test[output][provided]["06"]] > 0:
          feedback += "- Your program doesn't parse the econ0080.json file correctly, although its JSON output is correct for this dataset (provided output 6)\n"
        else:
          feedback += "- Your program doesn't parse the econ0080.json file correctly and as a result its JSON output is incorrect c(provided output 6)\n"

      if autograder_marks[test[catch2][extended]["08"]] > 0:
        if autograder_marks[test[output][provided]["07"]] > 0:
          feedback += "- Your program parses and imports the envi0201.json file correctly, and its JSON output is also correct for this dataset (provided output 7)\n"
        else:
          feedback += "- Your program parses the envi0201.json file correctly, although its JSON output is not correct for this dataset (provided output 7)\n"
      else:
        if autograder_marks[test[output][provided]["07"]] > 0:
          feedback += "- Your program doesn't parse the envi0201.json file correctly, although its JSON output is correct for this dataset (provided output 7)\n"
        else:
          feedback += "- Your program doesn't parse the envi0201.json file correctly and as a result its JSON output is incorrect c(provided output 7)\n"

      if autograder_marks[test[catch2][extended]["09"]] > 0:
        if autograder_marks[test[output][provided]["08"]] > 0:
          feedback += "- Your program parses and imports the tran0152.json file correctly, and its JSON output is also correct for this dataset (provided output 8)\n"
        else:
          feedback += "- Your program parses the tran0152.json file correctly, although its JSON output is not correct for this dataset (provided output 8)\n"
      else:
        if autograder_marks[test[output][provided]["08"]] > 0:
          feedback += "- Your program doesn't parse the tran0152.json file correctly, although its JSON output is correct for this dataset (provided output 8)\n"
        else:
          feedback += "- Your program doesn't parse the tran0152.json file correctly and as a result its JSON output is incorrect c(provided output 8)\n"






      # TASK 7
      task7marks    = int(autograder_marks[test[catch2][extended]["10"]] + autograder_marks[test[catch2][extended]["10a"]] + autograder_marks[test[output][provided]["09"]] + autograder_marks[test[output][provided]["10"]] + autograder_marks[test[output][extended]["06"]] + autograder_marks[test[output][extended]["06a"]])
      task7possible =                                                  2 +                                               0 +                                               1 +                                              1 +                                              1 +                                               0
      
      feedback += "\n1.6. TASK 7: IMPLEMENT AuthorityByYearCSV PARSING (" + str(task7marks) + "/" + str(task7possible) + ")\n"

      if autograder_marks[test[catch2][extended]["10"]] > 0:
        feedback += "A hidden Catch2 test confirmed that your program parses the complete-popu1009-popden.csv file correctly. "

        if autograder_marks[test[output][provided]["09"]] > 0:
          feedback += "Likewise, the output matched the expected output for this dataset (provided output 9). "
        else:
          feedback += "However, the output did not match the expected output for this dataset (provided output 9). "

      else:
        feedback += "A hidden Catch2 test indicates that your program does not parse the complete-popu1009-popden.csv as expected. "

        if autograder_marks[test[output][provided]["09"]] > 0:
          feedback += "However, the output matched the expected output for this dataset (provided output 9). "
        else:
          feedback += "Likewise, the output did not match the expected output for this dataset (provided output 9). "

      if autograder_marks[test[output][provided]["10"]] > 0:
        feedback += "The output for the complete-popu1009-pop.csv dataset was correct (provided output 9).\n\n"
      else:
        feedback += "The output for the complete-popu1009-pop.csv dataset didn't match what I expected (provided output 9).\n\n"

      if autograder_marks[test[output][provided]["06"]] > 0 or autograder_marks[test[output][provided]["06a"]] > 0:
        feedback += "When looking at the output for the command bethyw -a W06000015,W06000011 -y 2015 -j, your program gave an expected output. Note that there were two possible outputs expected here depending on how you interpreted the requirement to add Area and Measures instances for previously un-encountered areas/measures (i.e., you could have decided to always create an Area/Measure instance for a previously un-encountered area/measure and then apply the filtering to decide whether to import the data. Alternatively, you could have applied the filter first before deciding to create the Area/Measure instances). I initially intended the former but encountered both during marking and its clear the initial requirements were ambiguous (demonstrating the difficulty in writing precise specifications!).\n"
      else:
        feedback += "When looking at the output for the command bethyw -a W06000015,W06000011 -y 2015 -j, it looks like your program doesn't have an expected output. Note that there were two possible outputs expected here depending on how you interpreted the requirement to add Area and Measures instances for previously un-encountered areas/measures (i.e., you could have decided to always create an Area/Measure instance for a previously un-encountered area/measure and then apply the filtering to decide whether to import the data. Alternatively, you could have applied the filter first before deciding to create the Area/Measure instances). I initially intended the former but encountered both during marking and its clear the initial requirements were ambiguous (demonstrating the difficulty in writing precise specifications!).\n"






      # TASK 8
      task8marks    = int(autograder_marks[test[output][extended]["02"]] + autograder_marks[test[output][extended]["02a"]] + autograder_marks[test[output][provided]["10"]] + autograder_marks[test[output][extended]["03"]] + autograder_marks[test[output][extended]["04"]] + autograder_marks[test[output][extended]["05"]] + autograder_marks[test[output][extended]["05a"]])
      task8possible =                                                  1 +                                               0 +                                              1 +                                              1 +                                              1 +                                              1 +                                              0
      
      feedback += "\n1.7. TASK 8: IMPLEMENT EXTENED ARGUMENT FILTERING (" + str(task8marks) + "/" + str(task8possible) + ")\nFor this task, there were a variety of different output tests:\n"

      if autograder_marks[test[output][provided]["02"]] > 0 or autograder_marks[test[output][provided]["02a"]] > 0:
        feedback += "- The output for the command bethyw -a swan -m RAIL was exactly as I expected\n"
      else:
        feedback += "- The output for the command bethyw -a swan -m RAIL didn't seem to match what was expected (even accounting for the two interpretations of the filtering)\n"

      if autograder_marks[test[output][provided]["03"]] > 0:
        feedback += "- The output for the command bethyw -d popden -a swan -m RAIL was exactly as I expected\n"
      else:
        feedback += "- The output for the command bethyw -d popden -a swan -m RAIL didn't seem to match what was expected\n"

      if autograder_marks[test[output][provided]["04"]] > 0:
        feedback += "- The output for the command bethyw -d popden -a Abertawe,Swansea was exactly as I expected\n"
      else:
        feedback += "- The output for the command bethyw -d popden -a Abertawe,Swansea didn't seem to match what was expected\n"

      if autograder_marks[test[output][provided]["05"]] > 0 or autograder_marks[test[output][provided]["05a"]] > 0:
        feedback += "- The output for the command bethyw -a swan,card -m pop,rail -y 2010-2018 -j was exactly as I expected\n"
      else:
        feedback += "- The output for the command bethyw -a swan,card -m pop,rail -y 2010-2018 -j didn't seem to match what was expected (even accounting for the two interpretations of the filtering)\n"

      return stage_result(
        updated_label    = "Autograder marks imported and feedback generated",
        student_feedback = feedback,
        student_marks    = int(autograder_marks['Total Points']),
        next_stage       = "opensrc")
    except KeyError as e:
      return stage_result(
        updated_label = "Error with autograder import:" + str(e),
        next_stage    = None)


  def opensrc(student_id, marks, feedback):
    cmd = coursework.CMD_OPEN_CODE + [coursework.TEST_SRC_DIR]
    res = subprocess.run(cmd)
    return stage_result(
      updated_label     = "Source code opened in external application",
      next_stage        = "negative_marking_switch")



  def negative_marking_switch(student_id, marks, feedback):
      return stage_result(
          updated_label    = "Added 40 marks, remaining parts are negative marked... (" + str(marks) + " marks were for tests)",
          next_stage       = "tables_output",
          student_marks    = 40)


  def tables_output(student_id, marks, feedback): # max: -2 marks
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "bethyw.cpp",
           "input.cpp",
           "areas.cpp",
           "area.cpp",
           "measure.cpp",
           "main.cpp",
           "-o",
           "./bin/bethyw"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

    if res.returncode == 0:
      cmd = ["./bin/bethyw",
             "popden"]
      res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)
    
      stdout = res.stdout.decode("utf-8")
      stderr = res.stderr.decode("utf-8")

      if res.returncode == 0 and stderr == "":
        preamble = "\n2.0 GOODNESS (//goodness_total///40)\nThe marking for this section is based on a qualitative assessment of the code you produced for this assignment. This has been broken out, for clarity, over a number of subsections below.\n\n"
        multidecision = [
            {
             "out4":      ("Output is wrong",                         -2, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting doesn't seem right. Perhaps something went wrong somewhere? For this I looked at the 'popden' and compared it to what I expected."),
             "out3":      ("Output is very messy",                    -2, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting is a messy. You were given sample outputs and it was also explained that this should be human-readable, formatted in a table-like manner where all the values were aligned. "),
             "out2":      ("Output is messy",                         -1, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting is a bit messy, and could have been clearer. "),
             "out1":      ("Output is not quite perfect",              0, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting is neat and readable. "),
             "out0":      ("Output is perfect",                        0, preamble + "2.1. FORMATTED 'TABLES' OUTPUT\nYour output for the tables formatting is very neat and readable. ")
            },
            {
             "stats2":    ("<skip stats point>",                       0, ""),
             "stats1":    ("Statistics NOT included",                  0, "You did not include the required statistics in your output. "),
             "stats0":    ("Statistics included",                      0, "You did included the required statistics in your output, which is great. ")
            },
            {
             "noareas3":  ("<skip areas with no data point>",          0, ""),
             "noareas2":  ("Areas with no data missing",               0, "When an area has no measures or data, I was expecting something like <no measures> or <no data> to be printed to signify this.\n\n"),
             "noareas1":  ("Areas with no data messy",                 0, "When an area has no measures, I was expecting something like <no measures> or <no data> to be printed to signify this, and for this to be clear to the user.\n\n"),
             "noareas0":  ("Areas with no data fine",                  0, "You did include areas which had no data given the current filters, clearly denoting this.\n\n")
            },
        ]
        
        return stage_result(
          updated_label    = "Sample tables output generated",
          view_text        = ("Output from ./bin/bethyw -d popden -m area -y 1992-1995", stdout),
          decision         = multidecision,
          next_stage       = "memtest")

    return stage_result(
      updated_label    = "Couldn't compile and run coursework with tables table",
      next_stage       = "memtest",
      student_marks    = -2)
        

    if not os.path.isfile(coursework.TEST_SRC_DIR + "/README.md"):
      return stage_result(
        updated_label = "Tables output checked",
        next_stage    = "memtest")

    with open(coursework.TEST_SRC_DIR + "/README.md", "r") as f:
      contents = f.read()

    return stage_result(
      updated_label = "README.md included and opened",
      view_text     = ("README.md", contents),
      next_stage    = "memtest")


  def memtest(student_id, marks, feedback): # max: 0 marks
    return stage_result(
      updated_label = "Skipping Valgrind",
      next_stage    = "input_source")

    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "bethyw.cpp",
           "input.cpp",
           "areas.cpp",
           "area.cpp",
           "measure.cpp",
           "main.cpp",
           "-ggdb3",
           "-o",
           "./bin/bethyw"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

    if res.returncode != 0:
      # details = ' '.join(cmd) + "\n\n"
      details = res.stderr.decode("utf-8")

      return stage_result(
        updated_label = "Could not compile the coursework with GCC {0}".format(res.returncode),
        next_stage    = None,
        details       = details)

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

    feedback += "MEMORY LEAKS\n"
    valgrind_response = res.stderr.decode("utf-8")

    with open(coursework.MARKS_DIR + "/" + student_id + '-valgrind.txt', 'w') as file:
      file.write(valgrind_response)

    if valgrind_response.find("All heap blocks were freed") > 0:
      feedback += "Great work, your code has no memory leaks.\n\n"
      return stage_result(
          updated_label    = "Coursework passed memory leak test",
          next_stage       = "input_source",
          student_feedback = feedback,
          student_marks    = 0)
    else:
      feedback += "It seems that your code contains a one or more memory leaks. You should make sure you free any memory you allocate on the heap. In reality, you should have used good RAII principles taught in lectures and not needed to handle memory management at all.\n\n"
      return stage_result(
          updated_label    = "Coursework was found to contain memory leaks",
          next_stage       = "input_source",
          student_marks    = -2,
          student_feedback = feedback)


  def input_source(student_id, marks, feedback): # max -1
    multidecision = [
        {
         "inpt2":     ("InputSource and InputFile functions + destructor aren't virtual",                     -1, "\n\n2.2. INHERITANCE\nYou didn't make the InputSource and InputFile functions and destructor all virtual, as required. "),
         "inpt1":     ("InputSource and InputFile functions + destructor are virtual",                         0, "\n\n2.2. INHERITANCE\nIn InputSource and InputFile, you correctly used virtual functions, including with a virtual destructor."),
        },
      ]

    return stage_result(
      updated_label = "InputSource and InputFile functions checked",
      decision      = multidecision,
      next_stage    = "function_ordering")



  def function_ordering(student_id, marks, feedback): # max -.5 marks
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
        student_feedback = feedback + "\n\n2.3. CODE STYLE\nThank you for keeping the functions in the same order as in the provided code. This makes it easier to mark your work. ",
        student_marks    = 0,
        next_stage       = "not_const_functions")
    else:
      return stage_result(
        updated_label    = "The student didn't keep the functions in order",
        student_feedback = feedback + "\n\n2.3. CODE STYLE\nYou were asked to keep the functions in the same order as they were given to you in the block comments. Not doing this makes it significantly harder to mark your work. ",
        student_marks    = -.5,
        next_stage       = "not_const_functions")



  def not_const_functions(student_id, marks, feedback): # max -2 marks
    marks = 0
    not_consty = []

    # test area for const
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "area.cpp",
           "-o",
           "area"]
    res = subprocess.run(cmd, cwd='./_constcheck', capture_output=True)
    if res.returncode != 0:
      marks = -.6
    else:
      res = subprocess.run(["./area"], cwd='./_constcheck', capture_output=True)
      stdout = res.stdout.decode("utf-8")

      if "getLocalAuthorityCode() = 0" in stdout:
        marks -= .2
        not_consty.append("Area::getLocalAuthorityCode()")
      if "getName() = 0" in stdout:
        marks -= .2
        not_consty.append("Area::getName()")
      if "size() = 0" in stdout:
        marks -= .2
        not_consty.append("Area::size()")

    # test areas for const
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "areas.cpp",
           "-o",
           "areas"]
    res = subprocess.run(cmd, cwd='./_constcheck', capture_output=True)
    if res.returncode != 0:
      marks = -.2
    else:
      res = subprocess.run(["./areas"], cwd='./_constcheck', capture_output=True)
      stdout = res.stdout.decode("utf-8")

      if "size() = 0" in stdout:
        marks -= .2
        not_consty.append("Areas::size()")

    # test measure for const
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "measure.cpp",
           "-o",
           "measure"]
    res = subprocess.run(cmd, cwd='./_constcheck', capture_output=True)
    if res.returncode != 0:
      marks = -1.2
    else:
      res = subprocess.run(["./measure"], cwd='./_constcheck', capture_output=True)
      stdout = res.stdout.decode("utf-8")
      if "getCodename() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getCodename()")
      if "getLabel() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getLabel()")
      if "size() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::size()")
      if "getDifference() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getDifference()")
      if "getDifferenceAsPercentage() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getDifferenceAsPercentage()")
      if "getAverage() = 0" in stdout:
        marks -= .2
        not_consty.append("Measure::getAverage()")

    if marks == -.2:
      feedback += "In the various block comments in the comment, I expected various class functions to be declared as const (i.e., to be callable in a constant context). You did this well, although missed this for "
      for function in not_consty:
        feedback += function + '. '
    elif marks < -.2:
      feedback += "\n\nIn the various block comments in the comment, I expected the following class functions to be declared as const (i.e., to be callable in a constant context):\n"
      for function in not_consty:
        feedback += '  - ' + function + '\n'
      feedback += '\n'
    else:
      feedback += 'Well done for also correctly declaring the various requested functions as const. '

    return stage_result(
      updated_label    = "Deducted %f marks for non-const functions" % marks,
      next_stage       = "aggressive_warnings",
      student_feedback = feedback,
      student_marks    = marks)



  def aggressive_warnings(student_id, marks, feedback): # max -5.5 marks
    cmd = [coursework.GPP_COMMAND,
           "--std=c++14",
           "-pedantic",
           "-Wall",
           "-Wextra",
           "-Wcast-qual",
           "-Wctor-dtor-privacy",
           "-Wdisabled-optimization",
           "-Wformat=2",
           "-Winit-self",
           "-Wuninitialized",
           "-Wlogical-op",
           "-Wmissing-declarations",
           "-Wmissing-include-dirs",
           "-Wnoexcept",
           "-Woverloaded-virtual",
           "-Wredundant-decls",
           "-Wshadow",
           "-Wsign-promo",
           "-Wstrict-null-sentinel",
           "-Wstrict-overflow=5",
           "-Wswitch-default",
           "-Wundef",
           "-Werror",
           "-Wno-unused",
           "bethyw.cpp",
           "input.cpp",
           "areas.cpp",
           "area.cpp",
           "measure.cpp",
           "main.cpp",
           "-o",
           "./bin/bethyw"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)
    stdout = res.stdout.decode("utf-8")
    stderr = res.stderr.decode("utf-8")

    if res.returncode == 0 and stderr == "":
      return stage_result(
        updated_label    = "Coursework compiled without any warnings, despite all the extra flags",
        next_stage       = "code_style")

    else:
      quality_errors = {
        # string in gcc output : (marks to deduce, num regex matches, regex match, feedback, friends)
        'casts away qualifiers':                  (1, 2, r'([a-zA-Z.]*):([0-9]+)',            "It seems your code casts away some qualifiers (e.g. const) from variables, which is typically an indication of trouble in your code and bad practice. You should always work to honour qualifiers such as const rather than overriding them. The first occurence of this I spotted was in __ on line __."),

        'used uninitialized':                     (1, 2, r'([a-zA-Z.]*):([0-9]+)',            "You have used a variable that is uninitalised in your code, without initialising it. I discussed this in lectures and labs. This is incredibly easy to do as this is a case of 'undefined behaviour' (i.e., some compilers on some platforms will automatically initalise variables for you and some won't). However, I treated this as bad practice as you were advised in lectures to avoid doing this. The first occurence I spotted was in __ on line __."),

        'of equal expressions':                   (1, 2, r'([a-zA-Z.]*):([0-9]+)',            "There is some suspect logic in __ on line __—you seem testing the same thing twice in your logical test?"),

        'no previous declaration for':            (1, 2, r"([a-zA-Z.]*)[^']*'(.*)'",          "I asked you to always declare functions in header files before implementing them, but it seems you didn't always manage this, as in __ with the free function __.", ['no declaration matches']),
        'no declaration matches':                 (1, 2, r"([a-zA-Z.]*)[^']*'(.*)'",          "It seems that the although you provided an implementation in __ for the function __, there isn't a matching declaration of it?. I asked to you make sure you always included declarations for your functions in the appropriate header files.", ['no previous declaration for']),

        'shadows a parameter':                    (1, 3, r"([a-zA-Z.]*):([0-9]+)[^']*'(.*)'", "You've inadvertently shadowed a variable. This is where you create a variable inside a given scope, when it has been always declared in a higher scope or as a parameter (as in this case). The first place I spotted this was in __ on line __ with the __.", ['shadows a local', 'shadows a previous local', 'shadows a member']),
        'shadows a local':                        (1, 3, r"([a-zA-Z.]*):([0-9]+)[^']*'(.*)'", "You've inadvertently shadowed a variable. This is where you create a variable inside a given scope, when it has been always declared in a higher scope (as in this case) or where you declare a variable with the same name as a parameter. The first place I spotted this was in __ on line __ with the __.", ['shadows a member', 'shadows a previous local', 'shadows a parameter']),
        'shadows a previous local':               (1, 3, r"([a-zA-Z.]*):([0-9]+)[^']*'(.*)'", "You've inadvertently shadowed a variable. This is where you create a variable inside a given scope, when it has been always declared in a higher scope (as in this case) or where you declare a variable with the same name as a parameter. The first place I spotted this was in __ on line __ with the __.", ['shadows a member', 'shadows a local', 'shadows a parameter']),
          'shadows a member':                       (1, 3, r"([a-zA-Z.]*):([0-9]+)[^']*'(.*)'", "You've inadvertently shadowed a member variable. This is where you create a variable inside a given scope, when it has been always declared in a higher scope (a member variable in this case) or where you declare a variable with the same name as a parameter. The first place I spotted this was in __ on line __.", ['shadows a local', 'shadows a previous local', 'shadows a parameter']),

        'switch missing default case':            (.5, 2, r'([a-zA-Z.]*):([0-9]+)',            "You seem to have a switch statement in __ on __ that doesn't have a default value. This may be OK in this case, but typically one would be expected (e.g., to catch unexpected values).")
      }
      feedback_list = []
      found_quality_errors = []
      marks_subtraction = 0

      for line in stderr.split("\n"):
        for gcc_str, parse in quality_errors.items():
          if gcc_str not in found_quality_errors:
            if gcc_str in line:
              stderr = ("!! Found '%s'\n" % gcc_str) + stderr
              re_position_in_code = re.compile(parse[2])
              match = re.search(re_position_in_code, line)
              if match is not None:
                temp_feedback = parse[3]
                for i in range(0, parse[1]):
                  temp_feedback = temp_feedback.replace("__", match.group(i+1), 1)
                feedback_list.append(temp_feedback)
                marks_subtraction -= parse[0]

                found_quality_errors.append(gcc_str)
                try:
                  for friend_match in parse[4]:
                    found_quality_errors.append(friend_match)
                except:
                  pass
              else:
                pass

      marks_subtraction = max(-5, marks_subtraction)

      if len(feedback_list) == 0:
        return stage_result(
          updated_label    = "Deducted %d marks for warnings" % -(marks_subtraction),
          details          = "No automatically detected issues thus no marks could be automatically deducted. Please read the output below and prepare to modify the students feedback to include the issues highlighted!\n\n" + stderr,
          next_stage       = "code_style")

      elif len(feedback_list) == 1:
        lower = lambda s: s[:1].lower() + s[1:] if s else ''
        feedback += "While reviewing your code, I noticed the following that " + lower(feedback_list[0]) + "\n"

      elif len(feedback_list) > 1:
        feedback += "\n\nWhile reviewing your code, I noticed the following that:\n"
        for i, feedback_item in enumerate(feedback_list):
          feedback += '  ' + str(i+1) + ". " + feedback_item + "\n"

      return stage_result(
        updated_label    = "Deducted %f marks for warnings" % (-marks_subtraction),
        details          = stderr,
        next_stage       = "code_style",
        student_feedback = feedback + "\n",
        student_marks    = marks_subtraction)



  def code_style(student_id, marks, feedback): # max -16
    multidecision = [
        {
         "messy1":    ("Indentation/code style is very messy or inconsistent",                                 -2, "Your use of indentation and general code style seems somewhat inconsistent and messy. "),
         "messy2":    ("Indentation/code style is a little messy/mostly OK",                                   -1, "Your use of indentation and general code style seems occasionally inconsistent and messy. "),
         "messy3":    ("Indentation is perfect",                                                                0, "Your use of indentation and general code style is consistent. "),
        },

        {
         "comments5": ("No commenting",                                                                        -2, "You haven't really used any comments of note in your work. In future, you should use comments to explain complex chunks of code that may not be obvious at first glance. "),
         "comments4": ("Alright commenting (i.e. have used them if needed)",                                 -1.5, "Your use of commenting is OK. Remember, you only need comments to explain complex chunks of code rather than individual lines. You were told to assume that the people marking your work know C++. In future, focus on providing explanatory comments rather than comments that merely repeat what can be gleamed from code. "),
         "comments3": ("Excessive commenting given the complexity of the code",                                -1, "You have used a few too many comments in your coursework solution. Remember, you only need comments to explain complex chunks of code rather than individual lines. You were told to assume that the people marking your work know C++. "),
         "comments2": ("Could have included additional comments to explain complex chunks of code",            -1, "You could have used some more comments in your coursework solution to help readers of your code understand complex code blocks. "),
         "comments1": ("Good commenting in relevant places",                                                    0, "You have used commenting well throughout your coursework solution. Comments help readers of your code understand complex code blocks. ")
        },
        
        {
         "naming4":   ("Poor naming of variables ",                                                            -1, "You don't seem to have adopted a convention when it comes to naming your elements such as variables. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments. Remember, the names of variables if for humans reading your code and not the machine, so don't simply default to giving simplistic names, e.g., i, except in limited cased (e.g., iterators).\n\n", 0),
         "naming3":   ("OK naming of variables and functions (e.g. some variables are not descriptive)",      -.5, "In terms of naming convention, you could have shown greater care with naming your elements such as variables. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments. Remember, the names of variables if for humans reading your code and not the machine, so don't simply default to giving simplistic names, e.g., i, except in limited cased (e.g. iterators).\n\n", 1),
         "naming2":   ("Generally good naming of variables and functions",                                    -.5, "In terms of naming convention, you have used good naming of variables etc. in your code. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments.\n\n", 2),
         "naming1":   ("Consistently excellent naming of variables and functions",                              0, "In terms of naming convention, you have consistently used good naming of variables etc. in your code. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments.\n\n", 3)
        },
        
        {
         "const5":    ("No use of the const keyword with variables",                                           -2, "You don't seem to have used const in any significant way in your coursework. Using const wherever you will not be modifying a value or rely upon a variable to not change is good practice.\n\n"),
         "const4":    ("Little use of the const keyword with variables",                                       -2, "In terms of using const for non-modifiable variables and references, there are a few places where you could have used this where you did not. Using const wherever you will not be modifying a value or rely upon a variable to not change is good practice.\n\n"),
         "const3":    ("Could have used more instances of the const keyword with variables",                 -1.5, "In terms of using const for non-modifiable variables and references, there are a few places where you could have used this where you did not. Using const wherever you will not be modifying a value or rely upon a variable to not change is good practice.\n\n"),
         "const2":    ("Good use of the const keyword for variables",                                          -1, "In terms of using const for non-modifiable variables and references, you've used this well. Using const wherever you will not be modifying a value or rely upon a variable to not change is good practice.\n\n"),
         "const1":    ("Perfect use of the const keyword for variables",                                        0, "In terms of using const for non-modifiable variables and references, you've used this very well.\n\n"),
        },
        
        {
         "nd2":       ("Missing delete/delete [] for a new/new []",                                            -2, "There are a few places where you should have used delete/delete [] to ensure you have deallocated memory on the heap that you allocated with the new/new [] keywords. I covered this quite a few times in lectures that with C and C++, memory management is still the responsibility of the developer. "),
         "nd0":       ("delete/delete []'d everything they have new/new []'d",                               -0.5, "You used the new/new [] keywords in your code to allocate data on the heap, but also used the delete/delete [] keywords to free this memory. This is good, although generally speaking we should try to avoid newing and deleting as much as possible. "),
         "nd1":       ("No use of new/delete",                                                                  0, "You haven't used new/delete anywhere, which is great. As I covered in lectures, this introduces challenges, e.g., when we start to also mix in things like exceptions which sidestep the typical flow of execution. "),
        },
        
        {
         "if3":       ("Missing delete/delete [] with stream in InputFile",                                    -2, "It seems your InputSource/InputFile instances store a pointer but it's not clear where this is deleted. Remember, whenever we new, we must delete. This is also complicated by exceptions, which sidestep the normal flow of execution.  You could have used something like std::unique_ptr here, storing the stream as a member variable, or put more code in try...catch blocks to avoid this. "),
         "if2":       ("delete with stream in InputFile, but what about exceptions?",                          -1, "It seems your InputSource/InputFile instances store a pointer that gets deleted in the destructor, although it's not clear if this would get cleaned up if an exception was thrown in your code. You could have used something like std::unique_ptr here, storing the stream as a member variable, or put more code in try...catch blocks to avoid this."),
         "if1":       ("Use of std::unique_ptr or equivalent in InputFile",                                     0, "You have used a Standard Library RAII function, which is excellent practice and demonstrates great engagement with the topics discussed in lectures. Great work!"),
         "if0":       ("Stored the stream as a member variable",                                                0, "You have avoided using new/delete inside InputFile, which given we want to avoid this as much as possible, is good practice to keep up."),
        },
        
        {
         "div1":      ("Measure::getAverage/Difference/DifferenceAsPercentage() susceptible to div/0",         -2, "\n\nIn your implementation of the statistics functions in the Measure class, your code seems to be susceptible to a division by 0 error, which would have crashed your application. You should make sure you are not dividing by zero ever in code. This is a runtime error and hard to catch, but a common source of issues."),
         "div0":      ("Measure::getAverage/Difference/DifferenceAsPercentage() protected against size() = 0",  0, "")
        },
        
        {
         "pop2":      ("No populate functions handle nullptr",                                                 -2, "\n\nYour populate…() functions in areas.cpp don't seem to look for/check for nullptr being passed in with the filter arguments. You should always check parameter inputs in your functions, especially if they are pointers, before trying to do anything with them."),
         "pop1":      ("Some populate functions handle nullptr",                                               -1, "\n\nIn seems some your populate…() functions in areas.cpp don't seem to look for/check for nullptr being passed in in with the filter arguments. You should always check parameter inputs in your functions, especially if they are pointers, before trying to do anything with them."),
         "pop0":      ("All populate functions handle nullptr",                                                 0, "\n\nYour populate…() functions in areas.cpp are checking for nullptr on the filter arguments! This was an area where it was incredibly easy to forget to do this.")
        },
      ]

    return stage_result(
      updated_label = "Code style checking finished",
      decision      = multidecision,
      next_stage    = "extra_features")



  def extra_features(student_id, marks, feedback): # max +3
    multidecision = [
        {
         "pa2":       ("No extra program arguments",                                                           0, "\n\n2.4. EXTRA FEATURES\n"),
         "pa1":       ("Good extra program arugments",                                                         1, "\n\n2.4. EXTRA FEATURES\nThe extra features, including program arguments, you added are nice. "),
         "pa0":       ("Redundant extra program arguments",                                                    0, "\n\n2.4. EXTRA FEATURES\n"),
        },
        
        {
         "oo2":       ("No operator overloading",                                                               0, "You didn't seem to overload any operators except for what was explicitly asked. This is fine as you weren't expected to, but you could look into this in the future. "),
         "oo1":       ("Sensible operator overloading",                                                         1, "You overloaded some additional operators too, which was great. Operator overloading is a nice feature in C++ we should try to use it as much as we can (where it makes sense). "),
         "oo0":       ("Redundant operator overloading",                                                        0, "You overloaded some additional operators too, which was great. Operator overloading is a nice feature in C++ we should try to use it as much as we can (where it makes sense). I can't see much use of it in your coursework, but that's fine. "),
        },

        {
         "tests2":    ("No extra tests",                                                                       0, "You could have written some extra tests for catching edge cases, if you wanted. "),
         "tests1":    ("Sensible extra tests",                                                                 1, "Adding extra test cases was a nice touch! "),
         "tests0":    ("Redundant extra tests",                                                                0, "Adding extra test cases was a good idea, although the tests provided seem redundant? "),
        },
        
        {
         "x1":        ("No extra features",                                                                     0, "You didn't include any extra features, which was fine. You weren't asked too."),
         "x0":        ("They had extra features",                                                               0, ""),
        },
    ]

    return stage_result(
      updated_label = "Extra features checking finished",
      decision      = multidecision,
      next_stage    = "exceptions")



  def exceptions(student_id, marks, feedback): # max -4
    # Wildcard catch test
    files = ["bethyw.cpp",
             "bethyw.h",
             "input.cpp",
             "input.h",
             "areas.cpp",
             "areas.h",
             "area.cpp",
             "area.h",
             "measure.cpp",
             "measure.h"]
    found_in = []

    for file in files:
      with open(coursework.TEST_SRC_DIR + "/" + file, 'r') as f:
        all_lines = ''.join(f.readlines())
        wildcard_catch = re.compile(r'catch\s*\(\s*...\s*\)')
        match = re.search(wildcard_catch, all_lines)
        if match is not None:
          found_in.append(file)
          break

    if len(found_in) > 0:
      mark = -2
      feedback += "\n\n2.5. EXCEPTIONS\nFirstly, disappointingly, despite being asked not to do so, you had a wildcard catch(...) in your code. I found this in "
      for i, filename in enumerate(found_in):
        feedback += filename
        if i + 2 == len(found_in):
          feedback += ' and '
        elif i + 1 < len(found_in):
          feedback += ', '
      feedback += '.'
    else:
      feedback += "\n\n2.5. EXCEPTIONS\n"
      marks = 0

    # Const reference catch check
    files = ["bethyw.cpp",
             "bethyw.h",
             "input.cpp",
             "input.h",
             "areas.cpp",
             "areas.h",
             "area.cpp",
             "area.h",
             "measure.cpp",
             "measure.h"]
    found_in = []

    num_exceptions = 0
    num_const = 0
    num_ref = 0
    non_constref_exceptions = []
    re_catch = re.compile(r'catch\s*\(\s*([^)]*)\s*\)')
    for file in files:
      identified_catch_statements = []

      with open("_tempsrc/" + file, 'r') as f:
        for no, line in enumerate(f.readlines()):
          matches = re.findall(re_catch, line)  

          for match in matches:
            num_exceptions += 1
            identified_catch_statement = ''.join(match)

            if 'const ' in identified_catch_statement:
              num_const += 1
              if '&' in identified_catch_statement:
                num_ref += 1
            else:
              non_constref_exceptions.append(match + " (" + file + ", line " + str(no+1) + ")")

              if '&' in identified_catch_statement:
                num_ref += 1
    
    if num_const == num_exceptions:
      feedback += "You consistently used const when catching exceptions, which is good practice that I covered in lectures. "
    elif num_const == 0:
      feedback += "When catching exceptions, you never caught your exception objects as const, which I covered in lectures as something you should be doing (no marks were deducted for this). An exception should not be changed once it has been thrown, thus we should always catch them using the const keyword. "
    elif num_const/num_exceptions > .75:
      feedback += "When catching exceptions, you caught nearly all of your exception objects as const, although you missed the const keyword a few times (no marks were deducted for this). "
    elif num_const/num_exceptions > .5:
      feedback += "When catching exceptions, you caught most of your exception objects as const, which I covered in lectures as something you should be doing (no marks were deducted for this). "
    elif num_const/num_exceptions > .25:
      feedback += "When catching exceptions, most of your exception objects weren't caught as const, which I covered in lectures as something you should be doing. An exception should not be changed once it has been thrown, thus we should always catch them using the const keyword (no marks were deducted for this in this case). "
    else:
      feedback += "When catching exceptions, the majority of your exception objects weren't caught as const, which I covered in lectures as something you should be doing. An exception should not be changed once it has been thrown, thus we should always catch them using the const keyword (no marks were deducted for this in this case). "

    if num_ref == num_exceptions:
      feedback += "You did catch them all as references, which means you avoided copies of the exception objects being made when they are thrown. "
    elif num_ref == 0:
      feedback += "Sadly, you didn't catch them as references, which means when an exception was thrown a copy of the exception object was made. "
      marks += -2
    elif num_ref/num_exceptions > .75:
      feedback += "You caught nearly all of the exceptions as references, but at times caught exceptions by value. This means that a copy of an exception object would be made when an exception is made. "
      marks += -1.25
    elif num_const/num_exceptions > .5:
      feedback += "You caught most of the exceptions as references, but at times caught exceptions by value. This means that a copy of an exception object would be made when an exception is made. "
      marks += -1.5
    elif num_const/num_exceptions > .25:
      feedback += "Sadly, you failed to catch most of the exceptions as references. This means that a copy of an exception object would be made when an exception is made. "
      marks += -1.75
    else:
      feedback += "Sadly, pretty much all of your exceptions were not caught as references. This means that a copy of an exception object would be made when an exception is made. "
      marks += -2
      
    feedback += "\n"
    if len(non_constref_exceptions) > 0:
      feedback += "\nThe places I noticed you failed to fully use constant references are:\n"
      for non_constref_exception in non_constref_exceptions:
        feedback += "  - " + non_constref_exception + "\n"
    feedback += "\n"

    return stage_result(
      updated_label    = "Exceptions checked (%d total, %d const, %d ref)" % (num_exceptions, num_const, num_ref),
      student_feedback = feedback,
      student_marks    = marks,
      next_stage       = "code_efficiency")



  def code_efficiency(student_id, marks, feedback): # max -13
    multidecision = [
        {
         "ref4":      ("Little to no use of pass-by-reference",                                                -2, "2.6. CODE EFFICIENCY\nYou didn't really use much pass-by-reference in your code, which means data ends up being needlessly copied around in your code. In future, think about whether a function needs a copy of a variable, or can rely upon a reference to the original variable.\n\n"),
         "ref3":      ("Could have used more instances of pass-by-reference",                                -1.5, "2.6. CODE EFFICIENCY\nYou did use pass-by-reference in some of your functions, which means data is not needlessly copied around in your code. There are a few more places where you could have done this though.\n\n"),
         "ref2":      ("Good coverage of pass-by-reference where appropriate",                                 -1, "2.6. CODE EFFICIENCY\nYou did use pass-by-reference in many of your functions, which means data is not needlessly copied around in your code. There are a few more places where you could have done this though. Keep it up :)\n\n"),
         "ref1":      ("Excellent use of pass-by-reference where appropriate",                                  0, "2.6. CODE EFFICIENCY\nYou did use pass-by-reference pretty much everywhere I expected it, which means data is not needlessly copied around in your code. Keep it up :)\n\n")
        },
        
        {
         "std1":      ("Used 'using namespace std;",                                                           -1, "You used 'using namespace std' in your code, which I strongly discouraged in lectures. "),
         "std0":      ("Did not use 'using namespace std'",                                                     0, ""),
        },
        
        {
         "nul1":      ("Used NULL instead of nullptr",                                                          0, "You should also watch for using NULL in C++ vs. nullptr. nullptr is always a null pointer type, whereas the definition of NULL is 0 (practically there is no difference but syntactically it is clearer—I haven't deducted any marks here for it—it is merely a recommendation). "),
         "nul0":      ("Did not use NULL instead of nullptr",                                                   0, "You used 'using namespace std' in your code, which I strongly discouraged in lectures. "),
        },

        {
         "redund4":   ("Quite a bit of redundant or repeated code",                                            -3, "There's a fair few instances of redundant/repeated code which could have been made more efficient (e.g., by moving them into separate functions).\n\n"),
         "redund3":   ("Some redundant or repeated code (e.g. could have been new functions)",                 -2, "You've included some instances of redundant/repeated code which could have been made more efficient (e.g.,  by moving them into separate functions).\n\n"),
         "redund2":   ("Maybe some redundant or repeated code",                                                -1, "Generally speaking, your solution avoids redundant/repeated code. Don't be afraid of refactoring code into separate functions to enhance readability and clarity of your code.\n\n"),
         "redund1":   ("No redundant or repeated code",                                                         0, "You've also managed to avoid redundant/repeated code throughout, for example, by adding in extra functions.\n\n")
        },
        
        {
         "hc2":       ("Multiple instances of hardcoded values",                                               -3, "There were a few places where you have hardcoded values/conditions etc. to pass unit tests. While this might seem to work and pass the tests, it means your code is not as generic as possible. We should always try to write functions that conform to a standard rather than for specific instances of data, as expected in industry.\n\n"),
         "hc1":       ("One instance of hardcoded values",                                                   -1.5, "It looks like you have hardcoded values/conditions etc. in your code to pass unit tests. While this might seem to work and pass the tests, it means your code is not as generic as possible. We should always try to write functions that conform to a standard rather than for specific instances of data, as expected in industry.\n\n"),
         "hc0":       ("Avoided hardcoding values",                                                             0, "Looking at your code, it's great to see that you avoided hardcoding values in conditions etc, meaning your code could also work with different datasets, for example. Writing generic functions is key in software development.\n\n"),
        },

        {
         "attempt0":  ("Attempted nothing",                                                                    -2, "3. SUMMARY\nSadly, you attempted very little of this coursework and "),
         "attempt1":  ("Attempted some things (and did not so well)",                                          -1, "3. SUMMARY\nAlthough you only attempted some of the tasks in this coursework, "),
         "attempt2":  ("Attempted some things (and did well)",                                                  0, "3. SUMMARY\nYou only attempted some of the tasks in this courserwork but "),
         "attempt3":  ("Attempted most things (and did not so well)",                                         -.5, "3. SUMMARY\nAlthough you attempted most of the tasks in this coursework, "),
         "attempt4":  ("Attempted most things (and did well)",                                                  0, "3. SUMMARY\nYou attempted most of the tasks in this coursework and "),
         "attempt5":  ("Attempted everything (and did not so well)",                                          -.5, "3. SUMMARY\nAlthough You attempted everything in this coursework, "),
         "attempt6":  ("Attempted everything (and did well)",                                                   0, "3. SUMMARY\nYou attempted everything in this coursework and "),
        },
        
        {
         "overall8":  ("  0/4, this is a very poor coursework (quality, not completeness)",                    -4, "there is a lot of scope for improvement. Much of this coursework's marks were achievable without completing all the tasks. Focusing on delivering good, but perhaps, incomplete code would have helped you achieve a higher mark. You must focus on revising this module now in preparation for the exam."),
         "overall7":  ("  1/4, this is a poor coursework (quality, not completeness)",                         -3, "this is an OK coursework, although there is a quite a bit of scope for improvement. Much of this coursework's marks were achievable without completing all the tasks. Focusing on delivering good, but perhaps, incomplete code would have helped you achieve a higher mark. You must focus on revising this module now in preparation for the exam."),
         "overall6":  ("1.5/4, this is a OK coursework (quality, not completeness)",                        -2.5, "this is an OK coursework, although there is a scope for improvement. Much of this coursework's marks were achievable without completing all the tasks. Focusing on delivering good, but perhaps, incomplete code would have helped you achieve a higher mark."),
         "overall5":  ("  2/4, this is a good coursework (quality, not completeness)",                         -2, "this is an good attempt. You have produced some good code, but there a quite a few areas where you could have improved. Use the feedback to re-examine and reflect upon your code."),
         "overall4":  ("2.5/4, this is a very good coursework (quality, not completeness)",                  -1.5, "this is an great attempt. You have produced some OK code, but there a few areas where you could have improved. Use the feedback to re-examine and reflect upon your code."),
         "overall3":  ("  3/4, this is a great coursework (quality, not completeness)",                        -1, "this is an excellent coursework solution. You have produced some nice code, although there is, as always, a little room for improvement."),
         "overall2":  ("3.5/4, this is a excellent coursework (quality, not completeness)",                  -0.5, "this is an excellent coursework solution. You have produced some nice code, although there is, as always, a little room for improvement."),
         "overall1":  ("  4/4: this is a perfect coursework (quality, not completeness)",                       0, "this is a perfect coursework solution. You have produced some great code. Well done!")
        }
      ]

    return stage_result(
      updated_label = "Marking finished",
      decision      = multidecision,
      next_stage    = "feedback")


  def feedback(student_id, marks, feedback):
    mark_catch = re.compile(r'SUMMARY OF AUTOMATED MARKING \(([0-9]+)\/')
    match = re.search(mark_catch, feedback)

    if match is not None:
      autograder_mark = int(match.group(1))
      goodness_mark = marks - autograder_mark
    else:
      return stage_result(
        updated_label    = "Couldn't find Autograder mark in feedback",
        student_feedback = feedback,
        next_stage       = None)

    feedback = feedback.replace('//goodness_total//', str(goodness_mark))
    
    cmd = coursework.CMD_OPEN_CODE + [coursework.MARKS_DIR + "/" + student_id + "-feedback.txt"]
    res = subprocess.run(cmd)
    return stage_result(
      updated_label    = "Marking finished",
      student_feedback = feedback,
      next_stage       = None)

