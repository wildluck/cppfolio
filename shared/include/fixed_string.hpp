#pragma once

#include <string_view>
#include <cstddef>
#include <algorithm>

template<std::size_t N>
struct fixed_string {
    char data[N]{};

    /* Construct from a string literal */
    consteval fixed_string(const char (&str)[N]) {
        std::copy_n(str, N, data);
    }

    /* Internal constructor for operator+ results */
    consteval fixed_string() = default;

    /* Concatenate two fixed_strings - return a new, larger */
    template<std::size_t M>
    consteval auto operator+(const fixed_string<M>& other) const {
        fixed_string<N + M - 1> result{};
        std::copy_n(data, N - 1, result.data);
        std::copy_n(other.data, M, result.data + N - 1);
        return result;
    }

    /* Convert fixed_string to string_view for Crow routes */
    constexpr std::string_view sv() const { return { data, N - 1 }; }

    constexpr std::size_t size() const { return N - 1; }
};

template<std::size_t N>
consteval fixed_string<N> fixed_str(const char (&s)[N]) {
    return fixed_string<N>(s);
}
