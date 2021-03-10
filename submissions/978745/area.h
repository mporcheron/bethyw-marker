#ifndef AREA_H
#define AREA_H

/*
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  This file contains declaration of the Area class.
 */

#include <map>
#include <ostream>
#include <stdexcept>
#include <string>

#include "measure.h"

/*
 *  An Area object consists of a unique authority code, a container for names
 *  for the area in any number of different languages, and a container for the
 *  Measures objects.
 */
class Area {

    std::string localAuthorityCode;
    std::string localAuthorityNameWelsh;
    std::string localAuthorityNameEnglish;

    std::map<std::string, Measure> measuremap;

    public:

        Area() = default;
        Area(const std::string &localAuthorityCode) noexcept;

        std::string getLocalAuthorityCode() const noexcept;

        void setName(const std::string &lang, const std::string &name) noexcept(false);
        std::string getName(std::string lang) const noexcept(false);

        void setMeasure(const std::string &code, Measure &measure) noexcept;
        Measure & getMeasure(const std::string &code) noexcept(false);

        std::map<std::string, Measure> getMeasuremap() const noexcept;
        int size() const noexcept;

        friend std::ostream & operator<<(std::ostream &os, const Area &self);
        friend bool operator==(const Area &self, const Area &other);

};

#endif // * AREA_H
