#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h> // Added for timing measurements
#include "partition.h"
#include "performance_test.h"

#define MAX_BLOCK_SIZE 16384 // Define the maximum block size
#define IOTESTFILE_PATH "OTA_VBF:/iotest"
#define SPEEDTESTFILE_PATH "OTA_VBF:/speedtest"

static char buffer[MAX_BLOCK_SIZE]; // Static buffer with maximum block size
void perform_file_io_test() {
    const UINT block_sizes[] = {1024, 2048, 4096, 8192, 16384}; // Block sizes for testing
    const UINT iterations = 100; // Number of iterations per block size
    FIL file;
    FRESULT ret;
    UINT bw, br;
    memset(buffer, 0xFF, MAX_BLOCK_SIZE); // Initialize buffer to 0xFF

    for (UINT size_idx = 0; size_idx < sizeof(block_sizes) / sizeof(UINT); size_idx++) {
        UINT block_size = block_sizes[size_idx];

        double min_write_time = 1e9, max_write_time = 0, total_write_time = 0;
        double min_read_time = 1e9, max_read_time = 0, total_read_time = 0;

        for (UINT i = 0; i < iterations; i++) {
            // Write test on OTA_VBF partition
            clock_t start_write = clock();
            ret = f_open(&file, IOTESTFILE_PATH, FA_WRITE | FA_CREATE_ALWAYS); // Updated filename
            if (ret == FR_OK) {
                f_write(&file, buffer, block_size, &bw);
                f_close(&file);
            }
            clock_t end_write = clock();
            double write_time = ((double)(end_write - start_write)) / CLOCKS_PER_SEC;
            total_write_time += write_time;
            if (write_time < min_write_time) min_write_time = write_time;
            if (write_time > max_write_time) max_write_time = write_time;

            // Read test on OTA_VBF partition
            clock_t start_read = clock();
            ret = f_open(&file, IOTESTFILE_PATH, FA_READ); // Updated filename
            if (ret == FR_OK) {
                f_read(&file, buffer, block_size, &br);
                f_close(&file);
            }
            clock_t end_read = clock();
            double read_time = ((double)(end_read - start_read)) / CLOCKS_PER_SEC;
            total_read_time += read_time;
            if (read_time < min_read_time) min_read_time = read_time;
            if (read_time > max_read_time) max_read_time = read_time;
        }

        // Print results for current block size
        printf("Block Size: %u\n", block_size);
        printf("Write - Min: %.6f, Max: %.6f, Avg: %.6f\n",
               min_write_time, max_write_time, total_write_time / iterations);
        printf("Read - Min: %.6f, Max: %.6f, Avg: %.6f\n",
               min_read_time, max_read_time, total_read_time / iterations);
    }
}

void perform_large_file_test() {
    const UINT file_size = 16 * 1024 * 1024; // 16MB file size
    const UINT block_size = 4096; // 4K block size
    const double test_duration = 10.0; // 10 seconds test duration
    FIL file;
    FRESULT ret;
    UINT bw, br;
    memset(buffer, 0xFF, block_size); // Initialize buffer to 0xFF

    // Write test
    clock_t start_write = clock();
    ret = f_open(&file, SPEEDTESTFILE_PATH, FA_WRITE | FA_CREATE_ALWAYS);
    if (ret == FR_OK) {
        UINT bytes_written = 0;
        while (bytes_written < file_size) {
            f_write(&file, buffer, block_size, &bw);
            bytes_written += bw;
        }
        f_close(&file);
    }
    clock_t end_write = clock();
    double write_time = ((double)(end_write - start_write)) / CLOCKS_PER_SEC;
    double write_speed = (file_size / (1024.0 * 1024.0)) / write_time; // MB/s

    // Read test
    clock_t start_read = clock();
    ret = f_open(&file, SPEEDTESTFILE_PATH, FA_READ);
    if (ret == FR_OK) {
        UINT bytes_read = 0;
        while (bytes_read < file_size) {
            f_read(&file, buffer, block_size, &br);
            bytes_read += br;
        }
        f_close(&file);
    }
    clock_t end_read = clock();
    double read_time = ((double)(end_read - start_read)) / CLOCKS_PER_SEC;
    double read_speed = (file_size / (1024.0 * 1024.0)) / read_time; // MB/s

    // Print results
    printf("Large File Test (16MB, 4K blocks, 10s):\n");
    printf("Write Speed: %.2f MB/s\n", write_speed);
    printf("Read Speed: %.2f MB/s\n", read_speed);
}
