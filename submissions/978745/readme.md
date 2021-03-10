<!--
 *  +---------------------------------------+
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  This file contains information regarding the implementation of this project.
 -->

# Beth Yw?

Student Number : 978745

# build.sh has been edited, DO NOT run it without reading the usage guide!

### FULL test output provided in `all_tests_output.txt`
### FULL memory leak check in `valgrind_all_tests.txt`

Test additions
 - Tests added to test4.cpp to test the folowing edge cases
   - inputs starting with a hyphen "-1234"
   - inputs ending with a hyphen "1234-"
   - inputs containing more than one hyphen "1234--5678"
   - All of these will throw an invalid argument exception

Code additions
 - Years argument can set to "all" as well as omited to add all years to data
 - Measures argument is automatically converted to lowercase upon parsing
   - This is to make searching by key faster in later stages of processing
 - Additional `-i` flag added for indenting JSON output (used solely as a boolean)

Code design
 - Favour snake_case over camelCase for readability purposes
 - Where able, columns have been limited to 100 characters (5 lines are longer, longest = 109)
 - Empty constructors have been labelled as `/* EMPTY */`
   - Where not necessary destructors have not been implemented but declared `= default`
 - Minimal to no use of the keyword `auto` as it only seeks to make code less clear
 - Use of anonymous namespaces inside many source files to faciliatate quasi-private functions
 - Class header comments remain, as well as a comment anywhere with front heavy logic
 - Overly sized doc comments have been "trimmed" (Martin gave the OK)
 - Comments have symbols {*, ?, %, !} at the start
   - this is for syntax highlighting purposes
     - `*` = Generaldoc (green in my editor)
     - `?` = Question (blue in my editor)
     - `%` = Info (purple in my editor)
     - `!` = WTF (red in my editor)
 - Lack of curly brackets where possible to increase fluidity of the code
   - Doing so forces your IF, FOR and WHILE blocks to be a single statement
   - Keeping this line short then makes code more fluid and easier to read
 - Multiple return calls in many functions
   - This is to limit the execution of code after an exit condition has been found
 - Super janky directory hack (Martin is aware) in BethYw::loadAreas

Container selections
 - Measures, Area and Areas all use a standard map `std::map<typename T>`
   - This is to facilitate automatic ordering within the map and allow for sort-free printing

Compiler details
 - Clang(++), GCC is not very good at optimising code for UNIX and UNIX-like architectures
   - the errors also aren't as aesthetically pleasing to read
 - Manjaro Linux 64bit running Kernel 5.10.18-1-MANJARO
 - VsCodium, binary build from the AUR

Build changes
 - Re-written build.sh file to use precompiled object files, and speed up the build *a lot*
   - Build times dropped from 30~ seconds to 5~ seconds when including all test cases
   - Its small too! The final binary is under 400K! And the full test suite is only 2.0MB too!
    - The code, the JSON library, readme and the compiled binary would all fit on a 3 1/4" floppy!
    - (As demonstrated in `FloppyDisk.png`)

Early build, including all 12 tests
```
________________________________________________________
Executed in   36.26 secs   fish           external
   usr time   34.75 secs  459.00 micros   34.75 secs
   sys time    0.50 secs  305.00 micros    0.50 secs
```

Later build, after rewriting build.sh
```
________________________________________________________
Executed in    5.43 secs   fish           external
   usr time    5.17 secs  265.00 micros    5.17 secs
   sys time    0.25 secs   92.00 micros    0.25 secs
```
