cmake_minimum_required(VERSION 3.10.0)

set(PROJECT_NAME fatfs)

project(${PROJECT_NAME} VERSION 0.0.1 LANGUAGES ASM C CXX)

set(CMAKE_C_FLAGS "-std=c99")
set(CMAKE_BUILD_TYPE Debug)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/build)

set(SOURCE_PATH ${PROJECT_SOURCE_DIR}/source/)
add_subdirectory(source)