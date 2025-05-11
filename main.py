i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=100000)
lcd = LCD(addr=I2C_ADDR, cols=NUM_COLS, rows=NUM_ROWS, i2c=i2c)
lcd.begin()

do_connect()

client = MQTTClient(client_id="micropython", server=BROKER_IP, port=PORT, user=MQTT_USER, password=MQTT_PASS, ssl=True,)
client.set_callback(on_message)

try:
    print('Connecting to printer...')
    print1602_sentence(lcd, 'Connecting to printer...')

    client.connect()
    print('Connected')
    print1602_sentence(lcd, 'Connected to printer!')

    client.subscribe(TOPIC)

    client.publish(TOPIC, b'{"pushing": {"sequence_id": "0", "command": "pushall", "version": 1, "push_target": 1}}')
    
    while True:
        client.check_msg()
        time.sleep(LOOP_INTERVAL)

except Exception as e:
    print("Failed to connect to printer:", e)

finally:
    client.disconnect()