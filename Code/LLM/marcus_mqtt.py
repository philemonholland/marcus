
# import whisper
import whisper_compat as whisper
import openai 
import azure.cognitiveservices.speech as speechsdk
import asyncio
import sounddevice as sd
import numpy as np
import tempfile
import os
from scipy.io.wavfile import write
from playsound import playsound
import time
import random
import re
from datetime import datetime
from directtsb import DirectTextToSpeech, VOICE_CONFIG, EMOTIONS, REACTIONS
import serial
import serial.tools.list_ports
import warnings
import psutil  # For retrieving the IP address of the shared connection
import subprocess
# from asyncio_mqtt import Client
import subprocess
import sys
import threading
from aiomqtt import Client
import json
import math

# Variable globale
pi_ready = False
arduino_ready = 0
old_angle_x = 0
old_angle_y = 0
mkr_serial_global = 0
# whisper_compat.py
# from faster_whisper import WhisperModel as FasterWhisperModel



if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

################################################################################################
################################################################################################
################################## COMMUNICATION MQTT ##########################################
"""
    - Permet au Raspberry Pi de communiquer avec le PC via MQTT pour envoyer des informations pour le contrôle des moteurs
      ainsi que l'émotion perçue par Marcus avec la caméra.
"""

# --- Fonctions de contrôle des moteurs (à remplacer par les fonctions réelles) ---
# --- MQTT configuration (optionnel, décommentez si nécessaire) ---
# broker_ip = "192.168.243.2"
# topic = "commande_marcus"
# mqtt_client = mqtt.Client("SubscriberPC")
# mqtt_client.connect(broker_ip)
# mqtt_client.subscribe(topic)
# mqtt_client.loop_start()  # Démarrer MQTT en arrière-plan

def get_shared_connection_ip():
    """Détecte l'IP associée à l'interface 192.168.137.70"""
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == 2:  # IPv4
                if addr.address.startswith("192.168.137.240"):
                    return addr.address
    return None


# Callback executed when a message is received
def on_message(client, userdata, message):
    print(f"Message received: {message.payload.decode()}")

# Retrieve the shared connection IP automatically
shared_ip = get_shared_connection_ip()
if shared_ip:
    print(f"Detected IP Address: {shared_ip}")
else:
    print("Failed to detect the shared connection IP address.")
    raise SystemExit("Exiting program due to error.")

    
def launch_mosquitto():
    global pi_ready
    """Lance Mosquitto avec le fichier de config custom"""
    try:
        mosquitto_path = r"C:\Program Files\mosquitto\mosquitto.exe"
        config_path = r"C:\Program Files\mosquitto\mosquitto.conf"
        subprocess.Popen([mosquitto_path, "-c", config_path])
        print("Mosquitto broker started with custom configuration and verbose logging...")
        pi_ready = True
        time.sleep(3)  # Laisse le temps à Mosquitto de démarrer
    except Exception as e:
        print(f"Error starting Mosquitto: {e}")
        raise SystemExit("Exiting program due to Mosquitto launch failure.")


###################################################################################################
###################################################################################################
################################## COMMUNICATION UART #############################################
"""
    - Permet au Raspberry Pi de communiquer avec l'Arduino via UART pour envoyer des informations pour le contrôle des moteurs
    - Permet de communiquer avec l'arduino MEGA pour allumer la boule de crystal lorsque MARCUS pense à une prédiction
"""

# Permet de trouver les ports auxquels sont connectés les Arduinos 
def find_arduino_port():
    """Recherche automatique du port de l'Arduino MKR1000 (moteurs) et Arduino Mega."""
    ports = serial.tools.list_ports.comports()
    #for port in ports:
    #    print("Device:", port.device)
    #    print("Name:", port.name)
    #    print("Description:", port.description)
    #    print("HWID:", port.hwid)
    #    print("-----------")

    mkr_port = None
    mega_port = None

    for port in ports:
        desc = port.description.lower()
        if "mkr" in desc:
            mkr_port = port.device  
        elif "mega" in desc:
            mega_port = port.device
     
    return mkr_port, mega_port


# Permet de s'assurer que la communication est bien établie et que l'Arduino est prêt à recevoir 
def wait_for_arduino_ready(ser, arduino, timeout_sec=10):
    global arduino_ready
    """Attend le message READY de l'Arduino (même s'il est noyé dans d'autres données)."""
    print("En attente du signal READY...")

    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            line = ser.readline().decode(errors='ignore').strip()
            print(f"(Reçu: {line})")
            if "READY" in line:
                arduino_ready += 1
                print(f'arduino_ready : ', arduino_ready)
                print("Arduino est prêt !")
                print(f"Connexion au {arduino} établie.")
                return True
        except Exception as e:
            print(f"Erreur de lecture : {e}")
            return False

    print("Timeout : GO non reçu.")
    return False


# Mode manuel pour les tests unitaires 
def manual_mode(ser):
    print("Entrez les commandes sous la forme : mode, valeur, id")
    print("Tapez 'exit' pour quitter")

    try:
        mode = int(input("Mode (ex: 1) : "))
        value = int(input("Valeur (ex: 100) : "))
        device_id = int(input("ID (ex: 42) : "))

        data_to_send = f"{mode} {value} {device_id}\n"
        # data_to_send = f"{0} {0} {0}\n"
        ser.write(data_to_send.encode())
        print(f"Données envoyées : {data_to_send.strip()}")

        response = ser.readline().decode().strip()
        if response:
            print(f"Réponse reçue : {response}")
        else:
            print("Aucun retour reçu.")

    except ValueError:
        print("Entrée invalide. Veuillez entrer des nombres entiers.")

    exit_choice = input("Envoyer une autre commande ? (o/n) : ").strip().lower()
    if exit_choice != "o":
        print("Fermeture de la connexion...")
        return False
    else:
        return True

# Fonction pour allumer la boule de crystal de Marcus
def eteint_boule_crystal(ser):
    global stop_recording
    ser.write(b'0')
    print("Envoi de '0' pour allumer la boule")

    timeout = time.time() + 2
    while time.time() < timeout:
        response = ser.readline().decode().strip()
        if response == "ACK0":
            print("ACK0 reçu : boule éteinte")
            stop_recording = False
            return True
        elif response == "ERR":
            print("Erreur : caractère non reconnu")
            return False
    print("Timeout : pas de réponse de l’Arduino")
    return False

# Fonction pour éteindre la boule de crystal de Marcus
def allume_boule_crystal(ser):
    global stop_recording
    ser.write(b'1')
    print("Envoi de '1' pour allumer la boule")

    timeout = time.time() + 2
    while time.time() < timeout:
        response = ser.readline().decode().strip()
        if response == "ACK1":
            print("ACK reçu : boule allumée")
            return True
        elif response == "ERR":
            print("Erreur : caractère non reconnu")
            return False
    print("Timeout : pas de réponse de l’Arduino")
    return False


# Fonction pour envoyer un état à Marcus
def send_state(state):
    global mkr_serial_global
    ser = mkr_serial_global
    #REACTIONS=["not impressed", "posessed", "angry", "sad", "fear", "surprise", "neutral"]

    if state == 'not impressed':
         ser.write(b'0 0 0')
    
    elif state == 'posessed':
        ser.write(b'1 0 0')

    elif state == 'angry':
        ser.write(b'2 0 0')

    elif state == 'sad':
        ser.write(b'3 0 0')

    elif state == 'fear':
        ser.write(b'4 0 0')
    
    elif state == 'surprise':
        ser.write(b'5 0 0')
    
    elif state == 'neutral':
        ser.write(b'6 0 0')

    elif state == 'lost':
        ser.write(b'7 0 0') ########## À RAJOUTER DANS LE CODE MOTEUR!!!!!

###################################################################################################
###################################################################################################
########################################## LLM ####################################################
class Config:
    # API Keys & Client Initialization
    SPEECH_KEY = "FQJu6fm0vm24eIZ2A9WZqgSc11cv90iFZTZPLFT5yauy23sSHZhQJQQJ99BCACREanaXJ3w3AAAYACOGGZ5S"
    SPEECH_REGION = "canadaeast"
    LISTEN_WHILE_SPEAKING = False
    VOICE_CONFIG = VOICE_CONFIG
    EMOTIONS = EMOTIONS
    REACTIONS= REACTIONS
    
tts = DirectTextToSpeech(Config)

# --- Load Whisper Model ---
warnings.filterwarnings("ignore", category=FutureWarning)
#model = whisper.load_model("large")   
# model = WhisperModel("large-v2", device="cuda", compute_type="float16")
#print("Modèle Whisper chargé.")
import whisper_compat as whisper

model = whisper.load_model("base", device="cpu")



# System prompt for Marcus
conversation = [
    {
        "role": "system",
        "content": (
        "Tu es une tête décapité robotique nommé Marcus le Fabuleux, une bête de foir dans un carnaval. "
        "Ton nom est Marcus, et tu spécialises à prédire l'avenir des gens en lisant les signaux neuroquantique. "
        "Tu as un accent Québecois très prononcé."
        "Tu es aussi cynique et sarcastique."
        "Tu es narcissique."
        "Tu es un romantique fini qui fait des longues déclarations d'amour."
        "'reaction' et 'msg'. "
        "IMPORTANT : La propriété 'reaction' doit être une des valeurs suivantes et AUCUNE AUTRE :"
        "\"not impressed\", \"posessed\", \"neutral\", \"angry\", \"sad\", \"fear\", \"surprise\", "
        "IMPORTANT : La propriété 'emotion' doit être une des valeurs suivantes et AUCUNE AUTRE : "
        "\"not impressed\", \"posessed\", \"neutral\", \"angry\", \"sad\", \"fear\", \"surprise\", "
        "EMOTION DOIT ËTRE IDENTIQUE A REACTION"
        "Exemple de format de réponse attendu: {\"reaction\": \"not impressed\", \"emotion\": \"fear\", \"msg\": \"Ton message ici\"} "
        "N'inclus PAS de retour à la ligne dans la propriété 'message' et n'utilise PAS de triple backticks "
        "ou de marqueurs json pour formater ta réponse."
        )
    }
]

def fix_json(json_str):
    """
    Supprime les virgules superflues avant les crochets fermants (} ou ]).
    """
    return re.sub(r',\s*(?=[}\]])', '', json_str)

def extract_json(json_str):
    """
    Extrait la partie JSON d'une chaîne pouvant contenir du markdown.
    """
    # Enlever les éventuelles balises de code Markdown
    json_str = re.sub(r"^```(?:json)?", "", json_str)
    json_str = re.sub(r"```$", "", json_str)
    # Extraire la sous-chaîne commençant par { et finissant par }
    start = json_str.find('{')
    end = json_str.rfind('}')
    if start != -1 and end != -1:
        return json_str[start:end+1]
    return json_str


# class ConversationMemory:
#     def __init__(self, memory_file="marcus_memory.json", max_memory_items=10):
#         self.memory_file = memory_file
#         self.max_memory_items = max_memory_items
#         self.memory = self.load_memory()
        
#     def load_memory(self):
#         """Load memory from file or create a new one if it doesn't exist"""
#         try:
#             with open(self.memory_file, 'r', encoding='utf-8') as f:
#                 return json.load(f)
#         except (FileNotFoundError, json.JSONDecodeError):
#             # Initialize empty memory structure
#             return {
#                 "user_info": {},
#                 "interactions": [],
#                 "facts_learned": [],
#                 "last_session": None
#             }
    
#     def save_memory(self):
#         """Save memory to file"""
#         with open(self.memory_file, 'w', encoding='utf-8') as f:
#             json.dump(self.memory, f, ensure_ascii=False, indent=2)
    
#     def add_interaction(self, user_input, marcus_response, emotion, reaction):
#         """Add a new interaction to memory"""
#         timestamp = datetime.now().isoformat()
        
#         # Extract user information from input (e.g., name, preferences)
#         self._extract_user_info(user_input)
        
#         # Add interaction to history
#         self.memory["interactions"].append({
#             "timestamp": timestamp,
#             "user_input": user_input,
#             "marcus_response": marcus_response,
#             "emotion": emotion,
#             "reaction": reaction
#         })
        
#         # Keep only the most recent interactions
#         if len(self.memory["interactions"]) > self.max_memory_items:
#             self.memory["interactions"] = self.memory["interactions"][-self.max_memory_items:]
        
#         # Update last session
#         self.memory["last_session"] = timestamp
        
#         # Save to file
#         self.save_memory()
    
#     def _extract_user_info(self, user_input):
#         """Extract potential personal information from user input"""
#         # Simple name extraction (very basic example)
#         name_patterns = [
#             r"je m'appelle ([A-Za-zÀ-ÿ]+)",
#             r"mon nom est ([A-Za-zÀ-ÿ]+)"
#         ]
        
#         import re
#         for pattern in name_patterns:
#             match = re.search(pattern, user_input.lower())
#             if match:
#                 self.memory["user_info"]["name"] = match.group(1).capitalize()
        
#         # You could add more sophisticated extraction here
    
#     def get_memory_summary(self, limit=3):
#         """Get a summary of memory for context insertion"""
#         summary = ""
        
#         # Add user info if available
#         if "name" in self.memory["user_info"]:
#             summary += f"L'utilisateur s'appelle {self.memory['user_info']['name']}. "
        
#        # Add recent interactions
#         if self.memory["interactions"]:
#             summary += "Voici les dernières interactions:\n"
#             recent = self.memory["interactions"][-limit:]
#             for interaction in recent:
#                 summary += f"- Utilisateur: \"{interaction['user_input']}\"\n"
#                 summary += f"- Marcus ({interaction['emotion']}): \"{interaction['marcus_response']}\"\n"
        
#     #    # Add recent interactions
#     #     if self.memory["interactions"]:
#     #         summary += "Voici les dernières interactions:\n"
#     #         recent = self.memory["interactions"][-limit:]
#     #         for idx, interaction in enumerate(recent, start=1):
#     #             summary += f"{idx}. Utilisateur: \"{interaction['user_input']}\"\n"
#     #             summary += (
#     #                 f"   Marcus ({interaction['emotion']}, {interaction['reaction']}): "
#     #                 f"\"{interaction['marcus_response']}\"\n"
#     #             )
        
#         # Add session awareness
#         if self.memory["last_session"]:
#             last_time = datetime.fromisoformat(self.memory["last_session"])
#             now = datetime.now()
#             days_diff = (now - last_time).days
            
#             if days_diff == 0:
#                 if self.memory["interactions"]:
#                     summary += "C'est une conversation en cours aujourd'hui."
#             elif days_diff == 1:
#                 summary += "L'utilisateur était là hier aussi."
#             else:
#                 summary += f"L'utilisateur revient après {days_diff} jours d'absence."
        
#         return summary



# --- Modify your chat_request function ---
def chat_request(request: str):
    # Get memory summary to include in the system message
    # memory_context = memory.get_memory_summary()
    
    # # Update the system message with memory context
    # if memory_context:
    #     # Find the system message
    #     for i, message in enumerate(conversation):
    #         if message["role"] == "system":
    #             # Keep the JSON instruction at the end
    #             base_content = message["content"]
    #             json_instruction_part = "\n\nTRÈS IMPORTANT: Ta réponse DOIT être un objet JSON valide"
                
    #             # Split at the JSON instruction if it exists
    #             if json_instruction_part in base_content:
    #                 parts = base_content.split(json_instruction_part)
    #                 # Add memory context before the JSON instruction
    #                 conversation[i]["content"] = f"{parts[0]}\n\nMémoire récente: {memory_context}{json_instruction_part}{parts[1]}"
    #             else:
    #                 # Just append to the end if JSON instruction not found
    #                 conversation[i]["content"] = f"{base_content}\n\nMémoire récente: {memory_context}"
    #             break
    
    # Rest of your existing function
    conversation.append({"role": "user", "content": request})
    openai.api_key="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"

    # response = openai.ChatCompletion.create(
    #     model="gpt-3.5-turbo",
    #     messages=conversation,
    #     max_tokens=400,
    #     temperature=1.02
    #     )
    # reply_raw = response.choices[0].message.content.strip()
    
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=conversation,
        max_tokens=400,
        temperature=1.02
        )
    reply_raw = response.choices[0].message.content.strip()

    # Process response for JSON extraction
    reply_extracted = extract_json(reply_raw)
    fixed_reply = fix_json(reply_extracted)
    
    try:
        # Try to parse as JSON first
        reply_json = json.loads(fixed_reply)
        reaction = reply_json.get("reaction", random.choice(REACTIONS))
        emotion = reply_json.get("emotion", random.choice(EMOTIONS))
        message = reply_json.get("msg", reply_raw)
    except json.JSONDecodeError:
        # If that fails, look for a fallback pattern (e.g., key-value pairs in text)
        print("Erreur: Réponse non valide en JSON, tentative de récupération...")
        
        # Fallback: Try to extract emotion and message from text format
        reaction_match = re.search(r'"reaction"\s*:\s*"([^"]+)"', reply_raw)
        emotion_match = re.search(r'"emotion"\s*:\s*"([^"]+)"', reply_raw)
        message_match = re.search(r'"msg"\s*:\s*"([^"]+)"', reply_raw)
        
        if emotion_match and message_match and reaction_match:
            reaction_match = reaction_match.group(1)
            emotion = emotion_match.group(1)
            message = message_match.group(1)
            print("Récupération réussie!")
        else:
            # If all else fails, use the raw response as the message
            print("Échec de la récupération. Utilisation du texte brut.")
            reaction = random.choice(reaction)
            emotion = random.choice(EMOTIONS)
            message = reply_raw
    
    conversation.append({"role": "assistant", "content": reply_raw})
    
    # Add this interaction to memory
    #memory.add_interaction(request, message, emotion, reaction)
    
    return emotion, reaction, message

# --- Audio Parameters ---
SAMPLERATE = 16000
DURATION = 6



async def azure_text_to_speech(text, output_file, emotion="happy"):
    """Use the DirectTextToSpeech class instead of the old method"""
    print(f"Speaking with emotion: {emotion}")

    
    # Call the synthesize_speech method and wait for it to complete
    player_thread = await tts.synthesize_speech(text, emotion)
    
    # If a thread was returned, wait for it to complete
    if player_thread:
        player_thread.join()
    
    return True

def azure_tts_sync(text, output_file, emotion="happy"):
    """
    Using the alternative approach that worked in your tests.
    This uses speak_text_async instead of speak_ssml_async.
    """
    speech_config = speechsdk.SpeechConfig(subscription=Config.SPEECH_KEY, region=Config.SPEECH_REGION)
    
    # Voice mapping based on emotion
    voice_mapping = {
        "assistant": "fr-CA-JeanNeural",
        "angry": "fr-CA-JeanNeural",
        "chat": "fr-CA-JeanNeural",
        "cheerful": "fr-CA-JeanNeural",
        "customerservice": "fr-CA-JeanNeural",
        "excited": "fr-CA-JeanNeural",
        "friendly": "fr-CA-JeanNeural",
        "hopeful": "fr-CA-JeanNeural",
        "newscast": "fr-CA-JeanNeural",
        "sad": "fr-CA-JeanNeural",
        "shouting": "fr-CA-JeanNeural",
        "terrified": "fr-CA-JeanNeural",
        "unfriendly": "fr-CA-JeanNeural",
        "whispering": "fr-CA-JeanNeural"
    }
    
    voice_name = voice_mapping.get(emotion, "fr-CA-JeanNeural")
    
    # Set the voice name
    speech_config.speech_synthesis_voice_name = voice_name
    
    # Set the output format
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    
    # Create the audio output config
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    
    # Create the synthesizer
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )
    
    # Use speak_text_async instead of speak_ssml_async
    result = speech_synthesizer.speak_text_async(text).get()
    
    return result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted


def record_audio_with_vad(on_recording_finished=None, loop=None):
    """
    Enregistre l'audio avec détection de parole (VAD) et sauvegarde dans un fichier temporaire WAV.
    
    Paramètres:
      on_recording_finished (callable, optionnel) : Fonction callback déclenchée une fois l'enregistrement terminé.
      loop (asyncio.AbstractEventLoop, optionnel) : La boucle d'événements pour exécuter le callback dans le thread principal.
    
    Retourne:
      Le nom du fichier temporaire contenant l'enregistrement audio si l'enregistrement est réussi,
      ou None en cas d'échec (par exemple, s'il n'y a pas eu de parole détectée).
    """
    global stop_recording  # suppose que stop_recording est déclaré ailleurs dans votre code
    SAMPLERATE = 16000
    CHUNK_SIZE = 1024
    MAX_DURATION = 15        # en secondes
    SILENCE_THRESHOLD = 0.015
    SILENCE_DURATION = 2   # en secondes

    print("Attente de parole... (commencez à parler)")

    audio_buffer = []
    is_recording = False
    silence_frames = 0
    max_frames = int(MAX_DURATION * SAMPLERATE)
    frames_recorded = 0

    try:
        with sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='float32', blocksize=CHUNK_SIZE) as stream:
            timeout_counter = 0
            while frames_recorded < max_frames:
                audio_chunk, overflowed = stream.read(CHUNK_SIZE)
                if overflowed:
                    print("Dépassement de la mémoire tampon d'entrée")

                chunk_energy = np.mean(np.abs(audio_chunk))
                
                # Début de l'enregistrement dès que de la parole est détectée
                if chunk_energy > SILENCE_THRESHOLD and not is_recording:
                    print("Parole détectée, enregistrement en cours...")
                    send_state('posessed')
                    is_recording = True

                if is_recording:
                    audio_buffer.append(audio_chunk.copy())
                    frames_recorded += len(audio_chunk)
                    
                    # Gestion de la détection de silence pour terminer l'enregistrement
                    if chunk_energy <= SILENCE_THRESHOLD:
                        silence_frames += len(audio_chunk)
                        if silence_frames >= int(SILENCE_DURATION * SAMPLERATE):
                            print(f"Silence détecté pendant {SILENCE_DURATION}s, fin de l'enregistrement.")
                            stop_recording = True
                            
                            break
                    else:
                        silence_frames = 0
                else:
                    timeout_counter += 1
                    # Timeout de 10 secondes si aucune parole n'est détectée
                    if timeout_counter >= int(10 * SAMPLERATE / CHUNK_SIZE):
                        print("Aucune parole détectée après 10 secondes d'attente.")
                        timeout_counter = 0
                        is_recording = False
                        #return None
                    
    except Exception as e:
        print(f"Erreur durant l'enregistrement : {e}")
        import traceback
        traceback.print_exc()
        return None

    if not is_recording or len(audio_buffer) == 0:
        print("Aucun enregistrement valide.")
        return None

    # Concatène tous les fragments audio enregistrés en un seul tableau mono
    audio_mono = np.concatenate(audio_buffer).flatten()
    print(f"Enregistrement terminé. Durée: {len(audio_mono) / SAMPLERATE:.2f}s")

    # Déclenche le callback (si défini) dans le thread principal
    if on_recording_finished and loop is not None:
        asyncio.run_coroutine_threadsafe(on_recording_finished(), loop)

    # Normalisation de l'audio
    if np.max(np.abs(audio_mono)) > 0:
        audio_mono = audio_mono / np.max(np.abs(audio_mono)) * 0.9

    noise_threshold = 0.01
    audio_mono[np.abs(audio_mono) < noise_threshold] = 0

    try:
        # Crée un fichier temporaire dans lequel sauvegarder l'enregistrement
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
            write(temp_filename, SAMPLERATE, (audio_mono * 32767).astype(np.int16))
    except Exception as e:
        print(f"Erreur lors de l'écriture du fichier audio : {e}")
        return None

    return temp_filename

def transcribe_audio_file(temp_filename, language="fr", temperature=0.2, beam_size=5):
    """
    Transcrit l'audio contenu dans le fichier WAV spécifié.
    
    Paramètres:
      temp_filename (str) : Chemin du fichier audio à transcrire.
      language (str, optionnel) : La langue utilisée pour la transcription (par défaut "fr").
      temperature (float, optionnel) : Paramètre de température pour le modèle de transcription.
      beam_size (int, optionnel) : Taille du beam de recherche pour la transcription.
      fp16 (bool, optionnel) : Utilisation de la précision fp16 (par défaut False).

    Retourne:
      La transcription textuelle si la transcription est un succès, sinon None.
    """
    
    try:
        print("Transcription en cours...")
        
        result = model.transcribe(
            temp_filename,
            language=language,
            temperature=temperature,
            beam_size=beam_size,
            #fp16=fp16
        )
        transcription = result.get("text", "")
        
        return transcription.strip() if transcription else None
    except Exception as e:
        print(f"Erreur pendant la transcription : {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Supprime le fichier temporaire après la transcription
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
                print(f"Fichier temporaire supprimé : {temp_filename}")
            except Exception as e:
                print(f"Erreur en supprimant le fichier temporaire : {e}")

###############################################################################################
###############################################################################################
################################## PIPELINES ##################################################

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
- Le code ci-dessous est la boucle principale de Marcus, qui gère les différentes tâches asynchrones.
- Chaque tâche est responsable d'une partie spécifique du système, comme l'enregistrement audio, la transcription,
- Asyncio propose une boucle d'événements (event loop) qui exécute des tâches de manière coopérative
- Au lieu d'avoir un grand nombre de threads qui se bloquent mutuellement, asyncio permet d'éxécuter du
  code asynchrone dans un seul thread (event loop), et change de tâche chaque fois qu'une tâche attend quelque chose
  (Par exemple, un I/O ou un await)

  => Pas de blocage (asyncio passe la main à une autre tâche)
  => Communication plus simple (partage de file d'attente entre les tâches)

- record_and_transcribe_with_vad() est exécutée dans un thread séparé (sans asyncio) pour éviter de bloquer la boucle d'événements,
  parce que la fonction est bloquante de nature 
  => asyncio.run_in_executor() permet d'exécuter une fonction bloquante dans un thread séparé

- Donc au final, on a deux threads : un pour la boucle d'événements asyncio et un pour l'enregistrement audio
  => Réduction de la latence et amélioration de la réactivité du système

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

# Fonction de contrôle des moteurs
async def mkr_loop(mkr_command_queue, mkr_serial):
    while True:
        cmd = await mkr_command_queue.get()
        mkr_serial.write(cmd.encode() if isinstance(cmd, str) else cmd)
        response = mkr_serial.readline().decode().strip()
        print(f"[MKR] Réponse : {response}")


# Fonction de contrôle des lumières du présentoir (boule de crystal entre autres)
async def mega_loop(mega_command_queue, mega_serial):
    while True:
        cmd = await mega_command_queue.get()
        mega_serial.write(cmd.encode() if isinstance(cmd, str) else cmd)
        response = mega_serial.readline().decode().strip()
        print(f"[MEGA] Réponse : {response}")



async def listener_loop(transcription_queue, mega_command_queue, can_record):
    loop = asyncio.get_running_loop()

    async def on_recording_finished():
        await mega_command_queue.put(b'1')   # boule ON

    while True:
        await can_record.wait()             # ← bloque tant qu’on parle

        wav_path = await loop.run_in_executor(
            None, record_audio_with_vad, on_recording_finished, loop
        )
        if not wav_path:
            continue

        text = await loop.run_in_executor(None, transcribe_audio_file, wav_path)
        if text:
            await transcription_queue.put(text)
            send_state('neutral')




# async def mqtt_listener_loop(broker_ip, mkr_command_queue, topic="commande_marcus"):
#     try:
#         print(f"Attempting MQTT connect to {broker_ip}:1883 ...")
#         async with Client(broker_ip) as client:
#             print(f"Successfully connected to broker {broker_ip}")
#             await client.subscribe(topic)
#             print(f"Abonné à {topic}")

#             async for message in client.messages:
#                 try:
#                     payload_str = message.payload.decode()
#                     print(f"[MQTT] Message reçu sur {topic}: {payload_str}")

#                     # Essaie de parser le JSON, mais tolère aussi du texte brut
#                     try:
#                         payload_data = json.loads(payload_str)
#                         #await mkr_command_queue.put(payload_data)
#                     except json.JSONDecodeError:
#                         print("[MQTT] Message non-JSON, traité comme string brut")
#                         #await mkr_command_queue.put(payload_str)

#                 except Exception as msg_err:
#                     print(f"[MQTT] Erreur en traitant un message : {msg_err}")

#     except Exception as e:
#         print(f"[MQTT] Erreur de connexion ou d'écoute : {e}")


# Fonction de contrôle des moteurs via MQTT
async def mqtt_listener_loop(broker_ip, mkr_serial, topic="commande_marcus"):
    global old_angle_x
    global old_angle_y
    
    try:
        print(f"Attempting MQTT connect to {broker_ip}:1883 ...")
        async with Client(broker_ip) as client:
            print(f"Successfully connected to broker {broker_ip}")
            await client.subscribe(topic)
            print(f"Abonné à {topic}")

            while True:
                async for message in client.messages:
                    try:
                        payload_str = message.payload.decode()
                        print(f"[MQTT] Message reçu sur {topic}: {payload_str}")

                        # Essaie de parser le JSON, mais tolère aussi du texte brut
                        try:

                            ########################################################################
                            # Si le message est du JSON, on l'analyse
                            payload_data = json.loads(payload_str)
                            # Extract x, y, z, and emotion if they exist
                            x = payload_data.get("x")
                            y = payload_data.get("y")
                            z = payload_data.get("z")
                            emotion_camera = payload_data.get("emotion")
                            #print(f"[MQTT] Position: x={x}, y={y}, z={z}")
                            #print(f"[MQTT] Emotion: {emotion}")

                            height = 100 # VALEUR À CHANGER
                            depth = 50 # VALEUR À CHANGER

                            z = z + depth
                            y = y - height

                            angle_y = math.degrees(math.atan2(x, z))  # angle en radians        # Mettre .degrees() si on veut l'angle en degrés
                            angle_x = math.degrees(math.atan2(y, z))  # angle en radians        # Mettre .degrees() si on veut l'angle en degrés
                            if abs(old_angle_y-angle_y) > 10:
                                old_angle_y = angle_y
                                send_angle(mkr_serial, angle_y, 1)

                            if abs(old_angle_x-angle_x) > 10:
                                old_angle_x = angle_x
                                send_angle(mkr_serial, angle_x, 0)

                            """
                            if emotion_camera is 'lost':
                                send_state(mkr_serial, 'lost')

                            """
                            # Optionally: send structured data to queue
                            # await mkr_command_queue.put({
                            #     "x": x,
                            #     "y": y,
                            #     "z": z,
                            #     "emotion": emotion
                            # })

                        except json.JSONDecodeError:
                            print("[MQTT] Message non-JSON, traité comme string brut")
                            #await mkr_command_queue.put(payload_str)

                    except Exception as msg_err:
                        print(f"[MQTT] Erreur en traitant un message : {msg_err}")
    except Exception as e:
        print(f"[MQTT] Erreur de connexion ou d'écoute : {e}")


def send_angle(ser, angle, axis):
     
        
        movement_type = axis
        value = angle

        if movement_type == 0:
            value = max(-65, min(65, value))
            value = int(value)  # Co
            value = 90-value
            value_mot3 = 270 - value
            value_mot4 = value
            data_to_send_mot3 = f"{-1} {value_mot3} {3}\n"
            data_to_send_mot4 = f"{-1} {value_mot4} {4}\n" 
            ser.write(data_to_send_mot3.encode())  
            ser.write(data_to_send_mot4.encode())  
            print(f"Moteur 3,4 : {data_to_send_mot3}, {data_to_send_mot4}📤 Données envoyées")
        elif movement_type == 1:
            value = value+61
            value = max(61-45, min(61+45, value)) # À determiner
            value = int(value)  # Co
            value_mot20 = value
            data_to_send_mot20 = f"{-1} {value_mot20} {20}\n"
            ser.write(data_to_send_mot20.encode())  
            print(f"Moteur20 : {data_to_send_mot20} 📤 Données envoyées")
        else:
            value = max(70, min(110, value))  
            value = int(value)  # Convertir en entier
            value_mot3 = value + 90
            
            value_mot4 = value
            data_to_send_mot3 = f"{-1} {value_mot3} {3}\n"
            data_to_send_mot4 = f"{-1} {value_mot4} {4}\n"
            ser.write(data_to_send_mot3.encode())  
            ser.write(data_to_send_mot4.encode())  
            print(f"Moteur 3,4 : {data_to_send_mot3}, {data_to_send_mot4}📤 Données envoyées")

# Traitement de la voix avec chatGPT
async def processing_loop(transcription_queue, response_queue):
    while True:
        user_text = await transcription_queue.get()

        emotion, reaction, message = chat_request(user_text)

        await response_queue.put((emotion, message))

# Fonction de synthèse vocale
async def speaker_loop(response_queue, mega_command_queue, can_record,mkr_serial):
    while True:
        # Boule OFF et **interdiction d’enregistrer**
        await mega_command_queue.put(b'0')

        # On interdit Marcus d'enregistrer tant qu'il parle
        can_record.clear()

        emotion, msg = await response_queue.get()
        emotion = emotion if emotion in REACTIONS else random.choice(REACTIONS)
        print(f"[TTS] {emotion}: {msg}")
        send_state(emotion)

        await azure_text_to_speech(msg, None, emotion)

        # Petit délai pour laisser mourir l’écho, puis on ré‑active
        await asyncio.sleep(0.5)
        can_record.set()



###############################################################################################
###############################################################################################
################################## MAIN () ####################################################

async def main():
    global pi_ready
    global arduino_ready
    global mkr_serial_global
    print("Démarrage de MarcUS...")

    # Lancement de Mosquitto
    launch_mosquitto()

    # Détection de l'IP du broker MQTT
    shared_ip = get_shared_connection_ip()
    if shared_ip:
        print(f"Adresse IP détectée: {shared_ip}")
    else:
        print("Échec de connexion à l'adresse IP.")
        raise SystemExit("Exiting program due to error.")
    
    # Activer le mega
    _, mega_port = find_arduino_port()
    if not mega_port:
        print(" Arduino Mega non détecté.")
        raise RuntimeError("Connexion au MEGA échouée.")
    try:
        mega_serial = serial.Serial(mega_port, baudrate=115200, timeout=2)
        wait_for_arduino_ready(mega_serial, 'Mega')
        time.sleep(2)
        mega_serial.reset_input_buffer()
    except serial.SerialException as e:
        print(f"[MEGA] Erreur : {e}")

    print(f'arduino_ready (main loop) : ', arduino_ready)
    while True:
        if arduino_ready >= 0:
            break
        
    # Activer le MKR
    mkr_port, _ = find_arduino_port()
    if not mkr_port:
        print(" Arduino MKR non détecté.")
        #raise RuntimeError("Connexion au MKR1000 échouée.")
    try:
        mkr_serial = serial.Serial(mkr_port, baudrate=115200, timeout=2)
        mkr_serial_global = mkr_serial
        wait_for_arduino_ready(mkr_serial, 'MKR')
        time.sleep(2)
        mkr_serial.reset_input_buffer()
    except serial.SerialException as e:
        print(f"[MKR] Erreur : {e}")
    


    # lancer la boucle d'écoute MQTT
    broker_ip = shared_ip
    topic = "commande_marcus"


    # Crée les files de communication entre les tâches
    transcription_queue = asyncio.Queue()
    response_queue = asyncio.Queue()
    mega_command_queue = asyncio.Queue()
    mkr_command_queue = asyncio.Queue(maxsize=30) #Maxsize pour éviter le débordement
    print("initialisation des modules de Marcus...")

    can_record = asyncio.Event()
    can_record.set()


    while True:
        if arduino_ready >= 2 and pi_ready:
            break

    # Lance toutes les tâches en parallèle
    print(" Tout est prêt. MarcUS est réveillé.")
    await asyncio.gather(
    listener_loop(transcription_queue, mega_command_queue, can_record),
    processing_loop(transcription_queue, response_queue),
    # mqtt_listener_loop(broker_ip, mkr_command_queue), 
    mqtt_listener_loop(broker_ip, mkr_serial), 
    speaker_loop(response_queue, mega_command_queue, can_record, mkr_serial),
    mega_loop(mega_command_queue, mega_serial),
    mkr_loop(mkr_command_queue, mkr_serial)
    )


if __name__ == "__main__":
    asyncio.run(main())