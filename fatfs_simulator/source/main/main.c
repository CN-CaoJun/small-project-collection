#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "partition.h"

int main() {
    FRESULT ret;
    FIL file;
    UINT bw;

    char bufin[] = "hello world";
    char bufout[100] = {};

    if (1 == part_mount())
    {
        return -1;
    }

    ret = f_open(&file, "OTA_METADATA:/test", FA_CREATE_ALWAYS | FA_READ | FA_WRITE);
    ret = f_write(&file, bufin, strlen(bufin), &bw);
    f_lseek(&file, 0);
    ret = f_read(&file, bufout, 12U, &bw);
    ret = f_close(&file);
    printf("%s\n", bufout);

    part_umount();

    return 0;
}