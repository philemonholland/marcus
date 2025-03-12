import serial
import serial.tools.list_ports
import time
ACTIVATED_SERVOS = False

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
    try:
        movement_type = int(input("Type de mouvement (0:haut/bas 1:tilt) : "))
        value = int(input("Angle (ex: 100) : "))

        if movement_type == 0:
            value = max(-65, min(65, value))
            value = 90-value
            value_mot3 = 270 - value
            value_mot4 = value 
        else:
            value = max(70, min(110, value))  
            value_mot3 = value + 90
            value_mot4 = value

        # Send commands to motors
        data_to_send_mot3 = f"{0},{value_mot3},{3}\n"
        data_to_send_mot4 = f"{0},{value_mot4},{4}\n"
        ser.write(data_to_send_mot3.encode())  
        ser.write(data_to_send_mot4.encode())  
        print("📤 Données envoyées")

    except ValueError:
        print("❌ Entrée invalide. Veuillez entrer des nombres entiers.")

    return True

    
def read_serial(ser):
    while ser.in_waiting: 
        response = ser.readline().decode().strip()
        if response:
            print(f"📩 Réponse reçue : {response}")



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

        print("Manual mode")
        test = True

        while test:
            test = manual_mode(ser)  # Send command
            time.sleep(0.1)  # Allow time for the Arduino to process
            read_serial(ser)  # ✅ Non-blocking serial response printing

        ser.close()
        print("✅ Connexion série fermée.")

    except serial.SerialException as e:
        print(f"❌ Erreur série : {e}")

if __name__ == "__main__":
    main()
