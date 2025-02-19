#!/usr/bin/env python3
import time
from common.communication import create_message, TOPICS, MQTTClientWrapper

# Adresse du broker MQTT (à adapter)
BROKER_ADDRESS = "192.168.1.100"

def publier_vision(x, y, emotion):
    # Crée le client MQTT pour le module vision
    mqtt_client = MQTTClientWrapper("VisionPublisher", BROKER_ADDRESS)
    mqtt_client.connect()
    
    # Crée le payload avec les coordonnées et l'émotion
    payload = {"x": x, "y": y, "emotion": emotion}
    message = create_message("vision", "event", payload)
    
    # Publie le message sur le topic VISION
    mqtt_client.publish(TOPICS['VISION'], message)
    print("Message vision publié :", message)
    # Optionnel: Déconnecter ou laisser tourner selon le design
    time.sleep(1)

if __name__ == "__main__":
    # Simulation: détection d'un visage à la position (350, 200) avec l'émotion "happy"
    publier_vision(350, 200, "happy")
