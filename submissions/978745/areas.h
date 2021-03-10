#ifndef AREAS_H
#define AREAS_H

/*
 *  +---------------------------------------+
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  This file contains the declaration of the Areas class
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
 */

#include <map>
#include <ostream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_set>

#include "area.h"
#include "datasets.h"

/*
 *  An alias for filters based on strings.
 */
using StringFilterSet = std::unordered_set<std::string>;

/*
 *  An alias for a year filter.
 */
using YearFilterTuple = std::tuple<unsigned int, unsigned int>;

/*
 *  An alias for the data within an Areas object stores Area objects.
*/
using AreasContainer = std::map<std::string, Area>;

/*
 *  Areas is a class that stores all the data categorised by area.
 */
class Areas {

    AreasContainer areamap;

    public:

        Areas();

        void setArea(const std::string &localAuthorityCode, Area &area) noexcept;
        Area & getArea(const std::string &localAuthorityCode) noexcept(false);

        AreasContainer getAreamap() const noexcept;

        int size() const noexcept;

        void populateFromAuthorityCodeCSV(
            std::istream &is,
            const BethYw::SourceColumnMapping &cols,
            const StringFilterSet * const areas
        ) noexcept(false);

        void populateFromWelshStatsJSON(
            std::istream &is,
            const BethYw::SourceColumnMapping &cols,
            const StringFilterSet * const areasFilter,
            const StringFilterSet * const measuresFilter,
            const YearFilterTuple * const yearsFilter
        ) noexcept(false);

        void populateFromAuthorityByYearCSV(
            std::istream &is,
            const BethYw::SourceColumnMapping &cols,
            const StringFilterSet * const areasFilter,
            const StringFilterSet * const measuresFilter,
            const YearFilterTuple * const yearsFilter
        ) noexcept(false);

        void populate(
            std::istream &is,
            const BethYw::SourceDataType &type,
            const BethYw::SourceColumnMapping &cols,
            const StringFilterSet * const areasFilter = nullptr,
            const StringFilterSet * const measuresFilter = nullptr,
            const YearFilterTuple * const yearsFilter = nullptr
        ) noexcept(false);

        std::string toJSON(bool indent) const;

        friend std::ostream & operator<<(std::ostream &os, const Areas &self);

};

#endif // * AREAS_H
