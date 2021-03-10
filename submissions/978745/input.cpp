/*
 *  +---------------------------------------+
 *  | BETH YW? WELSH GOVERNMENT DATA PARSER |
 *  +---------------------------------------+
 *
 *  AUTHOR: 978745
 *
 *  This file contains implementations for the input source handlers.
 */

#include <fstream>
#include <stdexcept>
#include <string>

#include "input.h"

/*
 *  Constructor for an InputSource.
 *
 *  @param source
 *      A unique identifier for a source (i.e. the location).
 */
InputSource::InputSource(const std::string &source) noexcept : source(source) { /* Empty */ }

/*
 *  Retrieve the input source name from this object
 *
 *  This function should be callable from a constant context.
 *
 *  @return
 *      A non-modifable value for the source passed into the construtor.
 */
const std::string InputSource::getSource() const {
    return this->source;
}

/*
 *  Constructor for a file-based source.
 *
 *  @param path
 *      The complete path for a file to import.
 *
 *  @example
 *      InputFile input("data/areas.csv");
 */
InputFile::InputFile(const std::string &filePath) noexcept :
    InputSource(filePath), content_stream(new std::ifstream) { /* Empty */ }

/*
 * Destructor for a file-based source.
 */
InputFile::~InputFile() noexcept {
    delete this->content_stream;
}

/*
 *  Open a file stream to the file path retrievable from getSource()
 *  and return a reference to the stream.
 *
 *  @return
 *      A standard input stream reference
 *
 *  @throws
 *      std::runtime_error if there is an issue opening the file, with the message:
 *      InputFile::open: Failed to open file <file name>
 *
 *  @example
 *      InputFile input("data/areas.csv");
 *      input.open();
 */
std::istream & InputFile::open() const noexcept(false) {
    this->content_stream->open(this->getSource(), std::ios::in);
    if (this->content_stream->is_open()) return *this->content_stream;
    throw std::runtime_error("InputFile::open: Failed to open file " + this->getSource());
}
