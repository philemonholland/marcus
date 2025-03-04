import cv2
import numpy as np
import time
import paho.mqtt.client as mqtt
import json
from tensorflow.keras.models import load_model
from picamera2 import Picamera2



#Pour activer la communication
actif = True

#Connexion au broker MQTT
broker_ip = "192.168.243.2"  # IP du broker MQTT
topic = "commande_marcus"

client = mqtt.Client()
client.connect(broker_ip)

#Structure du message sous forme d'un dictionnaire
commande = {
    "x": 0,
    "y": 0,
    "z": 0,
    "emotion": "neutre"
}



# Function to draw rectangles around detections
def draw_rectangles(frame, detections, color, height=None):
    for (x, y, w, h) in detections:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        if height is not None:
            center_x = x + w // 2
            center_y = y + h // 2
            position_text = f"X: {center_x}, Y: {height-center_y}"
            cv2.putText(frame, position_text, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

# Function to predict emotions
def predict_emotion(face_region, model, emotions):
    resized = cv2.resize(face_region, (48, 48))
    normalized = resized / 255.0
    reshaped = np.reshape(normalized, (1, 48, 48, 1))  # reshape for model input
    predictions = model.predict(reshaped)
    emotion_label = np.argmax(predictions)
    return emotions[emotion_label]

def main():
    # Load cascades
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')

    # Load emotion recognition model and define emotions
    emotions = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']
    model = load_model('emotion_recognition_model.h5')

    # Initialize Picamera2
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (1536, 864)})
    picam2.configure(config)
    picam2.start()

    height = None
    
    
    intervall = 0.5
    next_time = time.time()
    
    x = 0
    y = 0
    z = 0
    emotion = ""

    while True:
        
        emotion = 'Neutral'
        
        frame = picam2.capture_array()
        if height is None:
            height = frame.shape[0]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=7, minSize=(30, 30))
        

        if len(faces) > 0:
        
            bigest_face = max(faces, key=lambda rect : rect[2] * rect[3])

            x,y,w,h = bigest_face

            face_region = gray[y:y + h, x:x + w]
            
            emotion = predict_emotion(face_region, model, emotions)
            draw_rectangles(frame, [(x, y, w, h)], (0, 255, 0), height)
            cv2.putText(frame, emotion, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Mise à jour des valeurs
            commande["x"] = x + w/2
            commande["y"] = -1*(y + h/2)
            #commande["z"] = w*h
            commande["emotion"] = emotion


        cv2.imshow('Face Detection with Emotion Recognition', frame)
        


        # Sauvegarde des valeurs précédentes
        x_precedent = x
        y_precedent = y
        z_precedent = z
        emotion_precedente = emotion

        # Publication MQTT
        message = json.dumps(commande)
        client.publish(topic, message)
        print("Message envoyé :", message)
        
        

        # Stop if any key is pressed
        if cv2.waitKey(1) != -1:
            client.disconnect()  # Déconnexion propre à la fin
            break

        next_time += intervall
        sleep_time = max(0, next_time - time.time())
        #print(sleep_time) #Debug tool
        time.sleep(sleep_time)

    picam2.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
