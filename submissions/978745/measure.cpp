/*
 *  +---------------------------------------+
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  This file contains the implementation of the Measure class.
 */

#include <iomanip>
#include <map>
#include <ostream>
#include <sstream>
#include <stdexcept>
#include <string>

#include "measure.h"

/*
 *  Construct a single Measure, that has values across many years.
 *
 *  All StatsWales JSON files have a codename for measures.
 *  You should convert all codenames to lowercase.
 *
 *  @param codename
 *      The codename for the measure
 *
 *  @param label
 *      Human-readable (i.e. nice/explanatory) label for the measure
 *
 *  @example
 *      std::string codename = "Pop";
 *      std::string label = "Population";
 *      Measure measure(codename, label);
 */
Measure::Measure(const std::string &codename, const std::string &label) noexcept :
    codename(codename), label(label) {
    std::string codename_lower;
    for (char c : this->codename)
        codename_lower.push_back(std::tolower(c));
    this->codename = codename_lower;
}

/*
 *  Retrieve the code for the Measure.
 *
 *  This function should be callable from a constant context
 *  and must promise to not modify the state of the instance
 *  or throw an exception.
 *
 *  @return
 *      The codename for the Measure
 *
 *  @example
 *      std::string codename = "Pop";
 *      std::string label = "Population";
 *      Measure measure(codename, label);
 *      std::string codename2 = measure.getCodename();
 */
std::string Measure::getCodename() const noexcept {
    return this->codename;
}

/*
 *  Change the label for the Measure.
 *
 *  @param label
 *      The new label for the Measure
 *
 *  @example
 *      Measure measure("pop", "Population");
 *      measure.setValue(1999, 12345678.9);
 *      measure.setLabel("New Population");
 */
void Measure::setLabel(const std::string &newLabel) noexcept {
    this->label = newLabel;
}

/*
 *  Retrieve the human-friendly label for the Measure.
 *
 *  This function should be callable from a constant context
 *  and must promise to not modify the state of the instance
 *  and to not throw an exception.
 *
 *  @return
 *      The human-friendly label for the Measure
 *
 *  @example
 *      std::string codename = "Pop";
 *      std::string label = "Population";
 *      Measure measure(codename, label);
 *      measure.setValue(1999, 12345678.9);
 *      std::string label = measure.getLabel();
 */
std::string Measure::getLabel() const noexcept {
    return this->label;
}

/*
 *  Add a particular year's value to the Measure object.
 *
 *  If a value already exists for the year, replace it.
 *
 *  @param key
 *      The year to insert a value for
 *
 *  @param value
 *      The value for the given year
 *
 *  @return
 *      void
 *
 *  @example
 *      std::string codename = "Pop";
 *      std::string label = "Population";
 *      Measure measure(codename, label);
 *      measure.setValue(1999, 12345678.9);
 */
void Measure::setValue(const int &key, const double &value) noexcept {
    auto search = this->valuemap.find(key);
    if (search != this->valuemap.end())
        this->valuemap.at(key) = value;
    else this->valuemap.insert({key, value});
}

/*
 *  Retrieve a Measure's value for a given year.
 *
 *  @param key
 *      The year to find the value for
 *
 *  @return
 *      The value stored for the given year
 *
 *  @throws
 *      std::out_of_range if year does not exist in Measure with the message
 *      No value found for year <year>
 *
 *  @return
 *      The value
 *
 *  @example
 *      std::string codename = "Pop";
 *      std::string label = "Population";
 *      Measure measure(codename, label);
 *      measure.setValue(1999, 12345678.9);
 *      double value = measure.getValue(1999); // returns 12345678.9
 */
double Measure::getValue(const int &key) noexcept(false) {
    auto search = this->valuemap.find(key);
    if (search != this->valuemap.end())
        return this->valuemap.at(key);
    std::string key_as_string = std::to_string(key);
    throw std::out_of_range("No value found for year " + key_as_string);
}

/*
 *  Retieve the map of values assigned to this measure
 *
 *  @return
 *      the map of values assigned to this thing
 */
std::map<int, double> Measure::getValuemap() const noexcept {
    return this->valuemap;
}

/*
 *  Retrieve the number of years data we have for this measure.
 *
 *  This function should be callable from a constant context
 *  and must promise to not change the state of the instance
 *  or throw an exception.
 *
 *  @return
 *      The size of the measure
 *
 *  @example
 *      std::string codename = "Pop";
 *      std::string label = "Population";
 *      Measure measure(codename, label);
 *      measure.setValue(1999, 12345678.9);
 *      int size = measure.size(); // returns 1
 */
int Measure::size() const noexcept {
    return this->valuemap.size();
}

/*
 *  Calculate the difference between the first and last year imported.
 *
 *  This function should be callable from a constant context
 *  and must promise to not change the state of the instance
 *  or throw an exception.
 *
 *  @return
 *    The difference/change in value from the first to the last year, or 0 if it
 *    cannot be calculated
 *
 *  @example
 *    Measure measure("pop", "Population");
 *    measure.setValue(1999, 12345678.9);
 *    measure.setValue(2010, 12345679.9);
 *    double diff = measure.getDifference(); // returns 1.0
 */
double Measure::getDifference() const noexcept {
    if (this->size() < 2) return 0.0;
    double front = this->valuemap.begin()->second;
    return this->valuemap.rbegin()->second - front;
}

/*
 *  Calculate the difference between the first and last year imported as a
 *  percentage.
 *
 *  This function should be callable from a constant context
 *  and must promise to not change the state of the instance
 *  or throw an exception.
 *
 *  @return
 *      The difference/change in value from the first to the last year as a decminal
 *      value, or 0 if it cannot be calculated
 *
 *  @example
 *      Measure measure("pop", "Population");
 *      measure.setValue(1990, 12345678.9);
 *      measure.setValue(2010, 12345679.9);
 *      double diff = measure.getDifferenceAsPercentage();
 */
double Measure::getDifferenceAsPercentage() const noexcept {
    if (this->size() < 2) return 0.0;
    double front = this->valuemap.begin()->second;
    return 100 * (this->getDifference() / front);
}

/*
 *  Calculate the average/mean value for all the values.
 *
 *  This function should be callable from a constant context
 *  and must promise to not change the state of the instance
 *  or throw an exception.
 *
 *  @return
 *      The average value for all the years, or 0 if it cannot be calculated
 *
 *  @example
 *      Measure measure("pop", "Population");
 *      measure.setValue(1999, 12345678.9);
 *      measure.setValue(1999, 12345679.9);
 *      double diff = measure.getDifference(); // returns 1
 */
double Measure::getAverage() const noexcept {
    if (this->size() < 1) return 0.0;
    double sum = 0.0;
    for (std::pair<const int, double> val : this->valuemap)
        sum += val.second;
    return sum / this->size();
}

/*
 *  Overload the << operator to print all of the Measure's imported data.
 *
 *  We align the year and value outputs by padding the outputs with spaces,
 *  i.e. the year and values should be right-aligned to each other so they
 *  can be read as a table of numerical values.
 *
 *  Years should be printed in chronological order. Three additional columns
 *  should be included at the end of the output, corresponding to the average
 *  value across the years, the difference between the first and last year,
 *  and the percentage difference between the first and last year.
 *
 *  See the coursework specification for more information.
 *
 *  @param os
 *      The output stream to write to
 *
 *  @param measure
 *      The Measure to write to the output stream
 *
 *  @return
 *      Reference to the output stream
 *
 *  @example
 *      std::string codename = "Pop";
 *      std::string label = "Population";
 *      Measure measure(codename, label);
 *      measure.setValue(1999, 12345678.9);
 *      std::cout << measure << std::end;
 */
std::ostream & operator<<(std::ostream &os, const Measure &self) {
    std::stringstream heading, top_row, bot_row;
    heading << self.getLabel() << " (" << self.getCodename() << ") ";
    bot_row << std::fixed;
    for (std::pair<const int, double> val : self.getValuemap()) {
        top_row << std::setw(std::to_string(val.second).size());
        top_row << val.first  << " ";
        bot_row << val.second << " ";}   // *  So many trailing spaces
    double a = self.getAverage();        // * and all just to pass tests
    double d = self.getDifference();
    double p = self.getDifferenceAsPercentage();
    top_row << std::setw(std::to_string(a).size()) << "Average" << " "
            << std::setw(std::to_string(d).size()) << "Diff."   << " "
            << std::setw(std::to_string(p).size()) << "% Diff." << " ";
    for (double flt : {a, d, p}) bot_row << flt << " ";
    return os << heading.str() << "\n" << top_row.str() << "\n" << bot_row.str();
}

/*
 *  Overload the == operator for two Measure objects. Two Measure objects
 *  are only equal when their codename, label and data are all equal.
 *
 *  @param lhs
 *      A Measure object
 *
 *  @param lhs
 *      A second Measure object
 *
 *  @return
 *      true if both Measure objects have the same codename,
 *      label and data; false otherwise
 */
bool operator==(const Measure &self, const Measure &other) {
    if (self.getCodename() != other.getCodename()) return false;
    if (self.getLabel()    != other.getLabel())    return false;
    if (self.getValuemap() != other.getValuemap()) return false;
    return true;
}
