#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include "partition.h"
// #include "AptivAsn1_FileName.h"
// #include "Platform_Types.h"

extern int fd;
static DWORD plist[] = {25, 25, 25, 25}; /* Divide drive into four partitions */
unsigned char work[4096];
FATFS ffs0;
FATFS ffs1;
FATFS ffs2;
FATFS ffs3;

const unsigned char Fatfs_Init_Flag = 0;

void print_files_in_partition(const char* path) {
    FRESULT res;
    DIR dir;
    static FILINFO fno;

    res = f_opendir(&dir, path); /* Open the directory */
    if (res == FR_OK) {
        for (;;) {
            res = f_readdir(&dir, &fno); /* Read a directory item */
            if (res != FR_OK || fno.fname[0] == 0) break; /* Break on error or end of dir */
            if (fno.fattrib & AM_DIR) { /* It is a directory */
                printf("   DIR: %s\n", fno.fname);
            } else { /* It is a file */
                printf("   FILE: %s\n", fno.fname);
            }
        }
        f_closedir(&dir);
    }
}

void print_partitions() {
    printf("Contents of OTA_VBF:\n");
    print_files_in_partition("OTA_VBF:");

    printf("Contents of OTA_METADATA:\n");
    print_files_in_partition("OTA_METADATA:");

    printf("Contents of RVDC:\n");
    print_files_in_partition("RVDC:");

    printf("Contents of SAL:\n");
    print_files_in_partition("SAL:");
}

int part_mount(void) {
    FRESULT ret;
    // FIL file;
    static const MKFS_PARM format_opt = {(FM_FAT32 | FM_SFD), 0, 0, 0, 0}; /* FileSystem Format options*/

    if (Fatfs_Init_Flag == 1)
    {
        if (f_fdisk(0, plist, work) != FR_OK)
        {
            printf("Failed to initialize virtual disk\n");
            return 1;
        }
        else
        {
            printf("Virtual disk initialized successfully\n");
        }

        printf("The disk is going to formatting...\n");
        // Partitions are not formatted, proceed with formatting
        ret = f_mkfs("OTA_VBF:", &format_opt, work, 4096);
        ret |= f_mkfs("OTA_METADATA:", &format_opt, work, 4096);
        ret |= f_mkfs("RVDC:", &format_opt, work, 4096);
        ret |= f_mkfs("SAL:", &format_opt, work, 4096);
        if (ret != FR_OK) 
        {
            printf("Failed to format filesystem\n");
            return 1;
        }
        else
        {
            printf("Filesystem formatted successfully\n");
        }
    }

    ret = f_mount(&ffs0, "OTA_VBF:", 1);       /* Registers filesystem object to the FatFs module */
    ret |= f_mount(&ffs1, "OTA_METADATA:", 1); /* Registers filesystem object to the FatFs module */
    ret |= f_mount(&ffs2, "RVDC:", 1);         /* Registers filesystem object to the FatFs module */
    ret |= f_mount(&ffs3, "SAL:", 1);          /* Registers filesystem object to the FatFs module */
    if (ret != FR_OK)
    {
        printf("Failed to mount filesystem\n");
        return 1;
    }
    else
    {
        if (Fatfs_Init_Flag == 1)
        {
            // f_mkdir(OTA_INTERNAL_FILES_PATH);
            // f_mkdir(RVDC_MA_PARTITION_PATH);
            // f_mkdir(RVDC_MDP_PARTITION_PATH);
            // f_mkdir(RVDC_INTERNAL_FILES_PATH);
        }
        
        printf("Filesystem mounted successfully\n");
        print_partitions(); // Print the contents of each partition
    }
    
    return 0;
}

int part_umount(void)
{
    f_mount(NULL, "OTA_VBF:", 0);
    f_mount(NULL, "OTA_METADATA:", 0);
    f_mount(NULL, "RVDC:", 0);
    f_mount(NULL, "SAL:", 0);

    close(fd); 
}