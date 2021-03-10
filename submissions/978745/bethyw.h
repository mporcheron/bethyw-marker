#ifndef BETHYW_H
#define BETHYW_H

/*
 *  +---------------------------------------+
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  This file contains the declaration of the BethYw namespace
 *  and other helper functions for initialising and running Beth Yw?
 */

#include <stdexcept>
#include <stdlib.h>
#include <string>

// #include "CSC371 Coursework Framework v1.0/YOUR_STUDENT_ID/lib_cxxopts.hpp"
#include "lib_cxxopts.hpp"

#include "areas.h"
#include "datasets.h"
#include "input.h"

const char DIR_SEP = '/';
// #ifdef _WIN32
//     '\\';
// #else
//     '/';
// #endif

/*
 *  An alias for input sources
 */
using InputSources = std::vector<BethYw::InputFileSource>;

namespace BethYw {

    const std::string STUDENT_NUMBER = "978745";

    int run(int argc, char *argv[]);

    cxxopts::Options cxxoptsSetup();

    std::string parseDirectoryArg(cxxopts::ParseResult &args) noexcept;
    InputSources parseDatasetsArg(cxxopts::ParseResult &args) noexcept(false);
    StringFilterSet parseAreasArg(cxxopts::ParseResult &args) noexcept;
    StringFilterSet parseMeasuresArg(cxxopts::ParseResult &args) noexcept;
    YearFilterTuple parseYearsArg(cxxopts::ParseResult &args) noexcept(false);

    void loadAreas(
        Areas &areas,
        std::string &dir,
        StringFilterSet &areasFilter
    ) noexcept;

    void loadDatasets(
        Areas &areas,
        const std::string &dir,
        InputSources &datasetsToImport,
        StringFilterSet &areasFilter,
        StringFilterSet &measuresFilter,
        YearFilterTuple &yearsFilter
    ) noexcept;

} // * namespace BethYw

#endif // * BETHYW_H
