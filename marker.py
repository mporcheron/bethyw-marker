
import curses
import curses.textpad
import collections
import emoji
import math
import os
import pandas as pd
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

# curses implementation based on PyRadio: https://pypi.org/project/pyradio/

class marker:
  def __init__(self, student_id):
    self.stdscr = None
    self.start_pos = 0
    self.student_id = student_id
    self.status = "Initialise marker system"
    
    self.marks_breakdown = collections.OrderedDict()
    self.marks = 0
    self.total_marks = 100
    self.max_marks = self.total_marks
    self.feedback = ""
    
    self.busy_dots = 0
    self.busy_timer = None
    self.busy_timer_stop = False
    
    self.error_details = ""
    
    self.progress = collections.OrderedDict()
    self.progress["catch2"]           = stage("Compile Catch2 binary", coursework.catch2)
    self.progress["setup"]            = stage("Copy student's submission into temporary marking directory", coursework.setup)
    self.progress["git"]              = stage("Review Git commits", coursework.git)
    self.progress["readme"]           = stage("Read the student's README", coursework.readme)
    self.progress["compile"]          = stage("Compile the student's coursework and check for warnings", coursework.compile)
    self.progress["unittest_compile"] = stage("Compile the student's coursework with Catch2", coursework.unittest_compile)
    self.progress["unittest"]         = stage("Test the student's coursework against automated tests", coursework.unittest)
    self.progress["memtest"]          = stage("Run the coursework with Valgrind", coursework.memtest)
    self.progress["quality"]          = stage("Evaluate the coding quality", coursework.quality)

    self.current_stage = "catch2"
    self.is_active = True
    
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
    curses.init_pair(1,  curses.COLOR_CYAN,    curses.COLOR_BLACK)
    curses.init_pair(2,  curses.COLOR_BLUE,    curses.COLOR_BLACK)
    curses.init_pair(3,  curses.COLOR_WHITE,   curses.COLOR_RED)
    curses.init_pair(4,  curses.COLOR_GREEN,   curses.COLOR_BLACK)
    curses.init_pair(5,  curses.COLOR_WHITE,   curses.COLOR_BLACK)
    curses.init_pair(6,  curses.COLOR_BLACK,   curses.COLOR_MAGENTA)
    curses.init_pair(8,  curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(9,  curses.COLOR_GREEN,   curses.COLOR_BLACK)
    curses.init_pair(10, curses.COLOR_WHITE,   curses.COLOR_BLUE)

    self.setup()
    
    self.status = "Awaiting input..."
    self.refresh_command()

    self.make_progress()
    
    while True:
      try:
        c = self.win_command.getch()
        if self.current_stage != None and c == ord('y'):
          self.make_progress()
        elif c == ord('q'):
          break
      except KeyboardInterrupt:
          break

    self.write_feedback()


  def write_feedback(self):
    with open("_marks/marks.csv", "a") as f:
      f.write(self.student_id + "," + str(min(self.marks, self.max_marks)))
      for key, marks in self.marks_breakdown.items():
        f.write("," + str(marks))
      f.write("\n")


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
    self.win_title.bkgd(' ', curses.color_pair(10) | curses.A_BOLD)
    self.win_title.addstr(1, 2, "CSC371 20/21 Marker", curses.color_pair(10)) 

    self.refresh_marks()
    self.win_title.noutrefresh()


  def refresh_marks(self):
    marks = min(self.marks, self.max_marks)

    text = "{0} ({1}/{2})".format(self.student_id, marks, self.total_marks)
    student_id_x = self.max_x - len(text) - 2

    self.win_title.addstr(1, student_id_x, text, curses.color_pair(10))
    self.win_title.refresh()


  def setup_body(self):
    self.max_y_body, self.max_x_body = self.win_body.getmaxyx()
    self.win_body.noutrefresh()
    self.refresh_body()


  def refresh_body(self, function = None):
    self.win_body.erase()
    self.win_body.move(3, 1)

    max_display = self.max_y_body - 1

    if function == None:
      function = self.show_progress
    function(max_display)

    self.win_body.refresh()


  def setup_command(self):
    self.win_command.noutrefresh()
    self.refresh_command()

    
  def refresh_command(self, awaiting_input=True):
    try:
      self.busy_timer_stop = True
    except AttributeError:
      pass

    self.win_command.erase()
    self.win_command.box()
    
    self.win_command.addstr(1, 2, "Current stage:", curses.color_pair(1)) 
    self.win_command.addstr(1, 17, self.status, curses.color_pair(5) | curses.A_BOLD) 

    if self.is_active:
      if awaiting_input:
        if self.current_stage == None:
          text = "Completed [q]"
        else:
          text = "Progress? [y/n]"
        progress_x = self.max_x - len(text) - 2
        self.win_command.addstr(1, progress_x, text, curses.color_pair(8) | curses.A_BOLD)
        self.win_command.refresh()
      else:
        self.busy_timer_stop = False
        self.busy_timer = threading.Timer(0, self.refresh_command_ticker)
        self.busy_timer.daemon = True
        self.busy_timer.start()
  
  
  def refresh_command_ticker(self):
    while not self.busy_timer_stop:
      text = "             "
      progress_x = self.max_x - len(text) - 5
      busy_dots = 1 + self.busy_dots
      for i in range(0, 3):
        text += "." if i < busy_dots else " "

      self.busy_dots = ((self.busy_dots + 1) % 3)
      self.win_command.addstr(1, progress_x, text, curses.color_pair(4) | curses.A_BOLD)
      self.win_command.refresh()
      time.sleep(.6)


  def setup_decision(self, decision):
    start_y = 10
    start_x = 10
    height = len(decision) + 5
    width = self.max_x - 20
    
    self.win_decision = curses.newwin(height, width, start_y, start_x)
    self.win_decision.box()

    title = " MAKE A DECISION "
    self.win_decision.addstr(0, int((width - len(title)) / 2), title, curses.color_pair(9) | curses.A_BOLD | curses.A_BLINK)

    self.win_decision.refresh()
    curses.doupdate()
    
    return self.refresh_decision(decision, 0)
  
  
  def refresh_decision(self, decision, selected_option):
    for i, option in enumerate(decision):
      text = "["
      text += "X" if selected_option == i else " "
      text += "] " + decision[option][0]
      self.win_decision.addstr(i+2, 2, text, curses.color_pair(9))

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


  # def setup_viewtext(self, title, contents):
  #   start_y = 5
  #   start_x = 10
  #   height = self.max_y - 10
  #   width = self.max_x - 20
  #
  #   self.win_viewtext = curses.newwin(height, width, start_y, start_x)
  #   self.win_viewtext.box()
  #
  #   title = " " + title + " (enter to close) "
  #   self.win_viewtext.addstr(0, int((width - len(title)) / 2), title, curses.color_pair(9) | curses.A_BOLD)
  #
  #   self.win_viewtext.refresh()
  #   curses.doupdate()
  #
  #   max_line_num = height - 3
  #   max_line_width = width - 4.0
  #
  #   contents_by_line = contents.split('\n')
  #   start_at_line = 0
  #   num_lines = len(list(contents_by_line))
  #   while True:
  #     additional_lines = 0
  #     for line_num in range(start_at_line, start_at_line+max_line_num):
  #       if line_num > (start_at_line + max_line_num - additional_lines):
  #         break
  #       spans_num_lines = math.ceil(len(contents_by_line[line_num]) / max_line_width)
  #       for j in range(0, spans_num_lines):
  #         start = j * max_line_width
  #         end = (j+1) * max_line_width
  #         this_line = str(contents_by_line[line_num])
  #         this_line = line[start:end]
  #         self.win_viewtext.addstr(1 + line_num - start_at_line + additional_lines + j, 3, , curses.color_pair(9))
  #       additional_lines += (spans_num_lines - 1)
  #
  #
  #     self.win_viewtext.refresh()
  #
  #     char =  self.win_viewtext.getch()
  #     if char == 65: # up arrow
  #       start_at_line = max((start_at_line - 1), 0)
  #     elif char == 66: # down arrow
  #       start_at_line = min((start_at_line + 1), num_lines)
  #     elif char == 10: # enter
  #       break
  #

  def show_progress(self, max_display):
    colour = curses.color_pair(5)
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


  def show_details(self, max_display):
    colour = curses.color_pair(3)
    self.win_body.addstr(self.start_pos + 1, 2, "ERROR DETAILS", colour)
    i = 1
    for line in self.error_details.split('\n'):
      line_num = i + self.start_pos + 2
      if line_num < max_display:
        self.win_body.addstr(line_num, 2, line, colour)
    
    
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
    self.error_details = stage_result.details

    # if stage_result.view_text != None:
    #   self.setup_viewtext(stage_result.view_text[0], stage_result.view_text[1])
  
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

    if stage_result.student_max_marks > -1:
      self.max_marks  = stage_result.student_max_marks

    if stage_result.next_stage == -1:
      self.is_active = False
    
    # update the existing stage's information
    next_stage.label = stage_result.updated_label
    next_stage.completed = -1 if stage_result.next_stage == -1 else 1

    # progress onto next stage
    self.current_stage = stage_result.next_stage
    self.refresh_marks()
    self.refresh_body(self.show_details if stage_result.details else None)
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
               updated_label,
               next_stage, # set to -1 if we cannot continue marking
               student_feedback = "",
               student_marks = 0,
               student_max_marks = -1, #change to a number to set max marks
               decision = None,
               view_text = None,
               details = None):
    self.updated_label = updated_label
    self.next_stage = next_stage
    self.student_feedback = student_feedback
    self.student_marks = student_marks
    self.student_max_marks = student_max_marks
    self.decision = decision
    self.view_text = view_text
    self.details = details
  
class coursework:
  CATCH2_EXE = os.getcwd() + "/_bin/catch.o"
  MARKS_DIR=os.getcwd() + "/_marks"
  ORIG_SRC_DIR=os.getcwd() + "/_origsrc"
  TEST_SRC_DIR=os.getcwd() + "/_tempsrc"

  CMD_OPEN_GIT=["open","-a","Sourcetree"]
  CMD_OPEN_README=["open"]
  CMD_OPEN_QUALITY=["open"]
  CMD_OPEN_CODE=["open","-a","TextMate"]
  
  
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
      return stage_result("Student src/ directory missing", -1)

    return stage_result(
      "Student files successfilly copied into temporary marking directory",
      "git")


  def git(student_id, marks, feedback):
    feedback = "USE OF GIT\n"
    if os.path.isdir(coursework.TEST_SRC_DIR + "/.git"):
      cmd = coursework.CMD_OPEN_GIT + [coursework.TEST_SRC_DIR]
      res = subprocess.run(cmd)
      
      decision = {
          "excellent": ("Excellent use of granular git commits and good commit messages",                  10, feedback + "You have used Git very well, committing work as you go and using relevant Git messages.\n\n",),
          "good":      ("Overall good use of granular git commits and good commit messages",               8, feedback + "You have used Git very well, committing work as you go and using relevant Git messages.\n\n",),
          "ok":        ("OK use of git commits, but some large commits or poor commit messages",           6, feedback + "Overall, your use of Git is OK, but could have been better. For higher marks, you should have made sure to perform granular commits (i.e. only committing a change or two at a time) with accurate messages.\n\n"),
          "poor":      ("Many large Git commits covering many changes and/or poor use of commit messages", 4, feedback + "Your use of Git is starting to get a bit messy. You should avoid commit lots of code in a single commit, and avoid simplistic messages that don't describe what happened in the commit.\n\n"),
          "bad":       ("Basically non-existant use of Git",                                               2, feedback + "Although you included your .git/ directory, it seems that you barely used Git, and certainly did not make the granular commit messages that you were expected to make.\n\n")}
      
      return stage_result(
        updated_label=".git/ directory opened in external application",
        decision=decision,
        next_stage="readme")
    else:
      feedback += "You did not include your .git/ directory, thus you will receive 0 marks for this coursework. You were told multiple times in lectures and in the coursework specification that you must include the .git/ directory"
      return stage_result(
        updated_label="No .git/ directory included - maximum marks set to 0",
        student_feedback=feedback,
        student_max_marks=0,
        next_stage="readme")


  def readme(student_id, marks, feedback):
    if not os.path.isfile(coursework.TEST_SRC_DIR + "/README.md"):
      return stage_result("No README.md included", "compile")

    # with open(coursework.TEST_SRC_DIR + "/README.md", "r") as f:
    #   contents = f.read()

    # return stage_result(
    #   updated_label="README.md included",
    #   view_text=("README.md", contents),
    #   next_stage="compile")

    cmd = coursework.CMD_OPEN_README + [coursework.TEST_SRC_DIR + "/README.md"]
    res = subprocess.run(cmd)

    return stage_result(
      updated_label="README.md opened in external application",
      next_stage="compile")


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
      feedback += "Your code compiles without issuing any warnings from the compiler, which is a good. You should never be submitting code with errors or warnings, even if the code is incomplete.\n\n"
      return stage_result(
        updated_label = "Coursework compiled without warnings",
        next_stage = "unittest_compile",
        student_feedback = feedback,
        student_marks = 5)
    elif res.returncode == 0 and stdout.find("warning") > -1:
      feedback =  "COMPILATION\n"
      feedback += "It looks like your code has some warnings from the compiler. You should aim to always produce code that has no warnings or errors, even if it is incomplete and does not implement all the functionality.\n\n"
      return stage_result(
        updated_label = "Coursework compiled with warnings",
        next_stage = "unittest_compile",
        student_feedback = feedback,
        student_marks = 0)
    elif res.returncode != 0:
      feedback =  "COMPILATION\n"
      feedback += "It seems that your code does not compile. As a result, we have been unable to mark your work with the automated unit tests. This represents a significant chunk of your marks that you could have gained.\n\n"

      # details = ' '.join(cmd) + "\n\n"
      details = res.stderr.decode("utf-8")

      return stage_result(
        updated_label = "!! Coursework failed to compile with result {0} !!".format(res.returncode),
        next_stage = "quality",
        student_feedback = feedback,
        student_marks = 0,
        details = details)


  def unittest_compile(student_id, marks, feedback):
    cmd = ["g++",
           "--std=c++14",
           "-Wall",
           "./src/bethyw.cpp",
           "./src/input.cpp",
           "./src/areas.cpp",
           "./src/area.cpp",
           "./src/measure.cpp",
           "./tests/testallus.cpp",
            coursework.CATCH2_EXE,
            "-o",
            "./bin/bethyw-test"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

    feedback = "UNIT TESTING\n"
    if res.returncode != 0:
      feedback += "It seems that your code does not compile with the unit tests. As a result, we have been unable to mark your work with the automated unit tests. This represents a significant chunk of your marks that you could have gained. \n\n"

      # details = ' '.join(cmd) + "\n\n"
      details = res.stderr.decode("utf-8")

      return stage_result(
        updated_label = "!! Compilation with Catch2 failed with result {0} !!".format(res.returncode),
        next_stage = "quality",
        student_feedback = feedback,
        student_marks = 0,
        details = details)

    return stage_result(
        updated_label = "Coursework compiled with Catch2",
        next_stage = "unittest",
        student_feedback = feedback,
        student_marks = 0)


  def unittest(student_id, marks, feedback):
    cmd = ["./bin/bethyw-test", "-r", "xml"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

    if res.returncode != 0:
      details = res.stderr.decode("utf-8")
      return stage_result(
        "Execution of unit tests failed with result: " + str(res.returncode),
        -1,
        details=details)
      
    # Parse Catch2 unit tests outcomes
    root = ET.XML(res.stdout.decode("utf-8"))

    df = pd.DataFrame(columns = ["student","filename", "tags", "result"])
    df = df.astype({"student": int})
    df = df.astype({"filename": str})
    df = df.astype({"tags": str})
    df = df.astype({"result": str})

    marks = 0
    total_tests = 0
    total_passes = 0
    
    for group in root.iter("Group"):
      for scenario in group.iter("TestCase"):
        result = False

        for result in scenario.iter("OverallResult"):
          total_tests += 1
          if result.get("success") == "true":
            result = "pass"
            total_passes += 1
          else:
            result = "fail"
          break
      
        # if result:
          # marks += catch2marks[scenario.get("tags")]

        df = df.append({"student"  : student_id,
                        "filename" : scenario.get("filename"),
                        "tags"     : scenario.get("tags"),
                        "result"   : result,
                        "marks"    : 0},
                        ignore_index=True)

    df.to_csv(coursework.MARKS_DIR + "/" + student_id + '-catch2.csv', index=False)

    feedback = "COMPILATION\nIt looks like your code has some warnings from the compiler. You should aim to always produce code that has no warnings or errors, even if it is incomplete and does not implement all the functionality.\n\n"
    return stage_result(
      "Unit tests completed ({0}/{1})".format(total_passes,total_tests),
      "memtest",
      feedback,
      55)


  def memtest(student_id, marks, feedback):
    cmd = ["valgrind",
           "--leak-check=yes",
           "--show-leak-kinds=all"
           "--track-origins=yes",
           "./bin/bethyw"]
    res = subprocess.run(cmd, cwd=coursework.TEST_SRC_DIR, capture_output=True)

    if res.returncode != 0:
      # details = ' '.join(cmd) + "\n\n"
      details = res.stderr.decode("utf-8")

      return stage_result(
        updated_label = "!! Running with valgrind failed with result {0} !!".format(res.returncode),
        next_stage = -1,
        details = details)
      
    feedback = "MEMORY LEAKS\n"
    valgrind_response = res.stdout.decode("utf-8")

    if valgrind_response.find("All heap blocks were freed") > 0:
      feedback += "Great work, your code has no memory leaks.\n\n"
      return stage_result(
          updated_label = "Coursework passed memory leak test",
          next_stage = "quality",
          student_feedback = feedback,
          student_marks = 5)
    else:
      feedback += "It seems that your code contains a one or more memory leaks. You should make sure you free any memory you allocate on the heap. In reality, you should have used good RAII principles taught in lectures and not needed to handle memory management at all.\n\n"
      return stage_result(
          updated_label = "Coursework was found to contain memory leaks",
          next_stage = "quality",
          student_feedback = feedback)

    
  def quality(student_id, marks, feedback):
    cmd = coursework.CMD_OPEN_CODE + [coursework.TEST_SRC_DIR + "/src"]
    res = subprocess.run(cmd)
    
    multidecision = [
        {"order1":    ("Functions in same order as provided code",                                            1, "CODE STYLE\nThank you for keeping the functions in the same order as in the provided code. This makes it easier to mark your work. "),
         "order2":    ("Functions have been rearranged",                                                      0, "CODE STYLE\nYou were asked to keep the functions in the same order as they were given to you in the block comments. Not doing this makes it significantly harder to mark your work. ")},

        {"comments1": ("Good commenting in relevant places",                                                  3, "You have used commenting well throughout your coursework solution. Comments help readers of your code understand complex code blocks. "),
         "comments2": ("Could have included additional comments to explain complex chunks of code",           2, "You could have used some more comments in your coursework solution to help readers of your code understand complex code blocks. "),
         "comments3": ("Excessive commenting given the complexity of the code",                               2, "You have used a few too many comments in your coursework solution. Remember, you only need comments to explain complex chunks of code rather than individual lines. You were told to assume that the people marking your work know C++. "),
         "comments4": ("Alright commenting (i.e. have used them if needed)",                                  1, "Your use of commenting is OK. Remember, you only need comments to explain complex chunks of code rather than individual lines. You were told to assume that the people marking your work know C++. In future, focus on providing explanatory comments rather than comments that merely repeat what can be gleamed from code. "),
         "comments5": ("No commenting",                                                                       0, "You haven't really used any comments of note in your work. In future, you should use comments to explain complex chunks of code that may not be obvious at first glance. ")},

        {"naming1":   ("Consistently good naming of variables and functions",                                 3, "In terms of naming convention, you have consistently used good naming of variables etc. in your code. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments.\n\n", 3),
         "naming2":   ("Generally good naming of variables and functions",                                    2, "In terms of naming convention, you have used good naming of variables etc. in your code. Good naming removes the need for many comments because it allows people to read and make sense of code without explanatory comments.\n\n", 2),
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

        {"redund1":   ("No redundant or repeated code",                                                       4, "You've also managed to avoid redundant/repeated code, which is always a bonus.\n\n"),
         "redund2":   ("Some redundant or repeated code (e.g. could have been new functions)",                2, "You've included some instances of redundant/repeated code which could have been made more efficient (e.g. by moving them into separate functions).\n\n"),
         "redund3":   ("Quite a bit of redundant or repeated code",                                           0, "There's a fair few instances of redundant/repeated code which could have been made more efficient (e.g. by moving them into separate functions).\n\n")},

        {"overall1":  ("Overall, this is an excellent coursework (quality, not completeness)",                0, "Overall, this is an excellent coursework. You have produced some nice code. Well done!"),
         "overall2":  ("Overall, this is a good coursework (quality, not completeness)",                      0, "Overall, this is an good coursework. You have produced some nice code, but there is some room for improvement. Well done!"),
         "overall3":  ("Overall, this is an ok coursework (quality, not completeness)",                       0, "Overall, this is an good attempt. You have produced some OK code, but there a few areas where you could have improved."),
         "overall4":  ("Overall, this is a poor coursework (quality, not completeness)",                      0, "Overall, there is quite a bit of scope for improvement. Much of this coursework's marks were achievable without completing all the tasks. Focusing on delivering good, but perhaps, incomplete code would have helped. ")}]
    
    return stage_result(
      updated_label="Sourcecode opened in external application",
      decision=multidecision,
      next_stage=None)

  def feedback(student_id, marks, feedback):
    pass
