import paho.mqtt.client as mqtt
import psutil  # For retrieving the IP address of the shared connection
import subprocess
import time

def get_shared_connection_ip():
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == 2:  # IPv4
                if addr.address.startswith("192.168.137.1"):
                    return addr.address
    return None

# Retrieve the shared connection IP automatically
shared_ip = get_shared_connection_ip()
if shared_ip:
    print(f"Detected IP Address: {shared_ip}")
else:
    print("Failed to detect the shared connection IP address.")
    raise SystemExit("Exiting program due to error.")

# MQTT Parameters
broker_ip = shared_ip  # PC's IP Address
topic = "commande_marcus"

# Callback executed when a message is received
def on_message(client, userdata, message):
    print(f"Message received: {message.payload.decode()}")

# Callback for connection errors
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Successfully connected to broker {broker_ip}")
        # Once connected, subscribe to the topic
        client.subscribe(topic)
    else:
        print(f"Connection failed, error code: {rc}")
        raise SystemExit("Exiting program due to connection error.")

# Launch Mosquitto broker with custom configuration file and verbose logging
def launch_mosquitto():
    try:
        # Replace with the full path to the Mosquitto executable and the configuration file
        mosquitto_path = r"C:\Program Files\mosquitto\mosquitto.exe"  # Example path for Windows
        config_path = r"C:\Program Files\mosquitto\Will.conf"  # Update with actual path
        subprocess.Popen([mosquitto_path, "-c", config_path])  # Use -v for verbose mode and -c for the custom config
        print("Mosquitto broker started with custom configuration and verbose logging...")
        time.sleep(3)  # Wait a few seconds to ensure Mosquitto starts up
    except Exception as e:
        print(f"Error starting Mosquitto: {e}")
        raise SystemExit("Exiting program due to Mosquitto launch failure.")

# Launch Mosquitto before running the MQTT code
launch_mosquitto()

# Create MQTT client
client = mqtt.Client("SubscriberPC")
client.on_message = on_message  # Assign callback function for messages
client.on_connect = on_connect  # Assign callback function for connection

# Connect to the broker (Mosquitto)
try:
    client.connect(broker_ip, 1883, 60)  # Specify port 1883 and timeout 60s
except Exception as e:
    print(f"Error connecting to broker: {e}")
    raise SystemExit("Exiting program due to connection failure.")

# Infinite loop to listen for messages
print(f"Waiting for messages on {topic}...")
client.loop_forever()
