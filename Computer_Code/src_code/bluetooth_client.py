import asyncio, subprocess, time
from bleak import BleakClient, BleakScanner
import keyboard

# Constants
SERVER_NAME = "ESP-32 S3"
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_WRITE_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E" #server's rx
UART_READ_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E" #server's tx
#client write and read characteristic is the servers 'rx and tx' characteristics mirrored

FILE_PATH = r"C:\Users\adria\Downloads\bionic_arm_proj\data\angle_list.txt"

def start_computer_vision():
    script_path = r"C:\Users\adria\Downloads\bionic_arm_proj\src\Hand_tracking.py" 
    try:
        process = subprocess.Popen(["python", script_path], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
        print("Computer Vision script started.")
        return process
    except Exception as e:
        print(f"Failed to start Computer Vision script: {e}")
        return None
    
async def wait_for_cv_startup(seconds):
    print(f"Waiting for Computer Vision to start up...")
    for i in range(seconds):
        print(f"Waiting... {i+1}/{seconds}")
        await asyncio.sleep(1)
    print("Wait complete. Proceeding with data transmission.")

def read_file():
    with open(FILE_PATH, 'r') as file:
        return file.read().strip()

# def parse_data(data):
#     if not data:
#         return []
    
#     return [int(x) if x else 180
#             for x in data.split(',')]

def parse_data(data):
    if not data:
        return []
    
    values = data.split(',')
    parsed_data = []
    for i, x in enumerate(values):
        if i % 3 == 2:  #every third value (0-indexed) is a lateral angle
            parsed_data.append(90 if not x else int(x))
        else:
            parsed_data.append(180 if not x else int(x))
    return parsed_data

async def run_client():
    print("Scanning for device...")

    #await isn't necessary here, but find_device_by_name is an async function
    #so.... (could help if we have other functionalities that can be performed while looking 
    #for device)
    device = await BleakScanner.find_device_by_name(SERVER_NAME)
    

    if not device:
        print(f"Could not find device with name '{SERVER_NAME}'")
        return

    print(f"Found device: {device.name}")
    
    #set event
    disconnected_event = asyncio.Event()


    def disconnected_callback(client):
        print("device was disconnected, goodbye xx.")
        disconnected_event.set()

    #acctually connected to the esp32
    async with BleakClient(device, disconnected_callback=disconnected_callback) as client:
        print(f"Connected to {device.name}")

        #start computer vision before reading data, this is a synchronous operation
        #we do not want to start anything until this opens to read the data
        # cv_process = start_computer_vision()
        # if cv_process is None:
        #     print('CV was none... could not open, check exception')
        #     return
        
        #it takes a while for the computer vision to load right now
        # await wait_for_cv_startup(15)

        last_sent_data = None
        stop_flag = asyncio.Event()

        #stop program by pressing 'g'
        def on_press(key):
            if key.name == 'g':
                print("Stop key pressed. Ending program...")
                stop_flag.set()

        #set event (seperate thread listening)
        keyboard.on_press(on_press)

        #async because its a special case where its used as a callback function
        async def notification_handler(sender, data):
            if data == b'cunt':
                print("Server is shutting down.")
                stop_flag.set()

        await client.start_notify(UART_READ_CHAR_UUID, notification_handler)

        last_valid_data = None
        last_valid_time = 0
        data_timeout = 0.7  

        while not stop_flag.is_set() and client.is_connected:
            try:
                #do not need to be async because we need these things to happen before sending
                file_content = read_file()
                current_data = parse_data(file_content)

                #control data
                if any(current_data): #if all current data is truthy
                    last_valid_data = current_data
                    last_valid_time = time.time()
                elif last_valid_data and (time.time() - last_valid_time) < data_timeout:
                    current_data = last_valid_data
                else:
                    # current_data = [180] * 8
                    current_data = [180, 180, 90] * 4 #default position

                #check if at least one of the angles differs by 2 to indicate
                #a change in data then send that
                if last_sent_data is None or any(abs(a - b) >= 3 for a, b in zip(current_data, last_sent_data)):
                    
                    data_to_send = ','.join(map(str, current_data)).encode()
                    await client.write_gatt_char(UART_WRITE_CHAR_UUID, data_to_send)

                    print(f"Sent: {data_to_send}")
                    last_sent_data = current_data
                else:
                    print("angle is not significantly different, not sending.")

                await asyncio.sleep(0.3) #read every few .3second

            except Exception as e:
                print(f"An error occurred: {e}")
                break

        if not client.is_connected:
            print("Connection was lost.")

        print("Disconnecting...")
        await client.stop_notify(UART_READ_CHAR_UUID)

        # if cv_process:
        #     cv_process.terminate()
        #     print('Computer Vision closed!')

    await disconnected_event.wait()
    print('Disconnected!')

if __name__ == "__main__":
    asyncio.run(run_client())
