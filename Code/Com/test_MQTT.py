import paho.mqtt.client as mqtt

# Paramètres MQTT
broker_ip = "192.168.243.2"  # Adresse IP du PC
topic = "commande_marcus"

# Callback exécuté lorsqu'un message est reçu
def on_message(client, userdata, message):
    print(f"Message reçu: {message.payload.decode()}")

# Création du client MQTT
client = mqtt.Client("SubscriberPC")
client.on_message = on_message  # Assigner la fonction de callback

# Connexion au broker (Mosquitto)
client.connect(broker_ip)

# S'abonner au topic
client.subscribe(topic)

# Boucle infinie pour écouter les messages
print(f"En attente de messages sur {topic}...")
client.loop_forever()
