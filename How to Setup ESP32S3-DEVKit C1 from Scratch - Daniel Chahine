How to Setup ESP32S3-DEVKit C1 from Scratch
Steps to Setup:

Ensure microcontroller is plugged in through the UART port to a windows machine, and that Python is downloaded onto the machine.
Open command prompt and enter:
pip install esptool

Erase the previous flash on the microcontroller with the prompt:
python -m esptool --chip esp32s3 --port COMX erase_flash

Where X is the COM number for the port through which the microcontroller is connected. You can find what the COM number is if you open Device Manager under the Ports Section.
Download the firmware.bin file and ensure it is named so.

Flash the microcontroller with the new firmware (ESP32-S3-DEVKITC1) Spiram Octal and the following prompt:
python -m esptool --chip esp32s3 --port COMX write_flash -z 0 firmware.bin
…should be good now if you are the chosen one…

Download and open the Thonny IDE.

Reset/Boot the microcontroller with the onboard button if the ide has not picked it up already.
Open the Thonny Options from the bottom-right-most section of the IDE. Ensure the appropriate microcontroller is selected, through the right port, and that it is running in Micropython (if micropython is desired).
If these are not configured, try with the selectable generic setups provided. Otherwise, click configure interpreter and go through the
