#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include "partition.h"
// #include "AptivAsn1_FileName.h"
// #include "Platform_Types.h"

extern int fd;
static DWORD plist[] = {76, 8, 9, 9}; /* Divide drive into Four partitions */
unsigned char work[4096];
FATFS ffs0;
FATFS ffs1;
FATFS ffs2;
FATFS ffs3;

const unsigned char Fatfs_Init_Flag = 0;

int part_mount(void)
{
    FRESULT ret;
    // FIL file;
    static const MKFS_PARM format_opt = {(FM_FAT32 | FM_SFD), 0, 0, 0, 0}; /* FileSystem Format options*/

    if (Fatfs_Init_Flag == 1)
    {
        if (f_fdisk(0, plist, work) != FR_OK)
        {
            printf("无法初始化虚拟磁盘\n");
            return 1;
        }
        else
        {
            printf("初始化虚拟磁盘 成功\n");
        }
        ret = f_mkfs("OTA_VBF:", &format_opt, work, 4096);
        ret |= f_mkfs("OTA_METADATA:", &format_opt, work, 4096);
        ret |= f_mkfs("RVDC:", &format_opt, work, 4096);
        ret |= f_mkfs("SAL:", &format_opt, work, 4096);
        if (ret != FR_OK)
        {
            printf("无法格式化文件系统\n");
            return 1;
        }
        else
        {
            printf("格式化文件系统 成功\n");
        }
    }

    ret = f_mount(&ffs0, "OTA_VBF:", 1);       /* registers filesystem object to the FatFs module */
    ret |= f_mount(&ffs1, "OTA_METADATA:", 1); /* registers filesystem object to the FatFs module */
    ret |= f_mount(&ffs2, "RVDC:", 1);         /* registers filesystem object to the FatFs module */
    ret |= f_mount(&ffs3, "SAL:", 1);          /* registers filesystem object to the FatFs module */
    if (ret != FR_OK)
    {
        printf("无法挂载文件系统\n");
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
        
        printf("挂载文件系统 成功\n");
    }
    return 0;
}

int part_umount(void)
{
    // 卸载文件系统
    f_mount(NULL, "OTA_VBF:", 0);
    f_mount(NULL, "OTA_METADATA:", 0);
    f_mount(NULL, "RVDC:", 0);
    f_mount(NULL, "SAL:", 0);

    close(fd); // 关闭虚拟磁盘文件
}