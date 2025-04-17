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

### detach the loop device
```
sudo losetup -d /dev/loop0
```
### how to debug

step 1: run gdbserver
```
sudo gdbserver localhost:1234 fatfs
```
step 2: run gdb in vscode via json
```
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug",
            "type": "cppdbg",
            "request": "launch",
            "program": "${workspaceRoot}/build/fatfs",
            "args": [],
            "stopAtConnect": false,
            "cwd": "${workspaceRoot}",
            "environment": [],
            "externalConsole": false,
            "MIMode": "gdb",
            "miDebuggerPath": "/usr/bin/gdb",
            "miDebuggerServerAddress": "localhost:1234"
        },
    ]
}
```

