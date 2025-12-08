#include "mylib/mylib.h"
#include <cassert>
#include <iostream>

void test_greeting() {
    auto result = mylib::get_greeting("Test");
    assert(result == "Hello, Test!");
    std::cout << "✓ test_greeting passed\n";
}

int main() {
    test_greeting();
    std::cout << "All tests passed!\n";
    return 0;
}
