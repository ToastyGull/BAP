from bluetooth import * #for bluetooth.UUID() and FLAGS
from ble_advertising import advertising_payload
from micropython import const
import utime
from machine import Pin, PWM

pwm_pin = []
pin_numbers = [14]
frequency = 50

#constants for bluetooth events
#alerts-------------------------
_IRQ_CENTRAL_CONNECT = const(1) #alert for device connected
_IRQ_CENTRAL_DISCONNECT = const(2) #alert for device disconnect
_IRQ_GATTS_WRITE = const(3) #alert for receiving data

#constants for UART services
_UART_UUID = UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E") #service Identifier for bluetooth on device (think of it like the address for a home)
_UART_RX = (UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"), FLAG_WRITE) #use write for rx (receiver) tells client you can write
_UART_TX = (UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"), FLAG_NOTIFY) #use notify for tx (transmit), tells client there is a message for them
_UART_SERVICE = (_UART_UUID, (_UART_TX, _UART_RX)) #order of tuple does not matter

def servo_init(pin_num, freaqy):
    global pwm_pin
    for pinny in pin_numbers:
        pwm = PWM(Pin(pinny, mode=Pin.OUT))
        pwm.freq(freaqy)
        pwm_pin.append(pwm)
        
def set_servo_angle(servo_index, angle):
    if 0 <= servo_index < len(pwm_pin):
        try:
            d = map_angle_to_duty(angle)
            pwm_pin[servo_index].duty(d)
#         print('Setting servo {} to angle {} (duty {})'.format(servo_index, angle, dutyy)) debugging
        except ValueError as e:
            pass
        dutyy = map_angle_to_duty(angle)
        pwm_pin[servo_index].duty(dutyy)
        
def map_angle_to_duty(angle):
    duty = int(((angle - 0) * (130 - 30) / (180 - 0)) + 30)
#     print('Duty is: {} from angle {}'.format(duty, angle))
    return duty

class BLEServer:
    def __init__(self, ble, name="ESP-32 S3"):
        self._ble = ble #BLE object from main thread
        self._ble.active(True) #turning on bluetooth in radio chip
        self._ble.irq(self._handle_irq_event) #sets processes/handle blocks to deal with events
        ((self._tx_handle, self._rx_handle),) = self._ble.gatts_register_services((_UART_SERVICE,)) #rego the services
        self._ble.gatts_set_buffer(self._rx_handle, 64, False) #set buffer size on the bluetooth stack level, do not append (we have max 63 chars (1 byte each))
        self._connected_device = None #we are guaranteed only one device will be connected so we don't need a list
        self._is_connected = False #flag
        self._receiving_buffer = bytearray() #buffer for actual program storage not bluetooth
        self._handler = None
        self._payload = advertising_payload(name=name) #name to advertise, make sure client side is looking for the same name
        self._advertise() #start advertising
        self._keyboard_interrupt = False
          
    def _handle_irq_event(self, event, data):
        #if device is connected
        if event == _IRQ_CENTRAL_CONNECT:
            detected_device, _, _ = data
            if detected_device is None:
                print('Connection event was triggered, but the device was {}'.format(detected_device))
                return
            self._connected_device = detected_device
            self._is_connected = True
            print('Device connected') 
        
        #if device disconnects
        elif event == _IRQ_CENTRAL_DISCONNECT:
            disconnected_device, _, _ = data
            self._is_connected = False
            self._connected_device = None
            
            #in the case of a keyboard interrupt while client is still connected,
            #this print statement will be exectued last because micropython
            #bluetooth processes are async, so no its not a bug xx 
            print('Device was disconnected')
            
            if not self._keyboard_interrupt: #only advertise again if device disconnects on its own
                print('Here we go again...')
                self._advertise() #advertise again
        
        #if we have received data
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data #when client writes to rx, the data returned is diff from above cases
            
            if not self._is_connected:
                print('oddly received data but device is not connected')
                return
            
            if attr_handle == self._rx_handle: #if attribute read matches what was written to rx on client
                received_data = self._ble.gatts_read(self._rx_handle) #decode (in byte form by default)
                print('Received data: {}'.format(received_data.decode())) #for debugging (might decode using utf-8)
                self._receiving_buffer += received_data #add byte form to buffer
                if self._handler: #if handler is set then call it to handle the received data
                    self._handler() #hypothetically should be handling the received data

    def _advertise(self, interval_us=500000): #advertise every 0.5 seconds (microseconds (us))
        self._ble.gap_advertise(interval_us, adv_data=self._payload)
        print('Advertising...')
    
    #scalable handler function, however we are only receiving data and processing it so we only have one handler (process received data)
    def set_handler(self, handler):
        self._handler = handler
        
#     def check_for_data(self):
#         return len(self._receiving_buffer)
    
    def read_received_data(self):
        data = self._receiving_buffer
        self._receiving_buffer = bytearray() #reset the buffer
        try:
            return data.decode().strip()
        except UnicodeError:
            print('Error in decoding data: {}'.format(data))
            return "" #need to double check, this might be a bug but for now its not cos we never really use it yet
        
    def disconnect_device(self, keyboard_interrupt=False):
        self._is_connected = False
        self._connected_device = None
        self._keyboard_interrupt = keyboard_interrupt
        
    def send_shutdown_signal(self):
        if self._is_connected: #if device is still connected
            s = b'cunt'
            self._ble.gatts_notify(self._connected_device, self._tx_handle, s)
            utime.sleep_ms(1000) #1 second to let client receive

#functions outside bluetooth
def countdown():
    for i in range(1,6): #five seconds is good, it takes around 3-5 seconds for client to disconnect
        print('{}'.format(str(i)))
        utime.sleep_ms(1000)

def start_connection():
    ble = BLE()
    server = BLEServer(ble)
    
    servo_init(pin_numbers, frequency)
    
    def handle_received():
        message = server.read_received_data()
#         print('the message is: {}'.format(message))
        if message:
            try:
                angle_list = [int(angle.strip()) for angle in message.split(',')]
                if angle_list:
                    for i, angle in enumerate(angle_list):
                        if i < len(pin_numbers):
                            set_servo_angle(i, angle)
#                             print('{} angle set ({})'.format((i + 1), angle))
            except ValueError as e:
                print('Error processing received data: {} - Error is {}'.format(message, str(e)))
        else:
            print('No data received')
    
    server.set_handler(handle_received)
    
    try:
        while True: #infinite loop for bluetooth connection
            pass
#             utime.sleep_ms(100)
    except KeyboardInterrupt:
        print('Stopping...')
        server.send_shutdown_signal() #send to client to close
        #remove connected device
        server.disconnect_device(keyboard_interrupt=True)
        countdown() #letting client side properly terminate ('device was disconnected' should print inbetween this time as its in an async (implicit) function) 
    finally:
        #ble.active(False)
        print('Stopped!')
        
if __name__ == '__main__':
    start_connection()
