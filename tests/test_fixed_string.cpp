#include "include/fixed_string.hpp"

/* Basic construction */
constexpr auto a = fixed_str("hello");
static_assert(a.size() == 5, "Size on construction must be 5\n");

/* Concatenation */
constexpr auto b = fixed_str("hello") + fixed_str(" world");
static_assert(b.size() == 11, "Size after concatenation must be 11\n");

/* String_view conversion */
constexpr auto c = fixed_str("abc");
static_assert(c.sv() == "abc", "fixed_string conversion to string_view must match");

/* Three-way chain */
constexpr auto d = fixed_str("<h1>") + fixed_str("Rishat") + fixed_str("</h1>");
static_assert(d.size() == 15, "Size in 'three-way chain' test must be 16");
static_assert(d.sv() == "<h1>Rishat</h1>", "fixed_string conversion in 'three-way chain' must match");

int main() {}
