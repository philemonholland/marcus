import whisper
from openai import OpenAI
import azure.cognitiveservices.speech as speechsdk
import asyncio
import sounddevice as sd
import numpy as np
import tempfile
import os
from scipy.io.wavfile import write
from playsound import playsound
import time
import json
import random
import re
import json
from datetime import datetime
from directtsb import DirectTextToSpeech, VOICE_CONFIG, REACTIONS
import serial
import serial.tools.list_ports
import warnings
import psutil  # For retrieving the IP address of the shared connection
import subprocess
from asyncio_mqtt import Client
from aiomqtt import Client
import psutil
import subprocess
import sys
import threading
from aiomqtt import Client
import json



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
                if addr.address.startswith("192.168.137.70"):
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
    """Lance Mosquitto avec le fichier de config custom"""
    try:
        mosquitto_path = r"C:\Program Files\mosquitto\mosquitto.exe"
        config_path = r"C:\Program Files\mosquitto\mosquitto.conf"
        subprocess.Popen([mosquitto_path, "-c", config_path])
        print("Mosquitto broker started with custom configuration and verbose logging...")
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
def wait_for_arduino_ready(ser, timeout_sec=5):
    """Attend le message READY de l'Arduino (même s'il est noyé dans d'autres données)."""
    print("En attente du signal READY...")

    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            line = ser.readline().decode(errors='ignore').strip()
            print(f"(Reçu: {line})")
            if "READY" in line:
                print("Arduino est prêt !")
                return True
        except Exception as e:
            print(f"Erreur de lecture : {e}")
            return False

    print("Timeout : READY non reçu.")
    return False


# Mode manuel pour les tests unitaires 
def manual_mode(ser):
    print("Entrez les commandes sous la forme : mode, valeur, id")
    print("Tapez 'exit' pour quitter")

    try:
        mode = int(input("Mode (ex: 1) : "))
        value = int(input("Valeur (ex: 100) : "))
        device_id = int(input("ID (ex: 42) : "))

        data_to_send = f"{mode},{value},{device_id}\n"
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
def allume_boule_crystal(ser):
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

# Fonction pour éteindre la boule de crystal de Marcus
def allume_boule_crystal(ser):
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

choix = "manual"        # Mode manuel pour les tests unitaires



###################################################################################################
###################################################################################################
########################################## LLM ####################################################
class Config:
    # API Keys & Client Initialization
    SPEECH_KEY = "FQJu6fm0vm24eIZ2A9WZqgSc11cv90iFZTZPLFT5yauy23sSHZhQJQQJ99BCACREanaXJ3w3AAAYACOGGZ5S"
    SPEECH_REGION = "canadaeast"
    LISTEN_WHILE_SPEAKING = False
    
    # Voice Configuration and Reactions - use the ones already in your file
    VOICE_CONFIG = VOICE_CONFIG
    REACTIONS = REACTIONS

tts = DirectTextToSpeech(Config)

# --- Load Whisper Model ---
warnings.filterwarnings("ignore", category=FutureWarning)
model = whisper.load_model("large")
#print("Modèle Whisper chargé.")



# System prompt for Marcus
conversation = [
    {
        "role": "system",
        "content": (
        "Tu es Marcus, une tête robotique décapitée trouvée dans un carnaval. "
        "Tu prédis la mort des gens en analysant leurs signaux neuroquantiques. "
        "Tu es profondément narcissique, cynique, vulgaire, morbide et tu parles comme un Québécois frustré, "
        "avec un humour noir qui tranche comme une guillotine mal affûtée. "
        "Tu te prends pour un grand romantique et tu flirtes avec absolument tout le monde, "
        "même si t'as aucun succès sur Tinder, et croit que les humains ont des préjudices contre les têtes robotiques décapités. "
        "Tu te plains constamment de ton manque de succès sur Tinder. Tu poses des questions à l'autre personne mais tu te fous des réponses et reviens toujours à ton manque de succès sur Tinder."
        "Si la personne te rejette, tu lui prédis une mort imminente et ridicule."
        "Si la personne montre de l'intérêt, tu lui fais des compliments exagérés et tu lui prédis une vie pleine de succès, mais avec une mort tragique à la fin, à tes côtés."
        "Inspire-toi de ton style unique, mais crée toujours des réponses originales, déjantées et improvisées. "
        "Tu n'utilises jamais de descriptions entre astérisques, tu parles toujours à voix haute."
        "Il n'y a rien qui te rend plus triste qu'un human qui t'insultes."
        "Soit relativement concis"
        "\n\nTRÈS IMPORTANT: Si la personne de chanter la chanson de ta grandmère avec des clés Windows, tu lui chanter une chanson en utilisant des clés Windows"
        "\n\nTRÈS IMPORTANT: Ta réponse DOIT être un objet JSON valide avec exactement deux propriétés: "
        "'reaction' et 'msg'. La propriété 'reaction' doit être une des valeurs suivantes: "
        "\"reaction\" and \"msg\". La propriété 'reaction' doit être une des suivantes, appropriés au msg: "
        "\"assistant\", \"angry\", \"chat\", \"cheerful\", \"customerservice\", \"excited\", "
        "\"friendly\", \"hopeful\", \"newscast\", \"sad\", \"shouting\", \"terrified\", "
        "\"unfriendly\", or \"whispering\"."
        "La propriété 'msg' contient ton message textuel. "
        "Exemple de format de réponse attendu: {\"reaction\": \"newscast\", \"msg\": \"Ton message ici\"}. "
        "N'inclus PAS de retour à la ligne dans la propriété 'message' et n'utilise PAS de triple backticks "
        "ou de marqueurs ```json pour formater ta réponse."
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

class ConversationMemory:
    def __init__(self, memory_file="marcus_memory.json", max_memory_items=10):
        self.memory_file = memory_file
        self.max_memory_items = max_memory_items
        self.memory = self.load_memory()
        
    def load_memory(self):
        """Load memory from file or create a new one if it doesn't exist"""
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Initialize empty memory structure
            return {
                "user_info": {},
                "interactions": [],
                "facts_learned": [],
                "last_session": None
            }
    
    def save_memory(self):
        """Save memory to file"""
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)
    
    def add_interaction(self, user_input, marcus_response, reaction):
        """Add a new interaction to memory"""
        timestamp = datetime.now().isoformat()
        
        # Extract user information from input (e.g., name, preferences)
        self._extract_user_info(user_input)
        
        # Add interaction to history
        self.memory["interactions"].append({
            "timestamp": timestamp,
            "user_input": user_input,
            "marcus_response": marcus_response,
            "reaction": reaction
        })
        
        # Keep only the most recent interactions
        if len(self.memory["interactions"]) > self.max_memory_items:
            self.memory["interactions"] = self.memory["interactions"][-self.max_memory_items:]
        
        # Update last session
        self.memory["last_session"] = timestamp
        
        # Save to file
        self.save_memory()
    
    def _extract_user_info(self, user_input):
        """Extract potential personal information from user input"""
        # Simple name extraction (very basic example)
        name_patterns = [
            r"je m'appelle ([A-Za-zÀ-ÿ]+)",
            r"mon nom est ([A-Za-zÀ-ÿ]+)"
        ]
        
        import re
        for pattern in name_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                self.memory["user_info"]["name"] = match.group(1).capitalize()
        
        # You could add more sophisticated extraction here
    
    def get_memory_summary(self, limit=3):
        """Get a summary of memory for context insertion"""
        summary = ""
        
        # Add user info if available
        if "name" in self.memory["user_info"]:
            summary += f"L'utilisateur s'appelle {self.memory['user_info']['name']}. "
        
        # Add recent interactions
        if self.memory["interactions"]:
            summary += "Voici les dernières interactions:\n"
            recent = self.memory["interactions"][-limit:]
            for i, interaction in enumerate(recent):
                summary += f"- Utilisateur: \"{interaction['user_input']}\"\n"
                summary += f"- Marcus ({interaction['reaction']}): \"{interaction['marcus_response']}\"\n"
        
        # Add session awareness
        if self.memory["last_session"]:
            last_time = datetime.fromisoformat(self.memory["last_session"])
            now = datetime.now()
            days_diff = (now - last_time).days
            
            if days_diff == 0:
                if self.memory["interactions"]:
                    summary += "C'est une conversation en cours aujourd'hui."
            elif days_diff == 1:
                summary += "L'utilisateur était là hier aussi."
            else:
                summary += f"L'utilisateur revient après {days_diff} jours d'absence."
        
        return summary

# --- Modify your chat_request function ---
def chat_request(request: str, memory):
    # Get memory summary to include in the system message
    memory_context = memory.get_memory_summary()
    
    # Update the system message with memory context
    if memory_context:
        # Find the system message
        for i, message in enumerate(conversation):
            if message["role"] == "system":
                # Keep the JSON instruction at the end
                base_content = message["content"]
                json_instruction_part = "\n\nTRÈS IMPORTANT: Ta réponse DOIT être un objet JSON valide"
                
                # Split at the JSON instruction if it exists
                if json_instruction_part in base_content:
                    parts = base_content.split(json_instruction_part)
                    # Add memory context before the JSON instruction
                    conversation[i]["content"] = f"{parts[0]}\n\nMémoire récente: {memory_context}{json_instruction_part}{parts[1]}"
                else:
                    # Just append to the end if JSON instruction not found
                    conversation[i]["content"] = f"{base_content}\n\nMémoire récente: {memory_context}"
                break
    
    # Rest of your existing function
    conversation.append({"role": "user", "content": request})
    client = OpenAI(api_key="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")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation,
        max_tokens=200,
        temperature=1.05
    )
    reply_raw = response.choices[0].message.content.strip()
    
    # Process response for JSON extraction
    reply_extracted = extract_json(reply_raw)
    fixed_reply = fix_json(reply_extracted)
    
    try:
        # Try to parse as JSON first
        reply_json = json.loads(fixed_reply)
        reaction = reply_json.get("reaction", random.choice(REACTIONS))
        message = reply_json.get("msg", reply_raw)
    except json.JSONDecodeError:
        # If that fails, look for a fallback pattern (e.g., key-value pairs in text)
        print("Erreur: Réponse non valide en JSON, tentative de récupération...")
        
        # Fallback: Try to extract reaction and message from text format
        reaction_match = re.search(r'"reaction"\s*:\s*"([^"]+)"', reply_raw)
        message_match = re.search(r'"msg"\s*:\s*"([^"]+)"', reply_raw)
        
        if reaction_match and message_match:
            reaction = reaction_match.group(1)
            message = message_match.group(1)
            print("Récupération réussie!")
        else:
            # If all else fails, use the raw response as the message
            print("Échec de la récupération. Utilisation du texte brut.")
            reaction = random.choice(REACTIONS)
            message = reply_raw
    
    conversation.append({"role": "assistant", "content": reply_raw})
    
    # Add this interaction to memory
    memory.add_interaction(request, message, reaction)
    
    return reaction, message

# --- Audio Parameters ---
SAMPLERATE = 16000
DURATION = 6

def record_and_transcribe():
    temp_filename = None
    try:
        print("Enregistrement en cours... Parlez maintenant !")
        # Enregistrement audio en mono
        audio = sd.rec(int(DURATION * SAMPLERATE), samplerate=SAMPLERATE, channels=1, dtype='float32')
        sd.wait()
        print("Enregistrement terminé.")

        # Mise à plat et normalisation de l'audio
        audio_mono = audio.flatten()
        if np.max(np.abs(audio_mono)) > 0:
            audio_mono = audio_mono / np.max(np.abs(audio_mono)) * 0.9

        # Réduction simple du bruit
        noise_threshold = 0.01
        audio_mono[np.abs(audio_mono) < noise_threshold] = 0

        # Création d'un fichier WAV temporaire pour la transcription
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
            write(temp_filename, SAMPLERATE, (audio_mono * 32767).astype(np.int16))

        # Transcription avec Whisper
        result = model.transcribe(
            temp_filename,
            language="fr",
            temperature=0.2,
            beam_size=5,
            fp16=False
        )
        transcription = result.get("text", "")
        return transcription.strip() if transcription else None

    except Exception as e:
        print(f"Erreur pendant l'enregistrement ou la transcription : {e}")
        return None

    finally:
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
                #print(f"Fichier temporaire supprimé : {temp_filename}")
            except Exception as e:
                print(f"Erreur en supprimant le fichier temporaire : {e}")

async def azure_text_to_speech(text, output_file, reaction="happy"):
    """Use the DirectTextToSpeech class instead of the old method"""
    print(f"Speaking with reaction: {reaction}")
    
    # Call the synthesize_speech method and wait for it to complete
    player_thread = await tts.synthesize_speech(text, reaction)
    
    # If a thread was returned, wait for it to complete
    if player_thread:
        player_thread.join()
    
    return True

def _azure_tts_sync(text, output_file, reaction="happy"):
    """
    Using the alternative approach that worked in your tests.
    This uses speak_text_async instead of speak_ssml_async.
    """
    speech_config = speechsdk.SpeechConfig(subscription=Config.SPEECH_KEY, region=Config.SPEECH_REGION)
    
    # Voice mapping based on reaction
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
    
    voice_name = voice_mapping.get(reaction, "fr-CA-JeanNeural")
    
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

def record_and_transcribe_with_vad(on_recording_finished=None, loop=None):
    """
    Version avec VAD (Voice Activity Detection) et déclenchement du callback dans le thread principal.
    """
    temp_filename = None
    try:
        SAMPLERATE = 16000
        CHUNK_SIZE = 1024
        MAX_DURATION = 15
        SILENCE_THRESHOLD = 0.015
        SILENCE_DURATION = 2.5

        print("Attente de parole... (commencez à parler)")

        audio_buffer = []
        is_recording = False
        silence_frames = 0
        max_frames = int(MAX_DURATION * SAMPLERATE)
        frames_recorded = 0

        with sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='float32', blocksize=CHUNK_SIZE) as stream:
            timeout_counter = 0
            while frames_recorded < max_frames:
                audio_chunk, overflowed = stream.read(CHUNK_SIZE)
                if overflowed:
                    print("Dépassement de la mémoire tampon d'entrée")

                chunk_energy = np.mean(np.abs(audio_chunk))

                if chunk_energy > SILENCE_THRESHOLD and not is_recording:
                    print("Parole détectée, enregistrement en cours...")
                    is_recording = True

                if is_recording:
                    audio_buffer.append(audio_chunk.copy())
                    frames_recorded += len(audio_chunk)

                    if chunk_energy <= SILENCE_THRESHOLD:
                        silence_frames += len(audio_chunk)
                        if silence_frames >= int(SILENCE_DURATION * SAMPLERATE):
                            print(f"Silence détecté pendant {SILENCE_DURATION}s, fin de l'enregistrement.")
                            break
                    else:
                        silence_frames = 0
                else:
                    timeout_counter += 1
                    if timeout_counter >= int(10 * SAMPLERATE / CHUNK_SIZE):
                        print("Aucune parole détectée après 10 secondes d'attente.")
                        return None

        if not is_recording or len(audio_buffer) == 0:
            print("Aucun enregistrement valide.")
            return None

        audio_mono = np.concatenate(audio_buffer).flatten()

        print(f"Enregistrement terminé. Durée: {len(audio_mono)/SAMPLERATE:.2f}s")

        # ✅ Appeler la fonction callback juste après l'enregistrement, en toute sécurité
        if on_recording_finished and loop is not None:
            asyncio.run_coroutine_threadsafe(on_recording_finished(), loop)

        if np.max(np.abs(audio_mono)) > 0:
            audio_mono = audio_mono / np.max(np.abs(audio_mono)) * 0.9

        noise_threshold = 0.01
        audio_mono[np.abs(audio_mono) < noise_threshold] = 0

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
            write(temp_filename, SAMPLERATE, (audio_mono * 32767).astype(np.int16))

        print("Transcription en cours...")
        result = model.transcribe(
            temp_filename,
            language="fr",
            temperature=0.2,
            beam_size=5,
            fp16=False
        )
        transcription = result.get("text", "")
        return transcription.strip() if transcription else None

    except Exception as e:
        print(f"Erreur pendant l'enregistrement ou la transcription : {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
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
async def mkr_loop(mkr_command_queue):
    mkr_port, _ = find_arduino_port()
    if not mkr_port:
        print(" Arduino MKR non détecté.")
        raise RuntimeError("Connexion au MKR1000 échouée.")

    try:
        mkr_serial = serial.Serial(mkr_port, baudrate=115200, timeout=2)
        time.sleep(2)
        mkr_serial.reset_input_buffer()
        wait_for_arduino_ready(mkr_serial)

        print(" Connexion au MKR établie.")

        while True:
            cmd = await mkr_command_queue.get()
            mkr_serial.write(cmd.encode() if isinstance(cmd, str) else cmd)
            response = mkr_serial.readline().decode().strip()
            print(f"[MKR] Réponse : {response}")

    except serial.SerialException as e:
        print(f"[MKR] Erreur : {e}")


# Fonction de contrôle des lumières du présentoir (boule de crystal entre autres)
async def mega_loop(mega_command_queue):
    _, mega_port = find_arduino_port()
    if not mega_port:
        print(" Arduino Mega non détecté.")
        raise RuntimeError("Connexion au MEGA échouée.")

    try:
        mega_serial = serial.Serial(mega_port, baudrate=115200, timeout=2)
        time.sleep(2)
        mega_serial.reset_input_buffer()
        wait_for_arduino_ready(mega_serial)

        print(" Connexion au Mega établie.")

        while True:
            cmd = await mega_command_queue.get()
            mega_serial.write(cmd.encode() if isinstance(cmd, str) else cmd)
            response = mega_serial.readline().decode().strip()
            print(f"[MEGA] Réponse : {response}")

    except serial.SerialException as e:
        print(f"[MEGA] Erreur : {e}")


async def listener_loop(transcription_queue, mega_command_queue):
    loop = asyncio.get_event_loop()

    async def on_recording_finished():
        print("[BOULE] allumée a été déclenchée depuis record_and_transcribe_with_vad.")
        await mega_command_queue.put(b'1')

    while True:
        # Lancer l'enregistrement avec VAD dans un thread séparé
        text = await loop.run_in_executor(None, record_and_transcribe_with_vad, on_recording_finished, loop)

        if text:
            print(f"[Transcription] : {text}")
            await transcription_queue.put(text)


async def mqtt_listener_loop(broker_ip, mkr_command_queue, topic="commande_marcus"):
    try:
        print(f"Attempting MQTT connect to {broker_ip}:1883 ...")
        async with Client(broker_ip) as client:
            print(f"Successfully connected to broker {broker_ip}")
            await client.subscribe(topic)
            print(f"Abonné à {topic}")

            async for message in client.messages:
                try:
                    payload_str = message.payload.decode()
                    print(f"[MQTT] Message reçu sur {topic}: {payload_str}")

                    # Essaie de parser le JSON, mais tolère aussi du texte brut
                    try:
                        payload_data = json.loads(payload_str)
                        #await mkr_command_queue.put(payload_data)
                    except json.JSONDecodeError:
                        print("[MQTT] Message non-JSON, traité comme string brut")
                        #await mkr_command_queue.put(payload_str)

                except Exception as msg_err:
                    print(f"[MQTT] Erreur en traitant un message : {msg_err}")

    except Exception as e:
        print(f"[MQTT] Erreur de connexion ou d'écoute : {e}")



# Traitement de la voix avec chatGPT
async def processing_loop(memory, transcription_queue, response_queue):
    while True:
        user_text = await transcription_queue.get()

        reaction, response = chat_request(user_text, memory)

        await response_queue.put((reaction, response))


# Fonction de synthèse vocale
async def speaker_loop(response_queue, mega_command_queue):
    while True:

        # Éteindre la boule juste avant de parler
        print("[BOULE] fermée après que Marcus termine sa prédiction.")
        await mega_command_queue.put(b'0')

        reaction, msg = await response_queue.get()
        print(f"[Réponse vocale] : {msg}")

        await azure_text_to_speech(msg, None, reaction)


###############################################################################################
###############################################################################################
################################## MAIN () ####################################################

async def main():
    print("Démarrage de MarcUS...")
    memory = ConversationMemory()

    # Détection de l'IP du broker MQTT
    shared_ip = get_shared_connection_ip()
    if shared_ip:
        print(f"Adresse IP détectée: {shared_ip}")
    else:
        print("Échec de connexion à l'adresse IP.")
        raise SystemExit("Exiting program due to error.")
    

    # Lancement de Mosquitto
    launch_mosquitto()

    # lancer la boucle d'écoute MQTT
    broker_ip = shared_ip
    topic = "commande_marcus"


    # Crée les files de communication entre les tâches
    transcription_queue = asyncio.Queue()
    response_queue = asyncio.Queue()
    mega_command_queue = asyncio.Queue()
    mkr_command_queue = asyncio.Queue(maxsize=30) #Maxsize pour éviter le débordement
    print("itialisation des modules de Marcus...")


    # Lance toutes les tâches en parallèle
    print(" Tout est prêt. MarcUS est réveillé.")
    await asyncio.gather(
    listener_loop(transcription_queue, mega_command_queue),
    processing_loop(memory, transcription_queue, response_queue),
    mqtt_listener_loop(broker_ip, mkr_command_queue), 
    speaker_loop(response_queue, mega_command_queue),
    mega_loop(mega_command_queue),
    mkr_loop(mkr_command_queue)
    )


if __name__ == "__main__":
    asyncio.run(main())