#ifndef MEASURE_H
#define MEASURE_H

/*
 *  +---------------------------------------+
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  This file contains the decalaration of the Measure class.
 */

#include <iomanip>
#include <map>
#include <ostream>
#include <sstream>
#include <stdexcept>
#include <string>

/*
 *  The Measure class contains a measure code, label,
 *  and a container for readings from across a number of years.
 */
class Measure {

    std::string codename;
    std::string label;

    std::map<int, double> valuemap;

    public:

        Measure() = default;
        Measure(const std::string &code, const std::string &label) noexcept;

        std::string getCodename() const noexcept;

        void setLabel(const std::string &newLabel) noexcept;
        std::string getLabel() const noexcept;

        void setValue(const int &key, const double &value) noexcept;
        double getValue(const int &key) noexcept(false);

        std::map<int, double> getValuemap() const noexcept;
        int size() const noexcept;

        double getDifference() const noexcept;
        double getDifferenceAsPercentage() const noexcept;
        double getAverage() const noexcept;

        friend std::ostream & operator<<(std::ostream &os, const Measure &self);
        friend bool operator==(const Measure &self, const Measure &other);

};

#endif // * MEASURE_H
