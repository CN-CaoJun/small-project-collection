cmake_minimum_required(VERSION 3.19)

include(CMake_Cross.cmake)

project(RTOSDEMO VERSION 0.0.1 LANGUAGES ASM C CXX)

set(CMAKE_BUILD_TYPE Debug)

add_definitions(
    -DQEMU_SOC_MPS2 
    -DHEAP3
)


INCLUDE_DIRECTORIES(${PROJECT_SOURCE_DIR}/FreeRTOS/Include)
INCLUDE_DIRECTORIES(${PROJECT_SOURCE_DIR}/MPS2_CMSIS/Include)
INCLUDE_DIRECTORIES(${PROJECT_SOURCE_DIR}/APP/Include)
INCLUDE_DIRECTORIES(${PROJECT_SOURCE_DIR}/APP_CXX/Include)
INCLUDE_DIRECTORIES(${PROJECT_SOURCE_DIR}/Main)


aux_source_directory(${PROJECT_SOURCE_DIR}/FreeRTOS/Source FreeRTOS_SRCS)
add_library(FreeRTOS_LIB ${FreeRTOS_SRCS})

aux_source_directory(${PROJECT_SOURCE_DIR}/MPS2_CMSIS/Source MPS2_CMSIS_SRCS)
add_library(MPS2_CMSIS_LIB ${MPS2_CMSIS_SRCS})


aux_source_directory(${PROJECT_SOURCE_DIR}/APP/Source APP_SRCS)
add_library(APP_LIB ${APP_SRCS})

aux_source_directory(${PROJECT_SOURCE_DIR}/APP_CXX/Source APP_CXX_SRCS)
add_library(APP_CXX_LIB ${APP_CXX_SRCS})


aux_source_directory(${PROJECT_SOURCE_DIR}/Main MAIN_SRCS)
# add_library(${PROJECT_NAME} ${MAIN_SRCS})


set(CMAKE_EXE_LINKER_FLAGS  " -T ${PROJECT_SOURCE_DIR}/MPS2_CMSIS/mps2_m3.ld -specs=nano.specs --specs=rdimon.specs -lc -lrdimon -Xlinker -Map=${PROJECT_SOURCE_DIR}/build/output.map")

add_executable(${PROJECT_NAME}.elf 
    ${MAIN_SRCS}
)
target_link_libraries(${PROJECT_NAME}.elf 
    MPS2_CMSIS_LIB
    FreeRTOS_LIB
    APP_LIB
    APP_CXX_LIB
)

set(ELF_FILE ${PROJECT_BINARY_DIR}/${PROJECT_NAME}.elf)
set(HEX_FILE ${PROJECT_BINARY_DIR}/${PROJECT_NAME}.hex)
set(BIN_FILE ${PROJECT_BINARY_DIR}/${PROJECT_NAME}.bin)



