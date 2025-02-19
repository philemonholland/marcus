"""
EXEMPLES DE MESSAGES
{
  "timestamp": "2025-02-08T16:30:00Z",
  "source": "vision",
  "type": "event",
  "payload": {
    "x": 350,
    "y": 200,
    "emotion": "happy"
  }
}
{
  "timestamp": "2025-02-08T16:31:00Z",
  "source": "central",
  "type": "command",
  "payload": {
    "command": "TALK",
    "text": "Hello, how can I help you?"
  }
}
{
  "timestamp": "2025-02-08T16:32:00Z",
  "source": "central",
  "type": "command",
  "payload": {
    "command": "MIRROR EMOTION",
    "emotion": "anger"
  }
}

"""

# Fichier: common/communication.py
import json
import time
import paho.mqtt.client as mqtt

# Définition des topics communs pour la communication entre les sous-systèmes
TOPICS = {
    'VISION': 'marcus/vision',  # Topic pour les événements de vision (ex: détection de visage)
    'VOICE': 'marcus/voice',    # Topic pour la reconnaissance vocale (ex: commandes vocales)
    'LLM_REQUEST': 'marcus/llm/req',        # Topic pour l'IA générative (ex: réponses ou commandes)
    'LLM_RESPONSE': 'marcus/llm/res',        # Topic pour l'IA générative (ex: réponses ou commandes)
    'SERVOS': 'marcus/servos'   # Topic pour les commandes envoyées aux servos
}

def get_timestamp():
    """Retourne l'horodatage actuel au format ISO."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def create_message(source, msg_type, payload):
    """
    Crée un message JSON standardisé.

    Paramètres :
        source (str) : Source du message (ex: 'vision', 'voice', 'llm')
        msg_type (str) : Type du message ('event' pour un événement, 'command' pour une commande)
        payload (dict) : Données spécifiques au message

    Retourne :
        str : Chaîne JSON représentant le message.
    """
    message = {
        "timestamp": get_timestamp(),  # Ajoute un horodatage
        "source": source,              # Spécifie l'origine du message
        "type": msg_type,              # Indique s'il s'agit d'un événement ou d'une commande
        "payload": payload             # Contenu du message
    }
    return json.dumps(message)  # Convertit en chaîne JSON

def parse_message(message_str):
    """
    Analyse une chaîne JSON et retourne un dictionnaire.

    Paramètres :
        message_str (str) : La chaîne JSON représentant un message.

    Retourne :
        dict : Le message analysé sous forme de dictionnaire ou None en cas d'erreur.
    """
    try:
        return json.loads(message_str)  # Tente de convertir la chaîne JSON en dictionnaire
    except json.JSONDecodeError as e:
        print("Erreur lors du décodage du message :", e)  # Affiche l'erreur en cas d'échec
        return None

class MQTTClientWrapper:
    """
    A simple wrapper around the Paho MQTT client that provides a common interface.
    """
    def __init__(self, client_id, broker_address, broker_port=1883):
        self.client = mqtt.Client(client_id)
        self.broker_address = broker_address
        self.broker_port = broker_port

    def connect(self):
        """
        Connect to the MQTT broker.
        """
        self.client.connect(self.broker_address, self.broker_port, 60)

    def publish(self, topic, payload, qos=0):
        """
        Publish a message to a specified topic.
        
        Parameters:
            topic (str): The MQTT topic to publish to.
            payload (str): The payload to send (should be JSON-formatted).
            qos (int): Quality of Service level.
        """
        self.client.publish(topic, payload, qos=qos)

    def subscribe(self, topic, on_message_callback):
        """
        Subscribe to a topic with a given callback for handling messages.
        
        Parameters:
            topic (str): The topic to subscribe to.
            on_message_callback (callable): Function to call when a message arrives.
        """
        self.client.on_message = on_message_callback
        self.client.subscribe(topic)

    def loop_forever(self):
        """
        Enter a blocking loop to process MQTT network events.
        """
        self.client.loop_forever()

def create_mqtt_client(client_id, broker_address, broker_port=1883):
    """
    Creates and returns a Paho MQTT client that is connected to the specified broker.
    
    Parameters:
        client_id (str): Unique client ID.
        broker_address (str): MQTT broker IP address.
        broker_port (int): MQTT broker port.
        
    Returns:
        mqtt.Client: A connected MQTT client.
    """
    client = mqtt.Client(client_id)
    client.connect(broker_address, broker_port, 60)
    return client