cmake_minimum_required(VERSION 3.10.0)

project(example VERSION 0.0.1 LANGUAGES ASM C CXX)

set(CMAKE_C_FLAGS "-std=c99")
set(CMAKE_BUILD_TYPE Debug)

set(SOURCE_PATH ${PROJECT_SOURCE_DIR}/source/)
add_subdirectory(source)