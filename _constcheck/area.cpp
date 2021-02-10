#include <iostream>
#include "../_tempsrc/area.h"

// https://stackoverflow.com/questions/30407754/how-to-test-if-a-method-is-const

template <typename... >
using void_t = void;

template <typename T, typename = void>
struct getLocalAuthorityCode : std::false_type { };

template <typename T>
struct getLocalAuthorityCode<T, void_t<
    decltype(std::declval<const T&>().getLocalAuthorityCode())
    > > : std::true_type { };



std::string test = "test";

template <typename T, typename = void>
struct getName : std::false_type { };

template <typename T>
struct getName<T, void_t<
    decltype(std::declval<const T&>().getName(test))
    > > : std::true_type { };



template <typename T, typename = void>
struct size : std::false_type { };

template <typename T>
struct size<T, void_t<
    decltype(std::declval<const T&>().size())
    > > : std::true_type { };

int main() 
{

  std::cout << "getLocalAuthorityCode() = " << getLocalAuthorityCode<Area>::value << std::endl;
  std::cout << "getName() = "               << getName<Area>::value << std::endl;
  std::cout << "size() = "                  << size<Area>::value << std::endl;
}