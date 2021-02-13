#!/bin/zsh

mv submissions/_framework .
find submissions -type f -name "lib_*" -exec rm {} \;
mv _framework submissions/

java -jar jplag-2.12.1-SNAPSHOT-jar-with-dependencies.jar submissions -vpd -l c/c++ -bc _framework
