#pragma once

#include <string>

namespace mylib {

/**
 * Generate a greeting message.
 *
 * @param name Name to greet
 * @return Formatted greeting string
 */
std::string get_greeting(const std::string& name);

} // namespace mylib
