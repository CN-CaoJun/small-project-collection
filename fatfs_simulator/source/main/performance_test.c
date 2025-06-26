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
#define SECTOR_TYPE 5
#define iterations 32 // Number of iterations per block size
static uint8 volatile emmc_io_test_flag = 1;
static uint32 write_collect[SECTOR_TYPE][iterations+3] = {0};
static uint32 read_collect[SECTOR_TYPE][iterations+3] = {0};
static void emmc_io_test(void)
{
    if (emmc_io_test_flag == 1)
    {
        const UINT block_sizes[SECTOR_TYPE] = {1024, 2048, 4096, 8192, 16384}; // Block sizes for testing
        FIL file;
        FRESULT ret;
        UINT bw, br;
        memset(wrbuffer, 0xFF, MAX_BLOCK_SIZE); // Initialize buffer to 0xFF
        
        #if EMBEDDENV 
        uint32 start_time = 0, end_time = 0;
        #else
        clock_t start_time = 0, end_time = 0;
        #endif

        // 清零统计数组
        memset(write_collect, 0, sizeof(write_collect));
        memset(read_collect, 0, sizeof(read_collect));

        for (UINT size_idx = 0; size_idx < SECTOR_TYPE; size_idx++) {
            UINT block_size = block_sizes[size_idx];
            
            // 每个块大小的统计变量
            double min_write_time_local = 1e9, max_write_time_local = 0, total_write_time_local = 0;
            double min_read_time_local = 1e9, max_read_time_local = 0, total_read_time_local = 0;
    
            // 执行10次写入测试
            for (UINT i = 0; i < iterations; i++) {
                // Write test on OTA_VBF partition
                start_time = IOTEST_GETTIME();
                ret = f_open(&file, IOTESTFILE_PATH, FA_WRITE | FA_CREATE_ALWAYS);
                if (ret == FR_OK) {
                    // 根据块大小选择写入方式
                    switch (block_size) {
                        case 1024:
                        case 2048:
                        case 4096:
                            // 直接写入，不超过缓冲区大小
                            f_write(&file, wrbuffer, block_size, &bw);
                            break;
                        case 8192:
                            // 分两次写入，每次4096字节
                            f_write(&file, wrbuffer, MAX_BLOCK_SIZE, &bw);
                            f_write(&file, wrbuffer, MAX_BLOCK_SIZE, &bw);
                            break;
                        case 16384:
                            // 分四次写入，每次4096字节
                            f_write(&file, wrbuffer, MAX_BLOCK_SIZE, &bw);
                            f_write(&file, wrbuffer, MAX_BLOCK_SIZE, &bw);
                            f_write(&file, wrbuffer, MAX_BLOCK_SIZE, &bw);
                            f_write(&file, wrbuffer, MAX_BLOCK_SIZE, &bw);
                            break;
                        default:
                            // 对于其他大小，按4096字节块分割写入
                            {
                                UINT remaining = block_size;
                                while (remaining > 0) {
                                    UINT write_size = (remaining > MAX_BLOCK_SIZE) ? MAX_BLOCK_SIZE : remaining;
                                    f_write(&file, wrbuffer, write_size, &bw);
                                    remaining -= write_size;
                                }
                            }
                            break;
                    }
                    f_sync(&file);
                    f_close(&file);
                }
                end_time = IOTEST_GETTIME();
                
                double write_time = ((double)(end_time - start_time));
                
                // 记录每次写入时间
                write_collect[size_idx][i] = (uint32)write_time;
                
                // 更新统计值
                total_write_time_local += write_time;
                if (write_time < min_write_time_local) min_write_time_local = write_time;
                if (write_time > max_write_time_local) max_write_time_local = write_time;
            }
            
            // 存储写入统计结果
            write_collect[size_idx][iterations] = (uint32)min_write_time_local;     // 最小值
            write_collect[size_idx][iterations + 1] = (uint32)max_write_time_local; // 最大值
            write_collect[size_idx][iterations + 2] = (uint32)(total_write_time_local / iterations); // 平均值

            // 执行10次读取测试
            for (UINT i = 0; i < iterations; i++) {
                // Read test on OTA_VBF partition
                start_time = IOTEST_GETTIME();
                ret = f_open(&file, IOTESTFILE_PATH, FA_READ);
                if (ret == FR_OK) {
                    // 根据块大小选择读取方式
                    switch (block_size) {
                        case 1024:
                        case 2048:
                        case 4096:
                            // 直接读取，不超过缓冲区大小
                            f_read(&file, wrbuffer, block_size, &br);
                            break;
                        case 8192:
                            // 分两次读取，每次4096字节
                            f_read(&file, wrbuffer, MAX_BLOCK_SIZE, &br);
                            f_read(&file, wrbuffer, MAX_BLOCK_SIZE, &br);
                            break;
                        case 16384:
                            // 分四次读取，每次4096字节
                            f_read(&file, wrbuffer, MAX_BLOCK_SIZE, &br);
                            f_read(&file, wrbuffer, MAX_BLOCK_SIZE, &br);
                            f_read(&file, wrbuffer, MAX_BLOCK_SIZE, &br);
                            f_read(&file, wrbuffer, MAX_BLOCK_SIZE, &br);
                            break;
                        default:
                            // 对于其他大小，按4096字节块分割读取
                            {
                                UINT remaining = block_size;
                                while (remaining > 0) {
                                    UINT read_size = (remaining > MAX_BLOCK_SIZE) ? MAX_BLOCK_SIZE : remaining;
                                    f_read(&file, wrbuffer, read_size, &br);
                                    remaining -= read_size;
                                }
                            }
                            break;
                    }
                    f_sync(&file);
                    f_close(&file);
                }
                end_time = IOTEST_GETTIME();
                
                double read_time = ((double)(end_time - start_time));
                
                // 记录每次读取时间
                read_collect[size_idx][i] = (uint32)read_time;
                
                // 更新统计值
                total_read_time_local += read_time;
                if (read_time < min_read_time_local) min_read_time_local = read_time;
                if (read_time > max_read_time_local) max_read_time_local = read_time;
            }
            
            // 存储读取统计结果
            read_collect[size_idx][iterations] = (uint32)min_read_time_local;     // 最小值
            read_collect[size_idx][iterations + 1] = (uint32)max_read_time_local; // 最大值
            read_collect[size_idx][iterations + 2] = (uint32)(total_read_time_local / iterations); // 平均值
        }
        
        #if EMBEDDENV 
        #else
        // 打印测试结果
        printf("Write Performance Test Results:\n");
        printf("Block Size\tMin(ticks)\tMax(ticks)\tAvg(ticks)\tAll 10 Results\n");
        for (UINT size_idx = 0; size_idx < SECTOR_TYPE; size_idx++) {
            printf("%u bytes\t%u\t\t%u\t\t%u\t\t", 
                   block_sizes[size_idx],
                   write_collect[size_idx][iterations],     // 最小值
                   write_collect[size_idx][iterations + 1], // 最大值
                   write_collect[size_idx][iterations + 2]  // 平均值
            );
            // 打印所有10次测试结果
            for (UINT i = 0; i < iterations; i++) {
                printf("%u ", write_collect[size_idx][i]);
            }
            printf("\n");
        }
        
        printf("\nRead Performance Test Results:\n");
        printf("Block Size\tMin(ticks)\tMax(ticks)\tAvg(ticks)\tAll 10 Results\n");
        for (UINT size_idx = 0; size_idx < SECTOR_TYPE; size_idx++) {
            printf("%u bytes\t%u\t\t%u\t\t%u\t\t", 
                   block_sizes[size_idx],
                   read_collect[size_idx][iterations],     // 最小值
                   read_collect[size_idx][iterations + 1], // 最大值
                   read_collect[size_idx][iterations + 2]  // 平均值
            );
            // 打印所有10次测试结果
            for (UINT i = 0; i < iterations; i++) {
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
