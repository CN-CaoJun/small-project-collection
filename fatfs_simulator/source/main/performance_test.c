#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h> // Added for timing measurements
#include "partition.h"
#include "performance_test.h"

typedef signed char         sint8;          /*        -128 .. +127            */
typedef unsigned char       uint8;          /*           0 .. 255             */
typedef signed short        sint16;         /*      -32768 .. +32767          */
typedef unsigned short      uint16;         /*           0 .. 65535           */
typedef signed long         sint32;         /* -2147483648 .. +2147483647     */
typedef unsigned long       uint32;         /*           0 .. 4294967295      */
typedef unsigned long long  uint64;         /*       0..18446744073709551615  */
typedef signed long long    sint64;         /* -9223372036854775808 .. 9223372036854775807 */
typedef float               float32;        /* IEEE754-1985 single precision  */
typedef double              float64;        /* IEEE754-1985 double precision  */



#define MAX_BLOCK_SIZE 4096 // Define the maximum block size
#define IOTESTFILE_PATH "OTA_VBF:/iotest"
#define SPEEDTESTFILE_PATH "OTA_VBF:/speedtest"
static unsigned char wrbuffer[MAX_BLOCK_SIZE]; // Static buffer with maximum block size
#define EMBEDDENV 0
#if EMBEDDENV 
#define IOTEST_GETTIME()       (*(volatile uint32*)0xF0001010u) //so 1 tick = 0.01us
#else
#define IOTEST_GETTIME()       clock() 
#endif
#define SECTOR_TYPE 3
static uint8 volatile emmc_io_test_flag = 1;
const UINT iterations = 10; // Number of iterations per block size
static uint32 write_collect[SECTOR_TYPE][13] = {0};
static uint32 read_collect[SECTOR_TYPE][13] = {0};
static double min_write_time = 1e9; 
static double max_write_time = 0; 
static double total_write_time = 0;
static double min_read_time = 1e9;
static double max_read_time = 0;
static double total_read_time = 0;
static void emmc_io_test(void)
{
    if (emmc_io_test_flag == 1)
    {
        // const UINT block_sizes[] = {1024, 2048, 4096, 8192, 16384}; // Block sizes for testing
        const UINT block_sizes[SECTOR_TYPE] = {1024, 2048, 4096}; // Block sizes for testing
        FIL file;
        FRESULT ret;
        UINT bw, br;
        memset(wrbuffer, 0xFF, MAX_BLOCK_SIZE); // Initialize buffer to 0xFF
        
        min_write_time = 1e9; 
        max_write_time = 0; 
        total_write_time = 0;
        min_read_time = 1e9;
        max_read_time = 0;
        total_read_time = 0;
        
        #if EMBEDDENV 
        uint32 start_write = 0, end_write = 0, start_read = 0, end_read = 0;
        #else
        clock_t start_write = 0, end_write = 0, start_read = 0, end_read = 0;
        #endif

        for (UINT size_idx = 0; size_idx < sizeof(block_sizes) / sizeof(UINT); size_idx++) {
            UINT block_size = block_sizes[size_idx];
    
            // double min_write_time = 1e9, max_write_time = 0, total_write_time = 0;
            // double min_read_time = 1e9, max_read_time = 0, total_read_time = 0;
    
            for (UINT i = 0; i < iterations; i++) {
                // Write test on OTA_VBF partition
                start_write = IOTEST_GETTIME();
                ret = f_open(&file, IOTESTFILE_PATH, FA_WRITE | FA_CREATE_ALWAYS); // Updated filename
                if (ret == FR_OK) {
                    f_write(&file, wrbuffer, block_size, &bw);
                    f_sync(&file);
                    f_close(&file);
                }
                // clock_t end_write = clock();
                end_write = IOTEST_GETTIME();
                double write_time = ((double)(end_write - start_write)) ;
                //record every write time
                write_collect[size_idx][i] = write_time;
                //calculate min, max, and total write time
                total_write_time += write_time;
                if (write_time < min_write_time) min_write_time = write_time;
                if (write_time > max_write_time) max_write_time = write_time;
                write_collect[size_idx][iterations] = min_write_time;
                write_collect[size_idx][iterations + 1] = max_write_time;
                //calculate average time
                write_collect[size_idx][iterations + 2] = total_write_time / iterations;

                // Read test on OTA_VBF partition
                // clock_t start_read = clock();
                start_read = IOTEST_GETTIME();
                ret = f_open(&file, IOTESTFILE_PATH, FA_READ); // Updated filename
                if (ret == FR_OK) {
                    f_read(&file, wrbuffer, block_size, &br);
                    f_sync(&file);
                    f_close(&file);
                }
                // clock_t end_read = clock();
                end_read = IOTEST_GETTIME();
                double read_time = ((double)(end_read - start_read)) ;
                //record every read time
                read_collect[size_idx][i] = read_time;
                //calculate min, max, and total read time
                total_read_time += read_time;
                if (read_time < min_read_time) min_read_time = read_time;
                if (read_time > max_read_time) max_read_time = read_time;
                read_collect[size_idx][iterations] = min_read_time;
                read_collect[size_idx][iterations + 1] = max_read_time;
                //calculate average time
                read_collect[size_idx][iterations + 2] = total_read_time / iterations;
            }
        }
        #if EMBEDDENV 
        #else
        // Add print statements after all loops
        printf("Write Collect Array:\n");
        for (UINT size_idx = 0; size_idx < SECTOR_TYPE; size_idx++) {
            printf("Block %u: ", size_idx);
            for (UINT i = 0; i < 13; i++) {
                printf("%u ", write_collect[size_idx][i]);
            }
            printf("\n");
        }
        printf("Read Collect Array:\n");
        for (UINT size_idx = 0; size_idx < SECTOR_TYPE; size_idx++) {
            printf("Block %u: ", size_idx);
            for (UINT i = 0; i < 13; i++) {
                printf("%u ", read_collect[size_idx][i]);
            }
            printf("\n");
        }
        #endif 
        emmc_io_test_flag = 0;
    }
}

void perform_file_io_test() {
    emmc_io_test();
}

void perform_large_file_test() {
    const UINT file_size = 16 * 1024 * 1024; // 16MB file size
    const UINT block_size = 4096; // 4K block size
    const double test_duration = 10.0; // 10 seconds test duration
    FIL file;
    FRESULT ret;
    UINT bw, br;
    memset(wrbuffer, 0xFF, block_size); // Initialize buffer to 0xFF

    // Write test
    clock_t start_write = clock();
    ret = f_open(&file, SPEEDTESTFILE_PATH, FA_WRITE | FA_CREATE_ALWAYS);
    if (ret == FR_OK) {
        UINT bytes_written = 0;
        while (bytes_written < file_size) {
            f_write(&file, wrbuffer, block_size, &bw);
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
            f_read(&file, wrbuffer, block_size, &br);
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
