
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
  MARKS_DIR = os.getcwd() + "/_marks"

  def __init__(self, student_id):
    self.stdscr        = None
    self.start_pos     = 0
    self.auto_progress = True

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
    self.progress["catch2"]           = stage("Compile Catch2 binary",                                      coursework.catch2)
    self.progress["setup"]            = stage("Copy student's submission into temporary marking directory", coursework.setup)
    self.progress["readme"]           = stage("Read the student's README",                                  coursework.readme)
    self.progress["git"]              = stage("Review Git commits",                                         coursework.git)
    self.progress["opensrc"]          = stage("Begin reading through the student's code",                   coursework.opensrc)
    self.progress["compile"]          = stage("Compile the student's coursework and check for warnings",    coursework.compile)
    self.progress["unittest"]         = stage("Test the student's coursework against automated tests",      coursework.unittest)
    self.progress["memtest"]          = stage("Run the coursework with Valgrind",                           coursework.memtest)
    self.progress["function_ordering"]= stage("Check that they have retained the ordering of functions",    coursework.function_ordering)
    self.progress["quality"]          = stage("Evaluate the coding quality",                                coursework.quality)
    #self.progress["feedback"]         = stage("Modify the feedback",                                        coursework.feedback)

    self.current_stage = "catch2"

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


  def catch2(student_id, marks, feedback):
    if os.path.isfile(coursework.CATCH2_EXE):
      return stage_result("Catch2 already compiled", "setup")

    cmd = ["g++",
           "--std=c++11",
           "-c",
           coursework.ORIG_SRC_DIR + "/libs/catch2/catch_main.cpp",
           "-o",
           coursework.CATCH2_EXE]

    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
      return stage_result("Could not compile Catch2 binary", -1)

    return stage_result("Catch2 binary successfully compiled", "setup")


  def __rmdir(directory):
    if os.path.isdir(directory):
      for root, dirs, files in os.walk(directory):
        for file in files:
          os.remove(os.path.join(root, file))

      shutil.rmtree(directory)


  def setup(student_id, marks, feedback):
    coursework.__rmdir(coursework.TEST_SRC_DIR)
    shutil.copytree(coursework.ORIG_SRC_DIR, coursework.TEST_SRC_DIR)

    try:
      shutil.copy("./" + student_id + "/README.md",
                  coursework.TEST_SRC_DIR + "/README.md")
    except FileNotFoundError:
      pass

    try:
      shutil.copytree("./" + student_id + "/.git",
                      coursework.TEST_SRC_DIR + "/.git")
    except FileNotFoundError:
      pass

    try:
      shutil.copytree("./" + student_id + "/src",
                      coursework.TEST_SRC_DIR + "/src")
    except FileNotFoundError:
      return stage_result(
        updated_label = "Student src/ directory missing",
        next_stage    = None)

    return stage_result(
      updated_label = "Student files successfilly copied into temporary marking directory",
      next_stage    = "readme")


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
      next_stage    = "git")


  def git(student_id, marks, feedback):
    feedback = "USE OF GIT\n"
    if os.path.isdir(coursework.TEST_SRC_DIR + "/.git"):
      cmd = coursework.CMD_OPEN_GIT + [coursework.TEST_SRC_DIR]
      res = subprocess.run(cmd)

      decision = {
          "excellent": ("Perfect use of granular commits, few files at a time, and commit messages",      10, feedback + "You have used Git very well, committing work as you go and using relevant Git messages. In large projects with multiple collorators committing work simulatenously on different parts of a codebase, being able to fully track, understand (and potentially revert) commits is key.\n\n",),
          "good":      ("Some granular commits and good messages, but not quite perfect",                  8,  feedback + "You have used Git very well, committing work as you go and using relevant Git messages. In large projects with multiple collorators committing work simulatenously on different parts of a codebase, being able to fully track, understand (and potentially revert) commits is key.\n\n",),
          "ok":        ("Some large commits or poor commit messages",                                      6,  feedback + "Overall, your use of Git is OK, but could have been better. For higher marks, you should have made sure to perform granular commits (i.e. only committing a change or two at a time) with accurate messages. In large projects with multiple collorators committing work simulatenously on different parts of a codebase, being able to fully track, understand (and potentially revert) commits is key. You were asked to try and stick to good practice in your coursework. \n\n"),
          "poor":      ("Many large Git commits covering many changes and/or poor use of commit messages", 4,  feedback + "Your use of Git is starting to get a bit messy. You should avoid commit lots of code in a single commit, and avoid simplistic messages that don't describe what happened in the commit.  In large projects with multiple collorators committing work simulatenously on different parts of a codebase, being able to fully track, understand (and potentially revert) commits is key. You were asked to try and stick to good practice in your coursework.\n\n"),
          "bad":       ("Basically non-existant use of Git",                                               2,  feedback + "Although you included your .git/ directory, it seems that you barely used Git, and certainly did not make the granular commit messages that you were expected to make.  In large projects with multiple collorators committing work simulatenously on different parts of a codebase, being able to fully track, understand (and potentially revert) commits is key. You were asked to try and stick to good practice in your coursework.\n\n")}

      return stage_result(
        updated_label = ".git/ directory opened in external application",
        decision      = decision,
        next_stage    = "opensrc")
    else:
      feedback += "You did not include your .git/ directory, thus you will receive 0 marks for this coursework. You were told multiple times in lectures and in the coursework specification that you must include the .git/ directory.\n\n"
      return stage_result(
        updated_label     = "No .git/ directory included - maximum marks set to 0",
        student_feedback  = feedback,
        student_max_marks = 0,
        next_stage        = "opensrc")


  def opensrc(student_id, marks, feedback):
    cmd = coursework.CMD_OPEN_CODE + [coursework.TEST_SRC_DIR + "/src"]
    res = subprocess.run(cmd)
    return stage_result(
      updated_label     = "Source code opened in external application",
      next_stage        = "compile")


  def compile(student_id, marks, feedback):
    cmd = ["g++",
           "--std=c++14",
           "-Wall",
           "./src/bethyw.cpp",
           "./src/input.cpp",
           "./src/areas.cpp",
           "./src/area.cpp",
           "./src/measure.cpp",
           "./main.cpp",
           "-ggdb3",
           "-o",
           "./bin/bethyw"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)
    stdout = res.stdout.decode("utf-8")

    if res.returncode == 0 and stdout == "":
      feedback =  "COMPILATION\n"
      feedback += "Your code compiles without issuing any warnings from the compiler, which is great. You should never be submitting code with errors or warnings, even if the code is incomplete.\n\n"
      return stage_result(
        updated_label    = "Coursework compiled without warnings",
        next_stage       = "unittest",
        student_feedback = feedback,
        student_marks    = 5)

    elif res.returncode == 0 and stdout.find("warning") > -1:
      feedback =  "COMPILATION\n"
      feedback += "It looks like your code has some warnings from the compiler? You should aim to always produce code that has no warnings or errors, even if it is incomplete and does not implement all the functionality. This was a relatively easy area to pick up some marks (i.e. the code you were given compiles without warnings already).\n\n"
      return stage_result(
        updated_label    = "Coursework compiled with warnings",
        next_stage       = "unittest",
        student_feedback = feedback,
        student_marks    = 0)

    elif res.returncode != 0:
      feedback =  "COMPILATION\n"
      feedback += "It seems that your code does not compile. Did you modify files outside of the src/ directory in your solution or did you try and compile this with a different compiler? This was the core part of this assessment: producing code to prescribed documentation and tests, and its a shame that your code doesn't even compile to do that. As your code does not compile we cannot test it with the unit and automated output tests, and thus represents a significant chunk of the marks that you could have gained. If you were having issues of this nature, you should have raised these early on in the Canvas discussion for the coursework or in the labs.\n\n"

      # details = ' '.join(cmd) + "\n\n"
      details = res.stderr.decode("utf-8")

      return stage_result(
        updated_label    = "Coursework failed to compile with result {0}".format(res.returncode),
        next_stage       = "quality",
        student_feedback = feedback,
        student_marks    = 0,
        details          = details)


  def __unittest_compile(unittest):
    cmd = ["g++",
           "-O0",
           "--std=c++14",
           "-Wall",
           "./src/bethyw.cpp",
           "./src/input.cpp",
           "./src/areas.cpp",
           "./src/area.cpp",
           "./src/measure.cpp",
           "./tests/" + unittest + ".cpp",
            coursework.CATCH2_EXE,
            "-o",
            "./bin/bethyw-" + unittest]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

    if res.returncode == 0:
      return True
    else:
      return res.stderr.decode("utf-8") 


  def unittest(student_id, marks, feedback):
    test_files = [
      "test1",
      "test2",
      "test3",
      "test4",
      "test5",
      "test6",
      "test7",
      "test8",
      "test9",
      "test10",
      "test11",
      "test12",
      "testus1",
      "testus2",
      "testus3",
      "testus4",
      "testus5",
      "testus6",
      "testus7",
      "testus8",
      "testus9",
      "testus10"
    ]

    all_scenarios = {
      "[args][datasets]"                    : (1, "unit", "seen",   "The datasets program argument can be parsed correctly"),
      "[areas][args]"                       : (1, "unit", "seen",   "The areas program argument can be parsed correctly"),
      "[args][measures]"                    : (1, "unit", "seen",   "The measures program argument can be parsed correctly"),
      "[args][years]"                       : (1, "unit", "seen",   "The year program argument can be parsed correctly"),
      "[InputFile][existent]"               : (2, "unit", "seen",   "A source file can be opened and read"),
      "[InputFile][nonexistent]"            : (1, "unit", "seen",   "A nonexistant source file cannot be opened for reading"),
      "[Measure][construct]"                : (2, "unit", "seen",   "A Measure object can be constructed with a codename and label"),
      "[Measure][populate]"                 : (2, "unit", "seen",   "A Measure object can be populated with values"),
      "[Area][construct]"                   : (1, "unit", "seen",   "An Area instance be constructed with a local authority code"),
      "[Area][names]"                       : (2, "unit", "seen",   "An Area instance can have names in multiple languages"),
      "[Areas<>][construct]"                : (1, "unit", "seen",   "An Areas<> instance can be constructed"),
      "[Areas<>][contain]"                  : (3, "unit", "seen",   "An Areas<> instance can contain Area instances"),
      "[Areas<>][authorityCodeCSV]"         : (3, "unit", "seen",   "areas.csv can be correctly parsed"),
      "[Area][Measures]"                    : (2, "unit", "seen",   "An Area instance can contain Measure instances"),
      "[Areas<>][popu1009]"                 : (4, "unit", "unseen", "popu1009.json can be correctly parsed"),
      "[args][extended][years]"             : (1, "unit", "unseen", "The year program argument can be parsed correctly [extended]"),
      "[Measure][extended][populate]"       : (1, "unit", "unseen", "A Measure object can be populated with values [extended]"),
      "[Areas<>][contain][extended]"        : (1, "unit", "unseen", "An Areas<> instance can contain Area instances [extended]"),
      "[Area][Measures][extended]"          : (1, "unit", "unseen", "An Area instance can contain Measure instances [extended]"),
      "[Areas<>][extended][popu1009]"       : (1, "unit", "unseen", "popu1009.json can be correctly parsed [extended for non-lowercase]"),
      "[Areas<>][popu1009][statistics]"     : (2, "unit", "unseen", "Statistics can be correctly calculated from imported data"),
      "[Areas<>][econ0080]"                 : (2, "unit", "unseen", "econ0080.json can be correctly parsed"),
      "[Areas<>][envi0201]"                 : (2, "unit", "unseen", "envi0201.json can be correctly parsed"),
      "[Areas<>][tran0152]"                 : (4, "unit", "unseen", "tran0152.json can be correctly parsed"),
      "[Areas<>][complete-popu1009-popden]" : (4, "unit", "unseen", "complete-popu1009-popden.csv can be correctly parsed")
    } # total = 46    
    
    test_files_attempted = 0
    test_files_compiled  = 0
    test_files_failed    = 0
    
    num_total_scenarios  = 0
    num_passed_scenarios = 0
    num_failed_scenarios = 0
    passed_scenarios = []
    failed_scenarios = []
    
    num_total_tests  = 0
    num_passed_tests = 0
    num_failed_tests = 0

    total_marks = 0
    
    # changes neede, test_files_failed => add feedback on tests scripts can't compile due to missing setions

    df = pd.DataFrame(columns = ["student","filename", "tags", "result"])
    df = df.astype({"student": int})
    df = df.astype({"filename": str})
    df = df.astype({"tags": str})
    df = df.astype({"result": str})
    
    for test_file in iter(test_files):
      test_files_attempted += 1
      compile_result = coursework.__unittest_compile(test_file)

      if compile_result is not True:
        test_files_failed += 1  
        with open(coursework.MARKS_DIR + "/" + student_id + '-catch2-' + test_file +'.txt', 'w') as file:
          file.write("Could not compile:\n" + compile_result)
      else:
        test_files_compiled += 1
        cmd = ["./bin/bethyw-" + test_file, "-r", "xml"]
        res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

        catch2xml  = res.stdout.decode("utf-8")
        with open(coursework.MARKS_DIR + "/" + student_id + '-catch2-' + test_file +'.xml', 'w') as file:
          file.write(catch2xml)

        # Parse Catch2 unit tests outcomes
        root = ET.XML(catch2xml)
        
        for result in root.iter("OverallResults"):
          total_tests  = int(result.get("successes"))
          total_tests += int(result.get("expectedFailures"))
          total_tests += int(result.get("failures"))

          passed_tests  = int(result.get("successes"))
          passed_tests += int(result.get("expectedFailures"))
          failed_tests  = int(result.get("failures"))
          break

        for group in root.iter("Group"):
          for scenario in group.iter("TestCase"):
            num_total_scenarios += 1

            scenario_label = scenario.get("name").replace('Scenario: ', '')

            for overall_result in scenario.iter("OverallResult"):
              if overall_result.get("success") == "true":
                result = "pass"

                num_passed_scenarios += 1
                passed_scenarios.append(scenario.get("tags"))
              
                marks = all_scenarios[scenario.get("tags")][0]
                total_marks += marks
              else:
                result = "fail"

                num_failed_scenarios += 1
                failed_scenarios.append(scenario.get("tags"))
              break
            break
          break

        num_total_tests += total_tests
        num_passed_tests += passed_tests
        num_failed_tests += failed_tests
        df = df.append({"student"         : student_id,
                        "filename"        : scenario.get("filename"),
                        "tags"            : scenario.get("tags"),
                        "result"          : result,
                        "scenario"        : scenario_label,
                        "marks"           : marks,
                        "tests_passed"    : passed_tests,
                        "tests_failed"    : failed_tests},
                        ignore_index=True)

    df.to_csv(coursework.MARKS_DIR + "/" + student_id + '-catch2.csv', index=False)

    # Report compilation 
    feedback  = "FUNCTIONAL TESTING\nWe tried to run your code through {0} different tests scripts (including the 12 which had been shared with you in advance). Some of these tests examined individual functions, whereas some assessed your overall program performance.\n\n".format(test_files_attempted)
    feedback += "With your coursework, {0}/{1} of the test files compiled successfuly. Compilation fails in situations where you have not implemented the functions in the expected/requested format, e.g. return type, function arguments, const etc. don't match what is expected in the test script, thus g++ fails to compile the script with your code. ".format(test_files_compiled, test_files_attempted)
    if test_files_compiled == test_files_attempted:
      feedback += "The fact that all the test files compiled is a great indication In addition to compiling with all the tests, "
    elif test_files_compiled >= (test_files_attempted/4*3):
      feedback += "The fact that most the test files compiled is a great indication. In addition to compiling with most the tests, "
    elif test_files_compiled >= (test_files_attempted/2):
      feedback += "A good number of the test files compiled, which is a great start. Of the tests which compiled, "
    elif test_files_compiled == 0:
      feedback += "Sadly, none of the test files failed to compile with your coursework. Given you were provided quite a few of the tests, this is somewhat dissapointing. The total list of scenarios was:\n"
    elif test_files_compiled == 1:
      feedback += "Your code compiled with just 1 test. Given you were provided quite a few of the tests, this is somewhat dissapointing. Of the tests which compiled, "
    elif test_files_compiled < (test_files_attempted/4):
      feedback += "Your code compiled with less than 25% of the tests. Given you were provided quite a few of the tests, this is somewhat dissapointing. Of the tests which compiled, "
    else:
      feedback += "Your code compiled with less than half of the tests. Given you were provided quite a few of the tests, this is somewhat dissapointing. Of the tests which compiled, "
      
    found_tags = []
    if test_files_compiled > 0:
      if test_files_compiled == test_files_attempted and num_passed_scenarios == num_total_scenarios:
        feedback += "your code passed the following {0} scenarios, which was all of them!. The tests were:\n".format(num_passed_scenarios)
      elif num_passed_scenarios == num_total_scenarios:
        feedback += "your code passed the following {0} scenarios (which was all of those which compiled). The list of passing tests was:\n".format(num_passed_scenarios)
      elif num_passed_scenarios >= (num_total_scenarios/4*3):
        feedback += "your code passed {0} tests. The list of passing tests was:\n".format(num_passed_scenarios)
      elif num_passed_scenarios == 0:
        feedback += "sadly none of them passed.\n"
      elif num_passed_scenarios == 1:
        feedback += "your code passed {0}. The passing test was:\n".format(num_passed_scenarios)
      elif num_passed_scenarios >= (num_total_scenarios/2):
        feedback += "your code passed {0}. The list of passing tests was:\n".format(num_passed_scenarios)
      elif num_passed_scenarios < (num_total_scenarios/4):
        feedback += "{0} passed. The list of passing tests was:\n".format(num_passed_scenarios)
      
      for passed_scenario in iter(passed_scenarios):
        found_tags.append(passed_scenario)
        feedback += "  - " + all_scenarios[passed_scenario][3] + "\n"

      if num_failed_scenarios == 1:
        feedback += "\nThere was {0} scenario where your code did not pass:\n".format(num_failed_scenarios)
      elif num_failed_scenarios > 0:
        feedback += "\nThere were {0} scenarios where your code did not pass the tests:\n".format(num_failed_scenarios)
        for failed_scenario in iter(failed_scenarios):
          feedback += "  - " + all_scenarios[failed_scenario][3] + "\n"

      if test_files_failed > 0:
        feedback += "\nThe files your code did not compile with correctly contained the following scenarios:\n"

    if test_files_failed > 0:
      for tag, scenario in all_scenarios.items():
        if tag not in found_tags: 
          feedback += "  - " + scenario[3] + "\n"

    feedback += "\n"

    return stage_result(
      updated_label    = "Testing completed ({0} compiled, {1} not compiled, {2} scenarios passed, {3} scenarios failed)".format(test_files_compiled, test_files_failed, num_passed_scenarios, num_failed_scenarios),
      next_stage       = "memtest",
      student_feedback = feedback, #TODO
      student_marks    = total_marks) # TODO


  def memtest(student_id, marks, feedback):
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
              "Areas<>::Areas()",
              "Areas<>::setArea",
              "Areas<>::setArea",
              "Areas<>::getArea",
              "Areas<>::wildcardCountSet",
              "Areas<>::isLocalAuthorityFiltered",
              "Areas<>::size",
              "Areas<>::populateFromAuthorityCodeCSV",
              "Areas<>::populateFromWelshStatsJSON",
              "Areas<>::populateFromAuthorityByYearCSV",
              "Areas<>::populate",
              "Areas<>::populate",
              "Areas<>::toJSON"],

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
      with open(coursework.TEST_SRC_DIR + "/src/" + filename) as file:
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