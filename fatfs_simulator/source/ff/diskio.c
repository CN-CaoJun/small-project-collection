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

/* Definitions of physical drive number for each drive */
#define DEV_RAM		0	/* Example: Map Ramdisk to physical drive 0 */
#define DEV_MMC		1	/* Example: Map MMC/SD card to physical drive 1 */
#define DEV_USB		2	/* Example: Map USB MSD to physical drive 2 */

#define VIRTUAL_DISK_PATH "/media/sf_Ubuntu-Share/ff_alex/sd.bin"

// #define VIRTUAL_DISK_PATH "/mnt/virtual_disk.img"

FILE *virtual_disk;

/*-----------------------------------------------------------------------*/
/* Get Drive Status                                                      */
/*-----------------------------------------------------------------------*/

DSTATUS disk_status (
	BYTE pdrv		/* Physical drive nmuber to identify the drive */
)
{
	DSTATUS stat;
	int result;

	return RES_OK;
}


/*-----------------------------------------------------------------------*/
/* Inidialize a Drive                                                    */
/*-----------------------------------------------------------------------*/

DSTATUS disk_initialize (
	BYTE pdrv				/* Physical drive nmuber to identify the drive */
)
{
    virtual_disk = fopen(VIRTUAL_DISK_PATH, "rb+");
    if (!virtual_disk) {
		printf("disk init error\n");
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
	if (!virtual_disk) {
        return RES_NOTRDY;
    }
    
    fseek(virtual_disk, sector * 512, SEEK_SET);
    ret = fread(buff, 512, count, virtual_disk);
	if (ret < count)
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
	if (!virtual_disk) {
        return RES_NOTRDY;
    }
    
    fseek(virtual_disk, sector * 512, SEEK_SET);
    ret = fwrite(buff, 512, count, virtual_disk);
	if (ret < count)
	{
		printf("disk write error\n");
	}
    fflush(virtual_disk);
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
		*(DWORD *)buff = 512;
 
		break;
 
	case GET_SECTOR_SIZE:
		*(DWORD *)buff = 512;
		break;
 
	case GET_BLOCK_SIZE:
		*(DWORD *)buff = 200;
		break;
		
	case CTRL_TRIM:
		
		break;
	}
	return FR_OK;
}

