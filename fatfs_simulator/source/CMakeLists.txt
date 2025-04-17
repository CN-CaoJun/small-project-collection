INCLUDE_DIRECTORIES(${SOURCE_PATH}/ff)
aux_source_directory(${SOURCE_PATH}/ff DIR_LIB_SRCS)

INCLUDE_DIRECTORIES(${SOURCE_PATH}/main)
aux_source_directory(${SOURCE_PATH}/main DIR_LIB_SRCS)

INCLUDE_DIRECTORIES(${SOURCE_PATH}/source)
aux_source_directory(${SOURCE_PATH}/source  DIR_LIB_SRCS)

add_executable(${PROJECT_NAME}  ${DIR_LIB_SRCS})