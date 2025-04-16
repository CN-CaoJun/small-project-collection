#include <stdio.h>
#include <stdlib.h>
#include "ff.h"
#include "diskio.h"


extern FILE *virtual_disk;
static DWORD plist[] = {88, 4, 4, 4};  /* Divide drive into Four partitions */
FATFS ffs0;
unsigned char work[4096];

int main() {
    FRESULT ret;
    FATFS fs;
    FIL file;
    static const MKFS_PARM format_opt = {(FM_FAT32|FM_SFD), 0, 0, 0, 0}; /* FileSystem Format options*/

          
    if (f_fdisk(0, plist, work) != RES_OK) {
        printf("无法初始化虚拟磁盘\n");
        return 1;
    }

    if (ret = f_mkfs("OTA_VBF:", &format_opt, work, 4096) != FR_OK)
    {
        printf("无法格式化文件系统\n");
        return 1;
    }

    if (f_mount(&ffs0, "OTA_VBF:", 1) != FR_OK) {
        printf("无法挂载文件系统\n");
        return 1;
    }

    // 打开/读取/写入文件等操作

    // 卸载文件系统
    f_mount(NULL, "", 0);

    fclose(virtual_disk); // 关闭虚拟磁盘文件
    return 0;
}