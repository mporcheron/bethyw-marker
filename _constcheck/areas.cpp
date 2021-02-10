#include <iostream>
#include "../_tempsrc/areas.h"

// https://stackoverflow.com/questions/30407754/how-to-test-if-a-method-is-const

template <typename... >
using void_t = void;



template <typename T, typename = void>
struct size : std::false_type { };

template <typename T>
struct size<T, void_t<
    decltype(std::declval<const T&>().size())
    > > : std::true_type { };

int main() 
{
  std::cout << "size() = "                  << size<Areas>::value << std::endl;
}