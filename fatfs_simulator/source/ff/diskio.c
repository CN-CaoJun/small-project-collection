/*-----------------------------------------------------------------------*/
/* Low level disk I/O module skeleton for FatFs     (C)ChaN, 2019        */
/*-----------------------------------------------------------------------*/
/* If a working storage control module is available, it should be        */
/* attached to the FatFs via a glue function rather than modifying it.   */
/* This is an example of glue functions to attach various exsisting      */
/* storage control modules to the FatFs module with a defined API.       */
/*-----------------------------------------------------------------------*/

#include "ff.h"			/* Obtains integer types */
#include "diskio.h"		/* Declarations of disk functions */
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>

/* Definitions of physical drive number for each drive */
#define DEV_RAM		0	/* Example: Map Ramdisk to physical drive 0 */
#define DEV_MMC		1	/* Example: Map MMC/SD card to physical drive 1 */
#define DEV_USB		2	/* Example: Map USB MSD to physical drive 2 */

int fd = -1;

/*-----------------------------------------------------------------------*/
/* Get Drive Status                                                      */
/*-----------------------------------------------------------------------*/

DSTATUS disk_status (
	BYTE pdrv		/* Physical drive nmuber to identify the drive */
)
{
	return RES_OK;
}


/*-----------------------------------------------------------------------*/
/* Inidialize a Drive                                                    */
/*-----------------------------------------------------------------------*/

DSTATUS disk_initialize (
	BYTE pdrv				/* Physical drive nmuber to identify the drive */
)
{
	const char* block_device = "/dev/sdb";
    fd = open(block_device, O_RDWR);
    if (fd == -1) {
        printf("无法打开块设备文件\r\n");
        return STA_NOINIT;
    }
    return RES_OK;
}



/*-----------------------------------------------------------------------*/
/* Read Sector(s)                                                        */
/*-----------------------------------------------------------------------*/

DRESULT disk_read (
	BYTE pdrv,		/* Physical drive nmuber to identify the drive */
	BYTE *buff,		/* Data buffer to store read data */
	LBA_t sector,	/* Start sector in LBA */
	UINT count		/* Number of sectors to read */
)
{
	size_t ret;
	__off_t sct = sector*512UL;
	if (fd == -1) {
        return RES_NOTRDY;
    }
    ret = lseek(fd, sct, SEEK_SET);
    ret = read(fd, buff, 512 * count);
	if (ret < count*512)
	{
		printf("disk read error\n");
	}
    return RES_OK;
}



/*-----------------------------------------------------------------------*/
/* Write Sector(s)                                                       */
/*-----------------------------------------------------------------------*/

#if FF_FS_READONLY == 0

DRESULT disk_write (
	BYTE pdrv,			/* Physical drive nmuber to identify the drive */
	const BYTE *buff,	/* Data to be written */
	LBA_t sector,		/* Start sector in LBA */
	UINT count			/* Number of sectors to write */
)
{
	size_t ret;
	__off_t sct = sector*512UL;
	if (fd == -1) {
        return RES_NOTRDY;
    }
    
    ret = lseek(fd, sct, SEEK_SET);
    ret = write(fd, buff, 512 * count);
	if (ret < count)
	{
		printf("disk write error\n");
	}
    fsync(fd);
    return RES_OK;
}

#endif


/*-----------------------------------------------------------------------*/
/* Miscellaneous Functions                                               */
/*-----------------------------------------------------------------------*/

DRESULT disk_ioctl (
	BYTE pdrv,		/* Physical drive nmuber (0..) */
	BYTE cmd,		/* Control code */
	void *buff		/* Buffer to send/receive control data */
)
{
	switch (cmd) {
	case CTRL_SYNC:
		break;
 
	case GET_SECTOR_COUNT:
		*(DWORD *)buff = SIZE_MB(512)/512;
		break;
 
	case GET_SECTOR_SIZE:
		*(DWORD *)buff = 512;
		break;
 
	case GET_BLOCK_SIZE:
		*(DWORD *)buff = 512;
		break;
		
	case CTRL_TRIM:
		
		break;
	}
	return FR_OK;
}

