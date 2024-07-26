import board
import busio
import time
import microcontroller
from adafruit_motor import servo 
from adafruit_pca9685 import PCA9685
# https://docs.circuitpython.org/projects/pca9685/en/latest/api.html#adafruit_pca9685.PCA9685.channels
# https://docs.circuitpython.org/en/latest/shared-bindings/busio/#busio.I2C

#initialise the i2c object
i2c = busio.I2C(microcontroller.pin.GPIO5, microcontroller.pin.GPIO4) #scl, sda, *, frequency, timeout
PCA_ADDRESS = 0x43 #0x43, 0x60
MIN_PULSE = 586
MAX_PULSE = 2540 #pulses given in microseconds

pca = PCA9685(i2c, address= PCA_ADDRESS)
pca.frequency = 50 #default freq --> 20ms

servos = []
try:
    for i in range(16):
        servos.append(servo.Servo(pca.channels[i], min_pulse=MIN_PULSE, max_pulse=MAX_PULSE))
except Exception as e:
    print(f"Error creating servo object: {e}")
    pca.deinit()
    exit(1)


for angle in range(180):
    for s in servos:
        s.angle = angle
    time.sleep(0.03)
for angle in range(180):
    for s in servos:
        s.angle = 180 - angle
    time.sleep(0.03)


pca.deinit()
