import serial
import serial.tools.list_ports
import time


def find_arduino_port():
    """Recherche automatique du port de l'Arduino MKR1000."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "MKR1000" in port.description:  # Vérifie si c'est bien un Arduino MKR1000
            return port.device  
    return None


def wait_for_arduino_ready(ser):
    """Attend que l'Arduino envoie le signal 'READY'."""
    while True:
        response = ser.readline().decode().strip()
        if response == "READY":
            print("🚀 Arduino est prêt !")
            return
        print(f"⏳ En attente du signal READY... (Reçu: {response})")
        time.sleep(0.5)


def manual_mode(ser):

    print("🔹 Entrez les commandes sous la forme : mode, valeur, id")
    print("🔹 Tapez 'exit' pour quitter")

    try:
        mode = int(input("Mode (ex: 1) : "))
        value = int(input("Valeur (ex: 100) : "))
        device_id = int(input("ID (ex: 42) : "))

        data_to_send = f"{mode},{value},{device_id}\n"
        ser.write(data_to_send.encode())  # Envoyer les données
        print(f"📤 Données envoyées : {data_to_send.strip()}")

        # Lire la réponse de l'Arduino
        response = ser.readline().decode().strip()
        if response:
            print(f"📩 Réponse reçue : {response}")
        else:
            print("⚠️ Aucun retour reçu.")

    except ValueError:
        print("❌ Entrée invalide. Veuillez entrer des nombres entiers.")

    exit_choice = input("Envoyer une autre commande ? (o/n) : ").strip().lower()
    if exit_choice != "o":
        print("👋 Fermeture de la connexion...")
        return False
    else:
        return True
    




choix = "manual"

def main():
    """Boucle principale pour envoyer des commandes à l'Arduino."""
    arduino_port = find_arduino_port()

    if not arduino_port:
        print("❌ Aucun Arduino MKR1000 détecté. Vérifiez la connexion USB.")
        return

    print(f"✅ Arduino MKR1000 détecté sur {arduino_port}")

    try:
        ser = serial.Serial(arduino_port, baudrate=115200, timeout=2)
        time.sleep(2)  # Attendre la stabilisation de la connexion
        wait_for_arduino_ready(ser)

        

        if(choix == "manual"):

            print("Manual mode")
            test = True

            """Boucle pour envoyer des commandes à l'Arduino."""
            while test:
                test = manual_mode(ser)




        elif(choix == "auto"):
            print("Auto mode")




        ser.close()
        print("✅ Connexion série fermée.")

    except serial.SerialException as e:
        print(f"❌ Erreur série : {e}")


if __name__ == "__main__":
    main()
