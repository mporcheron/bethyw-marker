#include <iostream>
#include "../_tempsrc/measure.h"

// https://stackoverflow.com/questions/30407754/how-to-test-if-a-method-is-const

template <typename... >
using void_t = void;

template <typename T, typename = void>
struct getCodename : std::false_type { };

template <typename T>
struct getCodename<T, void_t<
    decltype(std::declval<const T&>().getCodename())
    > > : std::true_type { };


template <typename T, typename = void>
struct getLabel : std::false_type { };

template <typename T>
struct getLabel<T, void_t<
    decltype(std::declval<const T&>().getLabel())
    > > : std::true_type { };


template <typename T, typename = void>
struct size : std::false_type { };

template <typename T>
struct size<T, void_t<
    decltype(std::declval<const T&>().size())
    > > : std::true_type { };


template <typename T, typename = void>
struct getDifference : std::false_type { };

template <typename T>
struct getDifference<T, void_t<
    decltype(std::declval<const T&>().getDifference())
    > > : std::true_type { };


template <typename T, typename = void>
struct getDifferenceAsPercentage : std::false_type { };

template <typename T>
struct getDifferenceAsPercentage<T, void_t<
    decltype(std::declval<const T&>().getDifferenceAsPercentage())
    > > : std::true_type { };



template <typename T, typename = void>
struct getAverage : std::false_type { };

template <typename T>
struct getAverage<T, void_t<
    decltype(std::declval<const T&>().getAverage())
    > > : std::true_type { };



int main() 
{

  std::cout << "getCodename() = "               << getCodename<Measure>::value << std::endl;
  std::cout << "getLabel() = "                  << getLabel<Measure>::value << std::endl;
  std::cout << "size() = "                      << size<Measure>::value << std::endl;
  std::cout << "getDifference() = "             << getDifference<Measure>::value << std::endl;
  std::cout << "getDifferenceAsPercentage() = " << getDifferenceAsPercentage<Measure>::value << std::endl;
  std::cout << "getAverage() = "                << getAverage<Measure>::value << std::endl;
}