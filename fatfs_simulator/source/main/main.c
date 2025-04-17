#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h> // Added for timing measurements
#include <pthread.h>
#include "partition.h"
#include "performance_test.h"

void* test_thread(void* arg) {
    // Perform I/O performance test
    perform_file_io_test();
    // Perform large file speed test
    perform_large_file_test();
    return NULL;
}

int main() {
    FRESULT ret;
    pthread_t thread;

    if (1 == part_mount()) {
        return -1;
    } else {
        printf("mount ok\n");
    }

    // Create thread for performance tests
    if(pthread_create(&thread, NULL, test_thread, NULL)) {
        fprintf(stderr, "Error creating thread\n");
        return -1;
    }

    // Wait for thread to complete
    pthread_join(thread, NULL);

    printf("start to umount\n");
    part_umount();

    return 0;
}
