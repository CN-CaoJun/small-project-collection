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
    else
    {
        printf("mount ok\n");
    }

    printf("start to umount\n");

    part_umount();

    return 0;
}