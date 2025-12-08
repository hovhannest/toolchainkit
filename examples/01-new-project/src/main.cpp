#include "mylib/mylib.h"
#include <spdlog/spdlog.h>

int main() {
    spdlog::info("Starting application");

    auto greeting = mylib::get_greeting("World");
    spdlog::info(greeting);

    return 0;
}
