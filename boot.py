# bundled umqtt.simple does not support SSL, replaced with commit 98d0a2b 
# https://github.com/micropython/micropython-lib/commit/98d0a2b69a24b9b53309be34d7c5aa6aede45c5e
from umqtts.simple import MQTTClient
import time
from lcd_i2c import LCD
from machine import I2C, Pin
import ujson
import network
try:
    from config import WIFI_SSID, WIFI_PASS, BROKER_IP, SERIAL_NUM, MQTT_PASS, PIN_SCL, PIN_SDA, BLANK_TIME
except ImportError:
    raise ImportError("Cannot import config.py! Copy config_template.py as config.py and fill in your details accordingly.")

# Does not require tinkering most of the time
MQTT_USER = "bblp"
PORT = 8883
LOOP_INTERVAL = 0.1
I2C_ADDR = 0x27

# Should not be tinkered with
NUM_ROWS = 2
NUM_COLS = 16
TOPIC = f"device/{SERIAL_NUM}/report"
current_layer = total_layers = progress = eta = error_code = None
current_line1 = current_line2 = ''

# Print on the 1602 LCD
def print1602(lcd, line1 = "Hello World!", line2 = '', do_sleep = False):
    global current_line1, current_line2
    if line1 == current_line1 and line2 == current_line2:
        return 0
    current_line1 = line1
    current_line2 = line2
    lcd.clear()
    if do_sleep:
        time.sleep(BLANK_TIME)
    lcd.set_cursor(col=0, row=0)
    lcd.print(line1)
    lcd.set_cursor(col=0, row=1)
    lcd.print(line2)
    return 1

# Print a full sentence on the 1602 LCD, splitting the text into two lines if it is too long
def print1602_sentence(lcd, text = "the quick brown fox jumps over the lazy dog"):
    if len(text) <= 16:
        line1 = text
        line2 = ''
    else:
        split_pos = text.rfind(' ', 0, 17)
        if split_pos == -1:
            line1 = text[:16]
            line2 = text[16:]
        else:
            line1 = text[:split_pos]
            line2 = text[split_pos+1:]

    return print1602(lcd, line1, line2)

def do_connect():
    sta_if = network.WLAN(network.WLAN.IF_STA)
    if not sta_if.isconnected():
        print('Connecting to network...')
        print1602_sentence(lcd, 'Connecting to network...')
        sta_if.active(True)
        sta_if.connect(WIFI_SSID, WIFI_PASS)
        while not sta_if.isconnected():
            time.sleep(0.1)
    try:
        network_config = sta_if.ipconfig('addr4')
        print('Network config:', network_config)
    except Exception as e:
        print('Failed to retrieve network config:', e)
        print1602_sentence(lcd, 'Network config error')
    print1602_sentence(lcd, 'Connected to network!')

def display_status(lcd, current_layer, total_layers, progress, eta):
    left1 = f"{current_layer}/{total_layers}"
    right1 = f"{progress}%"
    line1 = f"{left1:<12}{right1:>4}"[:16]

    line2 = f"ETA:{eta:>12}"[:16]

    return print1602(lcd, line1, line2, True)

def on_message(topic, msg):

    global current_layer, total_layers, progress, eta, error_code

    try:
        data = ujson.loads(msg)
        if "print" in data:
            print_data = data["print"]
            current_layer = print_data.get("layer_num", current_layer)
            total_layers = print_data.get("total_layer_num", total_layers)
            progress = print_data.get("mc_percent", progress)
            eta = print_data.get("mc_remaining_time", eta)
            error_code = print_data.get("print_error", error_code)
            
            if total_layers != None and total_layers != 0 and progress != 100 and error_code == 0:
                print(f"Layer: {current_layer}/{total_layers}")
                print(f"Progress: {progress}%")
                if isinstance(eta, int):
                    if eta >= 60:
                        eta_h = int(eta / 60)
                        eta_m = int(eta % 60)
                        eta = f'{eta_h}h{eta_m}m'
                    else:
                        eta = f'{eta}m'
                print(f"ETA: {eta}")
                print(f"=" * 16)
                display_status(lcd, current_layer, total_layers, progress, eta)
            # can only check idle if printer is idle after bootup
            elif total_layers == 0:
                print("No print job in progress")
                print1602_sentence(lcd, "No print job in progress")
            elif total_layers == None:
                print("Waiting for data from printer...")
                print1602_sentence(lcd, "Waiting for data from printer...")
            # TODO: Add logic to check if the print job is finished and display a message accordingly
            elif progress == 100:
                print("Print job finished")
                print1602_sentence(lcd, "Print job finished")
            # TODO: Add logic to check if error code is present and display a message accordingly
            elif error_code != 0:
                print(f"Printer error: {error_code}")
                print1602_sentence(lcd, f"Printer error: {error_code}")
            # TODO: Add logic to check if the print job is paused and display a message accordingly
    except Exception as e:
        print("Error parsing from json:", e)