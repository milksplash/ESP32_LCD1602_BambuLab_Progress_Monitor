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
    raise ImportError("Missing config.py! Copy config_template.py to config.py and fill in your details.")

# Does not require tinkering most of the time
MQTT_USER = "bblp"
PORT = 8883
LOOP_INTERVAL = 0.1
I2C_ADDR = 0x27

# Should not be tinkered with
NUM_ROWS = 2
NUM_COLS = 16
TOPIC = f"device/{SERIAL_NUM}/report"
current_layer = total_layers = progress = eta = None
current_line1 = current_line2 = ''

def print_n_update(lcd, line1 = "Hello World!", line2 = '', do_sleep = False):
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

def print1602(lcd, text = "Hello World!"):
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

    return print_n_update(lcd, line1, line2)

def do_connect():
    sta_if = network.WLAN(network.WLAN.IF_STA)
    if not sta_if.isconnected():
        print('Connecting to network...')
        print1602(lcd, 'Connecting to network...')
        sta_if.active(True)
        sta_if.connect(WIFI_SSID, WIFI_PASS)
        while not sta_if.isconnected():
            pass
    print('Network config:', sta_if.ipconfig('addr4'))
    print1602(lcd, 'Connected to network!')

def display_status(lcd, current_layer, total_layers, progress, eta):
    left1 = f"{current_layer}/{total_layers}"
    right1 = f"{progress}%"
    line1 = f"{left1:<12}{right1:>4}"[:16]

    line2 = f"ETA:{eta:>12}"[:16]

    return print_n_update(lcd, line1, line2, True)

def on_message(topic, msg):

    # global bed_temper
    global current_layer, total_layers, progress, eta

    try:
        data = ujson.loads(msg)
        if "print" in data:
            print_data = data["print"]
            current_layer = print_data.get("layer_num", current_layer)
            total_layers = print_data.get("total_layer_num", total_layers)
            progress = print_data.get("mc_percent", progress)
            eta = print_data.get("mc_remaining_time", eta)
            
            if total_layers != None and total_layers != 0:
                # print(f"Bed Temperature: {bed_temper}°C")
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
                
                # only update display if there is value update
                display_status(lcd, current_layer, total_layers, progress, eta)
            
            elif total_layers == 0:
                print("No print job in progress")
                # only update display if there is value update
                print1602(lcd, "No print job in progress")
            elif total_layers == None:
                print("Waiting for data from printer...")
                print1602(lcd, "Waiting for data from printer...")
    except Exception as e:
        print("Error parsing:", e)