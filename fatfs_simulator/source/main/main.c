#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h> // Added for timing measurements
#include "partition.h"
#include "performance_test.h"

int main() {
    FRESULT ret;

    if (1 == part_mount()) {
        return -1;
    } else {
        printf("mount ok\n");
    }

    // Perform I/O performance test
    perform_file_io_test();

    // Perform large file speed test
    perform_large_file_test();

    printf("start to umount\n");
    part_umount();

    return 0;
}
