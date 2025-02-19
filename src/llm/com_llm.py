#!/usr/bin/env python3
import json
import time
from common.communication import create_message, parse_message, TOPICS, MQTTClientWrapper

BROKER_ADDRESS = "192.168.1.100"

# Cette fonction simule le traitement d'un message de vision
def on_vision_message(client, userdata, msg):
    message_str = msg.payload.decode()
    print("Message reçu sur", msg.topic, ":", message_str)
    message = parse_message(message_str)
    if message and message.get("payload"):
        # Extraction des données de vision
        payload = message["payload"]
        x = payload.get("x", 0)
        y = payload.get("y", 0)
        emotion = payload.get("emotion", "neutral")
        print(f"Vision détectée: x={x}, y={y}, emotion={emotion}")
        
        # Appeler la fonction qui gère la voix/LLM
        traiter_voix_llm(emotion, x, y)

# Simule le traitement vocal et l'appel à une API LLM.
def traiter_voix_llm(emotion, x, y):
    # Simuler la réception d'une phrase par le micro
    texte_vocal = "Bonjour, comment allez-vous?"
    print("Texte reconnu par le micro:", texte_vocal)
    
    # Ici, vous appelleriez une API LLM en passant le texte et l'émotion pour obtenir une réponse.
    # Pour cette simulation, on crée une réponse simulée.
    reponse_llm = f"Réponse modulée par l'émotion '{emotion}': Bien, merci!"
    print("Réponse LLM simulée:", reponse_llm)
    
    # Convertir le texte en parole (ici, on se contente d'afficher le résultat)
    # Ensuite, on envoie des commandes à l'Arduino via MQTT.
    envoyer_commande_servos("MOVE", {"x": x, "y": y, "z": 0})  # commande pour ajuster le regard (yeux)
    envoyer_commande_servos("SPEAK", {"text": reponse_llm})    # commande pour bouger la bouche

# Fonction pour publier une commande sur le topic SERVOS
def envoyer_commande_servos(command, params):
    mqtt_client = MQTTClientWrapper("CentralCommander", BROKER_ADDRESS)
    mqtt_client.connect()
    
    # Le payload inclut le nom de la commande et les paramètres associés.
    payload = {"command": command}
    payload.update(params)  # Ajoute x, y, z ou text, etc.
    message = create_message("central", "command", payload)
    
    mqtt_client.publish(TOPICS['SERVOS'], message)
    print("Commande envoyée aux servos:", message)
    time.sleep(1)

def main():
    # Créez un client MQTT qui s'abonne au topic VISION
    mqtt_client = MQTTClientWrapper("CentralSubscriber", BROKER_ADDRESS)
    mqtt_client.connect()
    
    # Abonnez-vous au topic de la vision et utilisez on_vision_message pour traiter les messages
    mqtt_client.client.on_message = on_vision_message
    mqtt_client.client.subscribe(TOPICS['VISION'])
    
    print("Central PC en attente des messages de vision...")
    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()
