# BDU Diagnostic ToolBox
## Overview
BDU Diagnostic ToolBox is a comprehensive diagnostic tool designed for automotive ECU testing and programming. It provides a user-friendly interface for CAN communication, UDS diagnostics, and bootloader operations.

## Features
- Multi-protocol CAN interface support (Vector, PCAN, SLCAN, SocketCAN)
- UDS diagnostic services
- ECU bootloader programming capabilities
- Real-time message tracing
- CAN/CAN-FD communication support
## System Requirements
- Windows Operating System
- Python 3.7 (if running from source)
- Compatible CAN hardware interface
## Hardware Support
- Vector CAN interfaces
- PCAN-USB devices
- SLCAN compatible devices
- SocketCAN (Linux)
## Installation
1. Download the latest release from the releases page
2. Extract the package to your desired location
3. Run the executable BDU_DiagnosticToolBox.exe
## Usage Guide
### Connection Setup
1. Connect your CAN hardware interface
2. Launch the application
3. Click "Scan" to detect available CAN interfaces
4. Select your CAN interface from the dropdown list
5. Configure the baudrate parameters
6. Enable CAN-FD if required
7. Click "Initialize" to establish connection
### Diagnostic Operations
1. Select the target ECU from the diagnostic configuration
2. Use the service buttons to perform diagnostic operations:
   - Read DTCs
   - Clear DTCs
   - Read Data by Identifier
   - Write Data by Identifier
   - ECU Reset
   - Security Access
### Bootloader Operations
1. Select SBL and APP hex files using the file selection buttons
2. Verify file paths are correctly displayed
3. Click "Start Flash" to begin the programming sequence
4. Monitor the progress in the trace window
5. Wait for completion confirmation
### Message Tracing
- All operations are logged in the trace window
- Messages include timestamps and detailed information
- Use for debugging and operation verification

## Support
For technical support or bug reports, please contact:

- Email: jun.cao@aptiv.com
## License
© APTIV Co., Ltd. All rights reserved.