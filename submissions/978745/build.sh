#!/bin/bash

#* This build file has been extensively edited! this how it works now:

#* ./build.sh           -> Build just the main binary
#* >>> Building BethYw

#* ./build.sh test{x}   -> Build with test x (assuming test x exists!)
#* >>> Building BethYw with test{x} included

#* ./build.sh test{*}   -> Build with testmany (all 12, will need recompiling for different selection)
#* >>> Building BethYw with many tests included

#* ./build.sh debug     -> Build the main binary with debug flags
#* >>> Building BethYw with debug flags enabled

#* ./build.sh {*} debug -> Build whatever you want, with debug flags
#* >>> Building BethYw with {*} with debug flags enabled

BIN_DIR="bin"
TESTS_DIR="tests"
OBJECTS_DIR="objects"
BUILD_FLAGS="-Wall -Wextra -Wpedantic"
SOURCE_FILES="bethyw.cpp input.cpp areas.cpp area.cpp measure.cpp"
MAIN_FILE="main.cpp"
EXECUTABLE="./${BIN_DIR}/bethyw"

OUT_STRING="Building BethYw"

cd "${0%/*}"

if [[ $1 == test* ]]
then
    MAIN_FILE="./${BIN_DIR}/catch.o"
    EXECUTABLE="./${BIN_DIR}/bethyw-test"
    #? Do we need to compile Catch2?
    # if [ ! -f ./${BIN_DIR}/catch.o ]
    # then
    #     clang++ --std=c++11 -c ./lib_catch_main.cpp -o ./${BIN_DIR}/catch.o
    # fi
    if [[ $1 == test[0-9]* ]]
    then
        OUT_STRING+=" with $1 included"
        SOURCE_FILES+=" ./${OBJECTS_DIR}/$1.o"
    else
        OUT_STRING+=" with many tests included"
        # SOURCE_FILES+=" ./${OBJECTS_DIR}/testmany.o"
        SOURCE_FILES+=" testmany.cpp"
    fi
fi

if [[ $1 == debug || $2 == debug ]]
then
    OUT_STRING+=" with debug flags enabled"
    BUILD_FLAGS+=" -g"
fi

# rm -v ${EXECUTABLE} || true
echo $OUT_STRING
set -x
clang++ -Os -s --std=c++14 ${BUILD_FLAGS} ${SOURCE_FILES} ${MAIN_FILE} -o ${EXECUTABLE}