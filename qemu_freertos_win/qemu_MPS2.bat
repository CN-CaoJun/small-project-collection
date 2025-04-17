@echo off
echo qemu_script_open
echo param[0] = %1
if "%1"=="debug" (
   goto debug
   )else ( 
    goto run)
:debug
	echo enter debug mode
	D:\RT-ThreadStudio\repo\Extract\Debugger_Support_Packages\RealThread\QEMU\4.2.0.4\qemu-system-arm.exe -machine mps2-an385 -monitor null -semihosting --semihosting-config enable=on,target=native  -kernel  ./build/RTOSDEMO.elf  -serial stdio -nographic -s -S
:run
	echo enter run mode 
	D:\RT-ThreadStudio\repo\Extract\Debugger_Support_Packages\RealThread\QEMU\4.2.0.4\qemu-system-arm.exe -machine mps2-an385 -monitor null -semihosting --semihosting-config enable=on,target=native  -kernel  ./build/RTOSDEMO.elf  -serial stdio -nographic