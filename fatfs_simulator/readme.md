### Create a file of a specific size (e.g., 512MB)
```
dd if=/dev/zero of=block_device.img bs=1M count=512
```
### Associate the file with a loop device
```
sudo losetup -fP block_device.img
```
### List the loop device
```
losetup -l
```
### mount the loop device
```
sudo mount /dev/loop0 /mnt/fatfs
```
-> we can see the file system in linux folder manager

### unmount the loop device
```
sudo umount /mnt/fatfs
```

