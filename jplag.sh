#!/bin/zsh

mv submissions_all/_framework .
find submissions_all -type f -name "lib_*" -exec rm {} \;
mv _framework submissions_all/

java -jar jplag-2.12.1-SNAPSHOT-jar-with-dependencies.jar submissions_all -vpd -l c/c++ -bc _framework
