#include "mylib/mylib.h"
#include <fmt/core.h>

namespace mylib {

std::string get_greeting(const std::string& name) {
    return fmt::format("Hello, {}!", name);
}

} // namespace mylib
