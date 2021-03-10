/*
 *  +---------------------------------------+
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  The file contains the Areas class implementation.
 *
 *  The Areas class is responsible for parsing data from a standard
 *  input stream and then converting it into a series of objects:
 *
 *  Measure    - Represents a single Aeasure for an area, e.g. population.
 *   |             Contains a human-readable label and a map of
 *   |             the measure accross a number of years.
 *   |
 *   +-> Area  - Represents an Area.
 *        |        Contains a unique local authority code used in national statistics,
 *        |        a map of the names of the area (in English and Welsh),
 *        |        and a map of various Measure objects.
 *        |
 *        +-> Areas : A class that contains all Area objects.
 *
 *  Areas are the top level of the data structure in Beth Yw?
 */

#include <map>
#include <ostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_set>

#include "lib_json.hpp"

#include "area.h"
#include "areas.h"
#include "bethyw.h"
#include "datasets.h"
#include "measure.h"

/*
 *  An alias for the imported JSON parsing library.
 */
using json = nlohmann::json;

namespace {

    /*
     * Anonymous namespace effectively makes these
     * functions private to only this source file.
     */

    inline void make_and_set_area(
            Areas &areas, std::string &auth_code,
            std::string &name_eng, std::string &name_welsh) noexcept {
        Area area_to_create(auth_code);
        area_to_create.setName("eng", name_eng);
        area_to_create.setName("cym", name_welsh);
        areas.setArea(auth_code, area_to_create);
    }

    inline std::string convert_to_lower_case(const std::string &string) noexcept {
        std::string string_lower;
        for (char c : string) string_lower.push_back(std::tolower(c));
        return string_lower;
    }

}

/*
 *  Constructor for an Areas object.
 *
 *  @example
 *      Areas data = Areas();
 */
Areas::Areas() { /* EMPTY */ }

/*
 *  Add a particular Area to the Areas object.
 *
 *  If an Area already exists with the same local authority code, overwrite all
 *  data contained within the existing Area with those in the new
 *  Area (i.e. they should be combined, but the new Area's data should take
 *  precedence, e.g. replace a name with the same language identifier).
 *
 *  @param key
 *      The local authority code of the Area
 *
 *  @param value
 *      The Area object that will contain the Measure objects
 *
 *  @return
 *      void
 *
 *  @example
 *      Areas data = Areas();
 *      std::string localAuthorityCode = "W06000023";
 *      Area area(localAuthorityCode);
 *      data.setArea(localAuthorityCode, area);
 */
void Areas::setArea(const std::string &localAuthorityCode, Area &area) noexcept {
    auto search = this->areamap.find(localAuthorityCode);
    if (search != this->areamap.end()) {
        // * Add any new data
        Area * curr = &this->areamap.at(localAuthorityCode);
        for (std::string name : {"eng", "cym"})
            if (!area.getName(name).size())
                area.setName(name, curr->getName(name));
        this->areamap.at(localAuthorityCode) = area;
    } else this->areamap.insert({localAuthorityCode, area});
}

/*
 *  Retrieve an Area instance with a given local authority code.
 *
 *  @param key
 *      The local authority code to find the Area instance of
 *
 *  @return
 *      An Area object
 *
 *  @throws
 *      std::out_of_range if an Area with the set local authority code does not
 *      exist in this Areas instance
 *
 *  @example
 *      Areas data = Areas();
 *      std::string localAuthorityCode = "W06000023";
 *      Area area(localAuthorityCode);
 *      data.setArea(localAuthorityCode, area);
 *      Area area2 = areas.getArea("W06000023");
 */
Area & Areas::getArea(const std::string &localAuthorityCode) noexcept(false) {
    auto search = this->areamap.find(localAuthorityCode);
    if (search != this->areamap.end())
        return this->areamap.at(localAuthorityCode);
    throw std::out_of_range("No area found matching " + localAuthorityCode);
}

/*
 *  Retrieve the map of Area objects belonging to this object
 *
 *  @return
 *      The map of Area objects attached to thie object
 */
AreasContainer Areas::getAreamap() const noexcept {
    return this->areamap;
}

/*
 *  Retrieve the number of Areas within the container.
 *
 *  This function should be callable from a constant context,
 *  not modify the state of the instance,
 *  and must promise not throw an exception.
 *
 *  @return
 *    The number of Area instances
 *
 *  @example
 *      Areas data = Areas();
 *      std::string localAuthorityCode = "W06000023";
 *      Area area(localAuthorityCode);
 *      data.setArea(localAuthorityCode, area);
 *      int size = areas.size(); // returns 1
 */
int Areas::size() const noexcept {
    return this->areamap.size();
}

/*
 *  This function specifically parses the compiled areas.csv file of local
 *  authority codes, and their names in English and Welsh.
 *
 *  @param is
 *      The input stream from InputSource
 *
 *  @param cols
 *      A map of the enum BethyYw::SourceColumnMapping (see datasets.h) to strings
 *      that give the column header in the CSV file
 *
 *  @param areasFilter
 *      An umodifiable pointer to set of umodifiable strings for areas to import,
 *      or an empty set if all areas should be imported
 *
 *  @return
 *      void
 *
 *  @throws
 *      std::runtime_error if a parsing error occurs (e.g. due to a malformed file)
 *      std::out_of_range if there are not enough columns in cols
 *
 *  @example
 *      InputFile input("data/areas.csv");
 *      std::ifstream is = input.open();
 *      BethYw::SourceColumnMapping cols = InputFiles::AREAS.COLS;
 *      StringFIlterSet areasFilter = BethYw::parseAreasArg();
 *      Areas data = Areas();
 *      areas.populateFromAuthorityCodeCSV(is, cols, &areasFilter);
 */
void Areas::populateFromAuthorityCodeCSV(
        std::istream &is, const BethYw::SourceColumnMapping &cols,
        const StringFilterSet * const areasFilter) noexcept(false) {

    char delim = ',';
    std::string token;
    std::getline(is, token);

    std::stringstream header;
    header << cols.at(BethYw::AUTH_CODE) << delim
           << cols.at(BethYw::AUTH_NAME_ENG) << delim
           << cols.at(BethYw::AUTH_NAME_CYM);

    if (token != header.str())
        throw std::out_of_range("Mismatched column information");
    std::string auth_code, name_eng, name_welsh;

    try {

        while (!is.eof()) {
            std::getline(is, token);
            std::stringstream line(token);

            std::getline(line, auth_code, delim);
            std::getline(line, name_eng, delim);
            std::getline(line, name_welsh);

            bool add = areasFilter == nullptr || areasFilter->empty();
            if (!add) {
                auto search = areasFilter->find(auth_code);
                add = search != areasFilter->end();}
            if (add) make_and_set_area(*this, auth_code, name_eng, name_welsh);
        }

    } catch (std::exception &e) {
        throw std::runtime_error("Parse error encountered during area population");
    }
}

/*
 *  Data from StatsWales is in the JSON format, and contains three
 *  top-level keys: odata.metadata, value, odata.nextLink. value contains the
 *  data we need. Rather than been hierarchical, it contains data as a
 *  continuous list (e.g. as you would find in a table). For each row in value,
 *  there is a mapping of various column headings and their respective vaues.
 *
 *  @param is
 *      The input stream from InputSource
 *
 *  @param cols
 *      A map of the enum BethyYw::SourceColumnMapping (see datasets.h) to strings
 *      that give the column header in the CSV file
 *
 *  @param areasFilter
 *      An umodifiable pointer to set of umodifiable strings of areas to import,
 *      or an empty set if all areas should be imported
 *
 *  @param measuresFilter
 *      An umodifiable pointer to set of umodifiable strings of measures to import,
 *      or an empty set if all measures should be imported
 *
 *  @param yearsFilter
 *      An umodifiable pointer to an umodifiable tuple of two unsigned integers,
 *      where if both values are 0, then all years should be imported, otherwise
 *      they should be treated as the range of years to be imported (inclusively)
 *
 *  @return
 *      void
 *
 *  @throws
 *      std::runtime_error if a parsing error occurs (e.g. due to a malformed file)
 *      std::out_of_range if there are not enough columns in cols
 *
 *  @example
 *      InputFile input("data/popu1009.json");
 *      std::ifstream is = input.open();
 *      BethYw::SourceColumnMapping cols = InputFiles::DATASETS["popden"].COLS;
 *      StringFilterSet areasFilter = BethYw::parseAreasArg();
 *      StringFilterSet measuresFilter = BethYw::parseMeasuresArg();
 *      YearFilterTuple yearsFilter = BethYw::parseMeasuresArg();
 *      Areas data = Areas();
 *      areas.populateFromWelshStatsJSON(is, cols, &areasFilter, &measuresFilter, &yearsFilter);
 */
void Areas:: populateFromWelshStatsJSON(std::istream &is,
        const BethYw::SourceColumnMapping &cols,
        const StringFilterSet * const areasFilter,
        const StringFilterSet * const measuresFilter,
        const YearFilterTuple * const yearsFilter) noexcept(false) {

    json json_dump;
    is >> json_dump;

    for (auto &data_dump : json_dump["value"].items()) {
        auto &data = data_dump.value();

        std::string auth_code, engl_name;
        std::string meas_name, meas_code;
        std::string year_code;
        double value = 0;

        try {

            auth_code = data[cols.at(BethYw::AUTH_CODE)];
            engl_name = data[cols.at(BethYw::AUTH_NAME_ENG)];
            year_code = data[cols.at(BethYw::YEAR)];

            // % Trains doesn't have these value, so we cheat
            auto search = cols.find(BethYw::MEASURE_CODE);
            if (search != cols.end()) {
                meas_code = data[cols.at(BethYw::MEASURE_CODE)];
                meas_name = data[cols.at(BethYw::MEASURE_NAME)];
            } else {
                meas_code = cols.at(BethYw::SINGLE_MEASURE_CODE);
                meas_name = cols.at(BethYw::SINGLE_MEASURE_NAME);
            }

            // % Environment stores data as string
            if (data[cols.at(BethYw::VALUE)].is_string()) {
                std::string value_as_atring = data[cols.at(BethYw::VALUE)];
                value = std::atof(value_as_atring.c_str());
            } else value = data[cols.at(BethYw::VALUE)];

        } catch (std::exception &e) {
            throw std::out_of_range("Mismatched column information");
        }

        if (auth_code.empty() || engl_name.empty() || year_code.empty()
                              || meas_name.empty() || meas_code.empty())
            throw std::runtime_error("Parse error encountered during area population");

        // * Area filter here
        auto search = areasFilter->find(auth_code);
        if (areasFilter == nullptr || areasFilter->empty() || search != areasFilter->end()) {

            // * Work out if area exists first, make new one if not
            // ! tests don't actually load areas in at all
            Area area_to_add_to(auth_code);
            auto area_map = this->getAreamap();
            if (!area_map.empty()) for (auto area : area_map) if (area.first == auth_code)
                area_to_add_to = area.second;

            // * Measure filter here
            std::string code_lower = convert_to_lower_case(meas_code);
            auto search = measuresFilter->find(code_lower); // % Args are converted to lowercase
            if (measuresFilter == nullptr || measuresFilter->empty() || search != measuresFilter->end()) {

                // * Work out if measure exists
                Measure measure_to_add_to(code_lower, meas_name);
                auto mes_map = area_to_add_to.getMeasuremap();
                if (!mes_map.empty()) for (auto mes : mes_map) if (mes.first == code_lower)
                    measure_to_add_to = mes.second;

                // * Year filter here
                int y_low = std::get<0>(*yearsFilter);
                int y_hig = std::get<1>(*yearsFilter);
                int year = std::atoi(year_code.c_str());
                if (yearsFilter == nullptr || y_low == 0 || (year >= y_low && year <= y_hig)) {
                    measure_to_add_to.setValue(year, value);
                    area_to_add_to.setMeasure(code_lower, measure_to_add_to);
                }
            }

            area_to_add_to.setName("eng", engl_name);
            this->setArea(auth_code, area_to_add_to);
        }
    }

}

/*
 *  This function imports CSV files that contain a single measure. The
 *  CSV file consists of columns containing the authority code and years.
 *  Each row contains an authority code and values for each year (or no value
 *  if the data doesn't exist).
 *
 *  @param is
 *      The input stream from InputSource
 *
 *  @param cols
 *      A map of the enum BethyYw::SourceColumnMapping (see datasets.h) to strings
 *      that give the column header in the CSV file
 *
 *  @param areasFilter
 *      An umodifiable pointer to set of umodifiable strings for areas to import,
 *      or an empty set if all areas should be imported
 *
 *  @param measuresFilter
 *      An umodifiable pointer to set of strings for measures to import, or an empty
 *      set if all measures should be imported
 *
 *  @param yearsFilter
 *      An umodifiable pointer to an umodifiable tuple of two unsigned integers,
 *      where if both values are 0, then all years should be imported, otherwise
 *      they should be treated as a the range of years to be imported
 *
 *  @return
 *      void
 *
 *  @throws
 *      std::runtime_error if a parsing error occurs (e.g. due to a malformed file)
 *      std::out_of_range if there are not enough columns in cols
 *
 *  @example
 *      InputFile input("data/complete-popu1009-pop.csv");
 *      std::ifstream is = input.open();
 *      BethYw::SourceColumnMapping cols = InputFiles::DATASETS["complete-pop"].COLS;
 *      StringFilterSet areasFilter = BethYw::parseAreasArg();
 *      StringFilterSet yearsFilter = BethYw::parseYearsArg();
 *      Areas data = Areas();
 *      areas.populateFromAuthorityCodeCSV(is, cols, &areasFilter, &yearsFilter);
 */
void Areas::populateFromAuthorityByYearCSV(std::istream &is,
        const BethYw::SourceColumnMapping &cols,
        const StringFilterSet * const areasFilter,
        const StringFilterSet * const measuresFilter,
        const YearFilterTuple * const yearsFilter) noexcept(false) {

    char delim = ',';
    std::string token;
    std::getline(is, token);
    std::stringstream line(token);

    std::getline(line, token, delim);
    if (token != cols.at(BethYw::AUTH_CODE))
        throw std::runtime_error("Parse error encountered during data collection");
    std::vector<int> years;
    while (std::getline(line, token, delim))
        years.push_back(std::atoi(token.c_str()));

    while (!is.eof()) {
        std::getline(is, token);
        std::stringstream line(token);
        std::getline(line, token, delim);

        // * Area filter here
        auto search = areasFilter->find(token);
        if (areasFilter == nullptr || areasFilter->empty() || search != areasFilter->end()) {
            Area * area_to_add_to = &this->getArea(token);

            // * Measure filter here
            std::string code_lower = convert_to_lower_case(cols.at(BethYw::SINGLE_MEASURE_CODE));
            auto search = measuresFilter->find(code_lower);
            if (measuresFilter == nullptr || measuresFilter->empty() || search != measuresFilter->end()) {
                Measure mes(code_lower, cols.at(BethYw::SINGLE_MEASURE_NAME));

                for (int year : years) {
                    try { std::getline(line, token, delim);

                        // * Year filter here
 /*      __        */   int y_low = std::get<0>(*yearsFilter);
 /*    <(o )___    */   int y_hig = std::get<1>(*yearsFilter);
 /*     ( ._> /    */   if (yearsFilter == nullptr || y_low == 0 || (year >= y_low && year <= y_hig)) {
 /*      `---'     */       mes.setValue(year, std::atof(token.c_str()));
 /* Debugging Duck */       area_to_add_to->setMeasure(code_lower, mes);
                        }
                    } catch (std::exception &e) {
                        throw std::out_of_range("Mismatched column information");
                    }
                }

            }
        }
    }

}

/*
 *  Parse data from an standard input stream, that is of a particular type,
 *  and with a given column mapping, filtering for specific areas, measures,
 *  and years, and fill the container.
 *
 *  This overloaded function includes pointers to the three filters for areas,
 *  measures, and years.
 *
 *  @param is
 *      The input stream from InputSource
 *
 *  @param type
 *      A value from the BethYw::SourceDataType enum which states the underlying
 *      data file structure
 *
 *  @param cols
 *      A map of the enum BethyYw::SourceColumnMapping (see datasets.h) to strings
 *      that give the column header in the CSV file
 *
 *  @param areasFilter
 *      An umodifiable pointer to set of umodifiable strings for areas to import,
 *      or an empty set if all areas should be imported
 *
 *  @param measuresFilter
 *      An umodifiable pointer to set of umodifiable strings for measures to import,
 *      or an empty set if all measures should be imported
 *
 *  @param yearsFilter
 *      An umodifiable pointer to an umodifiable tuple of two unsigned integers,
 *      where if both values are 0, then all years should be imported, otherwise
 *      they should be treated as a the range of years to be imported
 *
 *  @return
 *      void
 *
 *  @throws
 *      std::runtime_error if a parsing error occurs (e.g. due to a malformed file),
 *      the stream is not open/valid/has any contents, or an unexpected type
 *      is passed in.
 *      std::out_of_range if there are not enough columns in cols
 *
 *  @example
 *      InputFile input("data/popu1009.json");
 *      std::ifstream is = input.open();
 *      BethYw::SourecColumnMapping cols = InputFiles::DATASETS["popden"].COLS;
 *      StringFilterSet areasFilter = BethYw::parseAreasArg();
 *      StringFilterSet measuresFilter = BethYw::parseMeasuresArg();
 *      YearFilterTuple yearsFilter = BethYw::parseMeasuresArg();
 *      Areas data = Areas();
 *      areas.populate(is, DataType::WelshStatsJSON, cols, &areasFilter, &measuresFilter, &yearsFilter);
 */
void Areas::populate(
        std::istream &is,
        const BethYw::SourceDataType &type,
        const BethYw::SourceColumnMapping &cols,
        const StringFilterSet * const areasFilter,
        const StringFilterSet * const measuresFilter,
        const YearFilterTuple * const yearsFilter) {
    if (type == BethYw::AuthorityCodeCSV) {
        populateFromAuthorityCodeCSV(is, cols, areasFilter);
    } else if (type == BethYw::AuthorityByYearCSV) {
        populateFromAuthorityByYearCSV(is, cols, areasFilter, measuresFilter, yearsFilter);
    } else if(type == BethYw::WelshStatsJSON) {
        populateFromWelshStatsJSON(is, cols, areasFilter, measuresFilter, yearsFilter);
    } else {
        throw std::runtime_error("Areas::populate: Unexpected data type");
    }
}

/*
 *  Convert this Areas object, and all its containing Area instances, and
 *  the Measure instances within those, to values.
 *
 *  @return
 *    std::string of JSON
 *
 *  @example
 *      InputFile input("data/popu1009.json");
 *      std::ifstream is = input.open();
 *      BethYw::SourceColumMapping cols = InputFiles::DATASETS["popden"].COLS;
 *      StringFilterSet areasFilter = BethYw::parseAreasArg();
 *      StringFilterSet measuresFilter = BethYw::parseMeasuresArg();
 *      YearFilterTuple yearsFilter = BethYw::parseMeasuresArg();
 *      Areas data = Areas();
 *      std::cout << data.toJSON();
*/
std::string Areas::toJSON(bool indent) const {
    json json_dump({});

    for (auto area : this->areamap) {
        json area_dump({});
        json measure_dump({});
        for (auto measure : area.second.getMeasuremap()) {
            json value_dump({});
            for (auto value : measure.second.getValuemap())
                value_dump[std::to_string(value.first)] = value.second;
            measure_dump[measure.first] = value_dump;
        }
        if (!measure_dump.empty())
            area_dump["measures"] = measure_dump;
        json names({});
        for (auto name : {"cym", "eng"})
            if (!area.second.getName(name).empty())
                names[name] = area.second.getName(name);
        area_dump["names"] = names;
        json_dump[area.first] = area_dump;
    }

    return json_dump.dump(indent ? 4 : -1);
}

// ! to csv

/*
 *  Overload the << operator to print all of the imported data.
 *
 *  @param os
 *      The output stream to write to
 *
 *  @param areas
 *      The Areas object to write to the output stream
 *
 *  @return
 *      Reference to the output stream
 *
 *  @example
 *      Areas areas();
 *      std::cout << areas << std::end;
 */
std::ostream & operator<<(std::ostream &os, const Areas &self) {
    if (self.size() == 0) return os;
    for (auto area : self.getAreamap()) os << area.second;
    return os;
}
