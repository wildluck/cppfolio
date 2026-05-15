cmake_minimum_required(VERSION 3.25)
project(cppfolio LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
FetchContent_Declare(
    crow
    GIT_REPOSITORY https://github.com/CrowCpp/Crow.git
    GIT_TAG        master
)
FetchContent_MakeAvailable(crow)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

add_custom_target(portfolio_codegen
    COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/../shared/codegen/codegen.py
      --project portfolio
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Running codegen.py... --project portfolio..."
    BYPRODUCTS
        ${CMAKE_CURRENT_SOURCE_DIR}/generated/data.hpp
        ${CMAKE_CURRENT_SOURCE_DIR}/generated/pages.hpp
    VERBATIM
)

add_executable(cppfolio src/main.cpp)
add_dependencies(cppfolio portfolio_codegen)

target_include_directories(cppfolio PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}
  ${CMAKE_CURRENT_SOURCE_DIR}/../shared
)

target_link_libraries(cppfolio PRIVATE Crow::Crow)
target_compile_options(cppfolio PRIVATE -Wall -Wextra -O2)
