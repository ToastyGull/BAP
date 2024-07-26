import board
import busio
import time
import microcontroller
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685
from adafruit_ble import BLERadio
from adafruit_ble.uuid import UUID
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
import adafruit_ble
# https://docs.circuitpython.org/projects/pca9685/en/latest/api.html#adafruit_pca9685.PCA9685.channels
# https://docs.circuitpython.org/en/latest/shared-bindings/busio/#busio.I2C


#constantsss
DEVICE_NAME = "ESP-32 S3"
CHANNELS = 16 
FREQUENCY = 50
PCA_ADDRESS = 0x43 #0x43 or 0x60
MIN_PULSE = 586
MAX_PULSE = 2540 #pulses in microseconds

#uncomment these if line 42 doesn't work to be used in line 44-46
# UART_SERVICE_UUID = UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
# UART_RX_CHAR_UUID = UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
# UART_TX_CHAR_UUID = UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

#initialise i2c and pca objects
i2c = busio.I2C(microcontroller.pin.GPIO5, microcontroller.pin.GPIO4)
pca = PCA9685(i2c, address=PCA_ADDRESS)
pca.frequency = FREQUENCY

#initialise servos, <-- if ur testing full hand, u might need to adjust the initialisation of the servos
#in the correct order, either physically or hardcode it below
servos = []
for i in range(16):
    servos.append(servo.Servo(pca.channels[i], min_pulse=MIN_PULSE, max_pulse=MAX_PULSE))

#bluetooth server shit
ble = BLERadio()
uart_service = UARTService() #should be the same by default, if not, use the variable below instead:

# uart_service = UARTService(service_uuid=UART_SERVICE_UUID, 
#                            rx_uuid=UART_RX_CHAR_UUID, 
#                            tx_uuid=UART_TX_CHAR_UUID)

advertisement = ProvideServicesAdvertisement(uart_service)
advertisement.complete_name = DEVICE_NAME

def set_servo_angle(servo_index, angle):
    if 0 <= servo_index < len(servos):
        servos[servo_index].angle = angle
        time.sleep(0.1)

def handle_received_data(data):
    try:
        angle_list = [int(angle.strip()) for angle in data.split(',')]
        if angle_list:
            #you might need to adjust this part of the loop if you change the
            #order of the servo initialisations, but do note that the order of the angles are:
            #index(A,B,lat),middle(A,B,lat),ring(A,B,lat),pinky(A,B,lat) 
            #like: 180, 180, 90, 180, 180, 90, 180, 180, 90, 180, 180, 90
            for i, angle in enumerate(angle_list):
                if i < CHANNELS: 
                    set_servo_angle(i, angle)
    except ValueError as e:
        print(f'Error processing received data: {data} - Error is {str(e)}')

def send_shutdown_signal(connection):
    print("Sending shutdown signal to client...")
    uart_service.write(b'cunt')
    time.sleep(1) 

def countdown():
    for i in range(5, 0, -1):
        print(f"Shutting down in {i}...")
        time.sleep(1)

def start_connection():
    print("Waiting for connection...")
    ble.start_advertising(advertisement)

    try:
        was_connected = False
        while True:
            connection = ble.connected
            if connection and connection.connected:
                if not was_connected:
                    print("Connected!")
                    was_connected = True
                uart_service.reset_input_buffer()
                
                #while we are connected
                while connection.connected:
                    if uart_service.in_waiting:
                        received_data = uart_service.read().decode().strip()
                        print(f"Received: {received_data}")
                        handle_received_data(received_data)
                    
                    time.sleep(0.1) #read every 0.1 seconds
                
                print("Disconnected")
            
                if was_connected:
                    print("Client disconnected")
                    was_connected = False

            if not was_connected:
                ble.start_advertising(advertisement) 
                print("Advertising...") 
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Initiating shutdown process...")
        if ble.connected:
            send_shutdown_signal(ble.connected)
            countdown()
    finally:
        ble.stop_advertising()
        uart_service.deinit()
        pca.deinit()
        print("Bluetooth and PCA9685 shut down")

if __name__ == '__main__':
    start_connection()
    print('program done xx')
