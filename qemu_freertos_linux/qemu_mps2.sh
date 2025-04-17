#!/bin/bash
echo "qemu_script_open"
echo "param[0] = $1"
if [ "$1" == "debug" ]; then
    echo "enter debug mode"
    qemu-system-arm \
        -machine mps2-an385 \
        -monitor null \
        -semihosting --semihosting-config enable=on,target=native \
        -kernel ./build/RTOSDEMO.elf \
        -serial stdio \
        -nographic \
        -s -S
else
    echo "enter run mode"
    qemu-system-arm \
        -machine mps2-an385 \
        -monitor null \
        -semihosting --semihosting-config enable=on,target=native \
        -kernel ./build/RTOSDEMO.elf \
        -serial stdio \
        -nographic
fi