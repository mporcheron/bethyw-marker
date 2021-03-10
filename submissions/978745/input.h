#ifndef INPUT_H
#define INPUT_H

/*
 *  +---------------------------------------+
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  This file contains declarations for the input source handlers.
 */

#include <fstream>
#include <stdexcept>
#include <string>

/*
 *  InputSource is an abstract/purely virtual base class for all input source
 *  types. In future versions of our application, we may support multiple input
 *  data sources such as files and web pages. Therefore, this virtual class
 *  will allow us to mix/match sources as needed.
*/
class InputSource {

    const std::string source;

    protected:

        InputSource(const std::string &source) noexcept;

    public:

        const std::string getSource() const;

};

/*
 *  Source data that is contained within a file. For now, our application will
 *  only work with files (and in particular, the files in the datasets directory).
*/
class InputFile : public InputSource {

    std::ifstream * content_stream;

    public:

        InputFile(const std::string &filePath) noexcept;
        ~InputFile() noexcept;

        std::istream & open() const noexcept(false);

};

#endif // * INPUT_H
