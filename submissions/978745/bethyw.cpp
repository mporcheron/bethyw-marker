/*
 *  +---------------------------------------+
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  This file contains the implementation of the BethYw namespace
 *  and other helper functions for initialising and running Beth Yw?
 */

#include <stdexcept>
#include <stdlib.h>
#include <string>
#include <typeinfo>

#include "lib_cxxopts.hpp"

#include "areas.h"
#include "bethyw.h"
#include "datasets.h"
#include "input.h"

namespace {

    /*
     * Anonymous namespace effectively makes these
     * functions private to only this source file.
     */

    inline InputSources all_datasets() {
        InputSources out;
        for (BethYw::InputFileSource dataSet : BethYw::InputFiles::DATASETS)
            out.push_back(dataSet);
        return out;
    }

    inline int find_number(unsigned int &i, std::string &text) {
        std::string token;
        while (i < (unsigned int) text.size() && std::isdigit(text.at(i)))
            token.push_back(text.at(i++));
        return std::atoi(token.c_str());
    }

}

/*
 *  Run Beth Yw?, parsing the command line arguments, importing the data,
 *  and outputting the requested data to the standard output/error.
*/
int BethYw::run(int argc, char *argv[]) {
    cxxopts::Options cxxopts = BethYw::cxxoptsSetup();
    cxxopts::ParseResult args = cxxopts.parse(argc, argv);

    try {
        // ! something
    } catch (cxxopts::option_not_exists_exception &e) {
        std::cerr << e.what() << std::endl;
        return EXIT_FAILURE;
    }

    if (args.count("help")) {
        std::cerr << cxxopts.help() << std::endl;
        return EXIT_SUCCESS;
    }

    std::string     dataDir;
    InputSources    dataFilter;
    StringFilterSet measFilter;
    StringFilterSet areaFilter;
    YearFilterTuple yearFilter;

    // * Parse arguments
    dataDir = BethYw::parseDirectoryArg(args);
    if (args.count("measures")) measFilter = BethYw::parseMeasuresArg(args);
    if (args.count("areas"))    areaFilter = BethYw::parseAreasArg(args);
    try {
        if (args.count("datasets")) dataFilter = BethYw::parseDatasetsArg(args);
        if (args.count("years"))    yearFilter = BethYw::parseYearsArg(args);
    } catch (std::invalid_argument &e) {
        std::cerr << e.what() << std::endl;
        return EXIT_FAILURE;
    }

    Areas data;
    BethYw::loadAreas(data, dataDir, areaFilter);
    BethYw::loadDatasets(data, dataDir, dataFilter, areaFilter, measFilter, yearFilter);

    args.count("json") ? std::cout << data.toJSON(args.count("indent")) : std::cout << data;

    return EXIT_SUCCESS;
}


/*
 *  This function sets up and returns a valid cxxopts object.
 *
 *  You do not need to modify this function.
 *  ( No, but I can make it look tidier (: )
 *
 *  @return
 *      A constructed cxxopts object
 *
 *  @example
 *      cxxopts::Options cxxopts = BethYw::cxxoptsSetup();
 *      cxxopts::ParseResult args = cxxopts.parse(argc, argv);
 */
cxxopts::Options BethYw::cxxoptsSetup() {
    cxxopts::Options cxxopts(
        "bethyw",
        "Student ID: " + STUDENT_NUMBER + "\n\n"
        "This program is designed to parse official Welsh Government statistics data files.\n"
    );

    cxxopts.add_options()
        (
            "dir",
            "Directory for input data passed in as files",
            cxxopts::value<std::string>()->default_value("datasets")
        )
        (
            "d,datasets",
            "The dataset(s) to import and analyse as a comma-separated list of codes "
            "(omit or set to 'all' to import and analyse all datasets)",
            cxxopts::value<std::vector<std::string>>()
        )
        (
            "a,areas",
            "The areas(s) to import and analyse as a comma-separated list of authority codes "
            "(omit or set to 'all' to import and analyse all areas)",
            cxxopts::value<std::vector<std::string>>()
        )
        (
            "m,measures",
            "Select a subset of measures from the dataset(s) "
            "(omit or set to 'all' to import and analyse all measures)",
            cxxopts::value<std::vector<std::string>>()
        )
        (
            "y,years",
            "Focus on a particular year (YYYY) or inclusive range of years (YYYY-ZZZZ) "
            "(omit or set to 'all' to import and analyse all years)",
            cxxopts::value<std::string>()->default_value("0")
        )
        (
            "j,json",
            "Print the output as JSON instead of tables."
        )
        (
            "i,indent",
            "Indenting for JSON output (optional flag)."
        )
        (
            "h,help",
            "Print usage."
        );

    return cxxopts;
}
/*
  Parse the directory argument passed into the command line.
  (optional argument)
*/
std::string BethYw::parseDirectoryArg(cxxopts::ParseResult &args) noexcept {
    return args["dir"].as<std::string>() + DIR_SEP;
}

/*
 *  Parse the datasets argument passed into the command line.
 *
 *  The datasets argument is optional, and if it is not included, all datasets
 *  should be imported. If it is included, it should be a comma-separated list of
 *  datasets to import. If the argument contains the value "all"
 *  (case-insensitive), all datasets should be imported.
 *
 *  @param args
 *      Parsed program arguments
 *
 *  @return
 *      A std::vector of BethYw::InputFileSource instances to import
 *
 *  @throws
 *      std::invalid_argument if the argument contains an invalid dataset with
 *      message: No dataset matches key <input code>
 *
 *  @example
 *      cxxopts::Options cxxopts = BethYw::cxxoptsSetup();
 *      cxxopts::ParseResult args = cxxopts.parse(argc, argv);
 *      InputSources datasetsToImport = BethYw::parseDatasetsArg(args);
 */
InputSources BethYw::parseDatasetsArg(cxxopts::ParseResult &args) noexcept(false) {
    std::vector<std::string> inputDatasets = args["datasets"].as<std::vector<std::string>>();
    std::vector<InputFileSource> dsets;
    for (std::basic_string<char> inputSet : inputDatasets) {
        if (inputSet == "all") return all_datasets();
        unsigned long size = dsets.size();
        for (InputFileSource dataSet : InputFiles::DATASETS)
            if (dataSet.CODE == inputSet) dsets.push_back(dataSet);
        if (dsets.size() == size) // * Nothing has been added
            throw std::invalid_argument("No dataset matches key: " + inputSet);
    }
    return dsets;
}

/*
 *  Parses the areas command line argument, which is optional. If it doesn't
 *  exist or exists and contains "all" as value (any case), all areas should be
 *  imported, i.e., the filter should be an empty set.
 *
 *  The filtering of inputs should be case insensitive.
 *
 *  @param args
 *      Parsed program arguments
 *
 *  @return
 *      An std::unordered_set of std::strings corresponding to specific areas
 *      to import, or an empty set if all areas should be imported.
 *
 *  @throws
 *      std::invalid_argument if the argument contains an invalid areas value with
 *      message: Invalid input for area argument
 */
StringFilterSet BethYw::parseAreasArg(cxxopts::ParseResult &args) noexcept {
    StringFilterSet areas;
    for (std::string item : args["areas"].as<std::vector<std::string>>()) {
        if ("all" == item) return StringFilterSet();
        areas.emplace(item);}
    return areas;
}

/*
 *  Parse the measures command line argument, which is optional. If it doesn't
 *  exist or exists and contains "all" as value (any case), all measures should
 *  be imported.
 *
 *  The filtering of inputs should be case insensitive.
 *
 *  @param args
 *      Parsed program arguments
 *
 *  @return
 *      An std::unordered_set of std::strings corresponding to specific measures
 *      to import, or an empty set if all measures should be imported.
 *
 *  @throws
 *      std::invalid_argument if the argument contains an invalid measures value
 *      with the message: Invalid input for measures argument
 */
StringFilterSet BethYw::parseMeasuresArg(cxxopts::ParseResult &args) noexcept {
    StringFilterSet measures;
    for (std::string item : args["measures"].as<std::vector<std::string>>()) {
        std::string item_lower; // % convert to lowercase to save pain later
        for (char c : item) item_lower.push_back(std::tolower(c));
        if ("all" == item) return StringFilterSet();
        measures.emplace(item_lower);}
    return measures;
}

/*
 *  Parse the years command line argument. Years is either a four digit year
 *  value, or two four digit year values separated by a hyphen.
 *
 *  @param args
 *      Parsed program arguments
 *
 *  @return
 *      A std::tuple containing two unsigned ints
 *
 *  @throws
 *      std::invalid_argument if the argument contains an invalid years value with
 *      the message: Invalid input for years argument
 */
YearFilterTuple BethYw::parseYearsArg(cxxopts::ParseResult &args) noexcept(false) {
    // ! This is quite c like, maybe change it..
    std::string temp = args["years"].as<std::string>();
    if (temp == "all") return std::make_tuple(0, 0);

    int hypen_count{0};
    for (char c : temp)
        if (!std::isdigit(c) && c != '-')
            throw std::invalid_argument("Invalid input for years argument");
        else hypen_count += c == '-';

    if (0 == hypen_count) {
        unsigned int t = std::atoi(temp.c_str());
        return std::make_tuple(t, t);
    }

    if ('-' == temp.front() || '-' == temp.back() || 1 < hypen_count)
        throw std::invalid_argument("Invalid input for years argument");

    unsigned int i = 0;
    unsigned int a = find_number(i, temp);
    unsigned int b = find_number(++i, temp);
    return std::make_tuple(std::min(a, b), std::max(a, b));
}

/*
 *  Load the areas.csv file from the directory `dir`. Parse the file and
 *  create the appropriate Area objects inside the Areas object passed to
 *  the function in the `areas` argument.
 *
 *  @param areas
 *      An Areas instance that should be modified
 *
 *  @param dir
 *      Directory where the areas.csv file is
 *
 *  @param areasFilter
 *      An unordered set of areas to filter, or empty to import all areas
 *
 *  @return
 *      void
 *
 *  @example
 *      Areas areas();
 *      BethYw::loadAreas(areas, "data", BethYw::parseAreasArg(args));
 */
void BethYw::loadAreas(Areas &areas, std::string &dir, StringFilterSet &areaFilter) noexcept {
    std::string file_name    = InputFiles::AREAS.FILE;
    SourceDataType data_type = InputFiles::AREAS.PARSER;
    SourceColumnMapping cols = InputFiles::AREAS.COLS;
    InputFile file((dir == "./" ? "" : dir) + file_name);
    try { // ! Such a dirty hack lol
        // ? areas.populateFromAuthorityCodeCSV(file.open(), cols, &areaFilter);
        areas.populate(file.open(), data_type, cols, &areaFilter);
    } catch (std::runtime_error &e) {
        std::cerr << "Error importing dataset:" << std::endl;
        std::cerr << e.what() << std::endl;
        exit(EXIT_FAILURE);
    }
}

/*
 *  Import datasets from `datasetsToImport` as files in `dir` into areas, and
 *  filtering them with the `areasFilter`, `measuresFilter`, and `yearsFilter`.
 *
 *  The actual filtering will be done by the Areas::populate() function, thus
 *  you need to merely pass pointers on to these flters.
 *
 *  This function should promise not to throw an exception. If there is an
 *  error/exception thrown in any function called by thus function, catch it and
 *  output 'Error importing dataset:', followed by a new line and then the output
 *  of the what() function on the exception.
 *
 *  @param areas
 *      An Areas instance that should be modified
 *
 *  @param dir
 *      The directory where the datasets are
 *
 *  @param datasetsToImport
 *      A vector of InputFileSource objects
 *
 *  @param areasFilter
 *      An unordered set of areas to filter, or empty to import all areas
 *
 *  @param measuresFilter
 *      An unordered set of measures to filter, or empty to import all measures
 *
 *  @param yearsFilter
 *      An two-pair tuple of unsigned ints corresponding to the range of years
 *      to import, which should both be 0 to import all years.
 *
 *  @return
 *      void
 *
 *  @example
 *      Areas areas();
 *      BethYw::loadDatasets(areas, "data",
 *          BethYw::parseDatasetsArgument(args),
 *          BethYw::parseAreasArg(args),
 *          BethYw::parseMeasuresArg(args),
 *          BethYw::parseYearsArg(args));
 */
void BethYw::loadDatasets(Areas &areas, const std::string &dir,
        InputSources &dsets, StringFilterSet &areaFilter,
        StringFilterSet &measFilter,YearFilterTuple &yearFilter) noexcept {
    try {
        for (InputFileSource dataset : dsets) {
            const InputFileSource * input_file = nullptr;
            if (dataset.CODE == "complete-area") // * CSV
                input_file = &InputFiles::COMPLETE_AREA;
            if (dataset.CODE == "complete-pop") // * CSV
                input_file = &InputFiles::COMPLETE_POP;
            if (dataset.CODE == "complete-popden") // * CSV
                input_file = &InputFiles::COMPLETE_POPDEN;
            if (dataset.CODE == "popden") // * JSON
                input_file = &InputFiles::POPDEN;
            if (dataset.CODE == "biz") // * JSON
                input_file = &InputFiles::BIZ;
            if (dataset.CODE == "aqi") // * JSON
                input_file = &InputFiles::AQI;
            if (dataset.CODE == "trains") // * JSON
                input_file = &InputFiles::TRAINS;
            if (input_file == nullptr) continue;
            InputFile file(dir + input_file->FILE);
            areas.populate(file.open(), input_file->PARSER, input_file->COLS,
                &areaFilter, &measFilter, &yearFilter);
        }
    } catch (std::exception &e) {
        std::cerr << "Error importing dataset:" << std::endl;
        std::cerr << e.what() << std::endl;
        exit(EXIT_FAILURE);
    }
}
