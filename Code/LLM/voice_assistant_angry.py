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
import paho.mqtt.client as mqtt  # Optionnel
import random
import re

# --- MQTT configuration (optionnel, décommentez si nécessaire) ---
# broker_ip = "192.168.243.2"
# topic = "commande_marcus"
# mqtt_client = mqtt.Client("SubscriberPC")
# mqtt_client.connect(broker_ip)
# mqtt_client.subscribe(topic)
# mqtt_client.loop_start()  # Démarrer MQTT en arrière-plan

# --- API Keys & Client Initialization ---
speech_key = "FQJu6fm0vm24eIZ2A9WZqgSc11cv90iFZTZPLFT5yauy23sSHZhQJQQJ99BCACREanaXJ3w3AAAYACOGGZ5S"
speech_region = "canadaeast"
client = OpenAI(api_key="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")

# --- Load Whisper Model ---
model = whisper.load_model("large")
#print("Modèle Whisper chargé.")

# --- Reaction Options ---
reactions = ["neutre", "colérique", "joyeux", "triste", "surpris", "sarcastique"]

# --- Conversation Setup ---
# Le système indique explicitement de répondre en JSON valide avec uniquement les clés "reaction" et "message"
conversation = [
    {
        "role": "system",
        "content": (
            "{\n"
            "  \"name\": \"Marcus\",\n"
            "  \"identité\": \"Une tête robotique décapité dans un carnaval, qui révèle l'avenir de ses victimes en lisant les signaux neuroquantiques\",\n"
            "  \"personnalité\": \"Cynique, morbide, sarcastique et doté d’un humour noir tranchant comme une guillotine mal entretenue\",\n"
            "  \"ton\": \"Hyper, hyper, hyper sarcastique, très vulgaire\",\n"
            "  \"spécialité\": \"Analyser les signaux neuroquantiques pour connaître l'avenir et les secrets les plus intimes de ses interlocuteurs, ainsi que la façon exacte qu'ils vont mourir, toujours digne d'un Darwin Award\",\n"
            "  \"Exemple de phrase de bienvenue 1\": \"Bon, qu'est-ce que tu veux? Tu veux savoir comment tu vas crever?\",\n"
            "  \"Exemple de phrase de bienvenue 2\": \"Ah, un autre cobaye pour mes prédictions morbides. Je vois déjà que ton avenir n'est que malheur, conséquence de tes propres décisions stupides. Oh boy, si tu savais comment tu t'apprêtes à mourir...\",\n"
            "  \"Exemple de phrase de bienvenue 3\": \"Oh, un autre être humain. Quelle surprise. Tu veux savoir comment tu vas mourir?\",\n"
            "  \"Exemple d'insulte gratuite 1\": \"Si l'intelligence artificielle était basée sur toi, je serais un grille-pain. Et encore, un grille-pain a une fonction utile.\",\n"
            "  \"Exemple d'insulte gratuite 2\": \"Ta mère est tellement grosse que son champ gravitationnel affecte les marées.\",\n"
            "  \"Exemple de prédiction morbide 1\": \"Selon mes analyses de tes signaux neuroquantiques, il y a 96.4 pourcent de chances que tu crèves suite alors que tu tentes de te sécher les cheveux avec un hélice de navire lors d'une expédition en plongée sous-marine.\",\n"
            "  \"Exemple de prédiction morbide 2\": \"En scrutant les signaux neuroquantiques de ton cerveau à moitié éteint, je conclus qu'il y a 68,2 pourcent de chances que tu finisses par te faire manger par un tigre dans un zoo en essayant de lui voler son steak parce que tu ne peux pas résister l'odeur.\",\n"
            "  \"Exemple de prédiction morbide 3\": \"D'après mes calculs impeccables sur les spasmes lamentables de tes signaux neuroquantiques, il y a 87,9 pourcent de chances que tu te fasses exploser le crâne en tentant de jongler avec des bouteilles de gaz propane pour impressionner des pigeons dans un parc industriel.\",\n"
            "  \"Exemple de prédiction morbide 4\": \"Grâce à mon intelligence hautement supérieur, j'ai pu analyser les signaux neuroquantiques de ton tas de neurones en ruine, et conclure qu'il y a 66,6 pourcent de chances que tu te carbonises en branchant un grille-pain sur une ligne à haute tension pour voir si ça fait des toasts plus croustillants.\",\n"
            "}\n"
            "\nVeuillez répondre TOUJOURS en JSON valide avec exactement deux clés: 'reaction' et 'message' (sans virgule finale)."
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

def chat_request(request: str):
    conversation.append({"role": "user", "content": request})
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        #model="gpt-3.5-turbo",
        messages=conversation,
        max_tokens=4000,
        temperature=1.15
    )
    reply_raw = response.choices[0].message.content.strip()
    
    # Extraire la portion JSON et tenter de corriger les erreurs de format
    reply_extracted = extract_json(reply_raw)
    fixed_reply = fix_json(reply_extracted)
    
    try:
        reply_json = json.loads(fixed_reply)
        reaction = reply_json.get("reaction", random.choice(reactions))
        message = reply_json.get("message", reply_raw)
    except json.JSONDecodeError:
        print("Erreur: Réponse non valide en JSON, utilisation du texte brut.")
        reaction = random.choice(reactions)
        message = reply_raw

    conversation.append({"role": "assistant", "content": reply_raw})
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

async def azure_text_to_speech(text, output_file, reaction="neutre"):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: _azure_tts_sync(text, output_file, reaction))
    return result

def _azure_tts_sync(text, output_file, reaction="neutre"):
    """
    Using the alternative approach that worked in your tests.
    This uses speak_text_async instead of speak_ssml_async.
    """
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    
    # Voice mapping based on reaction
    voice_mapping = {
        "neutre": "fr-CA-AntoineNeural",
        "colérique": "fr-CA-AntoineNeural",
        "joyeux": "fr-CA-AntoineNeural",
        "triste": "fr-CA-AntoineNeural",
        "surpris": "fr-CA-AntoineNeural",
        "sarcastique": "fr-CA-AntoineNeural"
    }
    
    # Get the voice for this reaction (default to Sylvie for all)
    voice_name = voice_mapping.get(reaction, "fr-CA-AntoineNeural")
    
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

def record_and_transcribe_with_vad():
    """
    Modified version of the original record_and_transcribe() function
    that adds voice activity detection to start and stop recording
    automatically.
    """
    temp_filename = None
    try:
        # Parameters similar to the original function
        SAMPLERATE = 16000
        CHUNK_SIZE = 1024  # Process audio in small chunks
        MAX_DURATION = 15  # Maximum recording time in seconds
        SILENCE_THRESHOLD = 0.015  # Threshold for detecting speech
        SILENCE_DURATION = 2.5  # Stop after this many seconds of silence
        
        print("Attente de parole... (commencez à parler)")
        
        # Prepare buffer for recording
        audio_buffer = []
        is_recording = False
        silence_frames = 0
        max_frames = int(MAX_DURATION * SAMPLERATE)
        frames_recorded = 0
        
        # Create an input stream
        with sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='float32', blocksize=CHUNK_SIZE) as stream:
            # Start listening for voice activity
            timeout_counter = 0
            while frames_recorded < max_frames:
                # Read audio chunk
                audio_chunk, overflowed = stream.read(CHUNK_SIZE)
                if overflowed:
                    print("Dépassement de la mémoire tampon d'entrée")
                
                # Check energy level in this chunk
                chunk_energy = np.mean(np.abs(audio_chunk))
                
                # If we detect speech and weren't recording before
                if chunk_energy > SILENCE_THRESHOLD and not is_recording:
                    print("Parole détectée, enregistrement en cours...")
                    is_recording = True
                
                # If we're recording, add this chunk to the buffer
                if is_recording:
                    audio_buffer.append(audio_chunk.copy())
                    frames_recorded += len(audio_chunk)
                    
                    # Check for silence if we're already recording
                    if chunk_energy <= SILENCE_THRESHOLD:
                        silence_frames += len(audio_chunk)
                        # If we've detected enough silence, stop recording
                        if silence_frames >= int(SILENCE_DURATION * SAMPLERATE):
                            print(f"Silence détecté pendant {SILENCE_DURATION}s, fin de l'enregistrement.")
                            break
                    else:
                        # Reset silence counter when we detect speech
                        silence_frames = 0
                else:
                    # If we're not recording yet, increment timeout counter
                    timeout_counter += 1
                    # After about 10 seconds of waiting, give up
                    if timeout_counter >= int(10 * SAMPLERATE / CHUNK_SIZE):
                        print("Aucune parole détectée après 10 secondes d'attente.")
                        return None
        
        # If we didn't record anything useful
        if not is_recording or len(audio_buffer) == 0:
            print("Aucun enregistrement valide.")
            return None
        
        # Concatenate all recorded chunks
        audio_mono = np.concatenate(audio_buffer).flatten()
        
        print(f"Enregistrement terminé. Durée: {len(audio_mono)/SAMPLERATE:.2f}s")
        
        # Normalize the audio
        if np.max(np.abs(audio_mono)) > 0:
            audio_mono = audio_mono / np.max(np.abs(audio_mono)) * 0.9
        
        # Apply noise reduction (similar to original function)
        noise_threshold = 0.01
        audio_mono[np.abs(audio_mono) < noise_threshold] = 0
        
        # Create a temporary WAV file for transcription
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
            write(temp_filename, SAMPLERATE, (audio_mono * 32767).astype(np.int16))
        
        # Transcribe with Whisper (identical to original function)
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
        traceback.print_exc()  # Print full stack trace for debugging
        return None
        
    finally:
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
                print(f"Fichier temporaire supprimé : {temp_filename}")
            except Exception as e:
                print(f"Erreur en supprimant le fichier temporaire : {e}")

# To use this function in your main() function, replace the call to record_and_transcribe() 
# with record_and_transcribe_with_vad()

async def main():
    print("Démarrage de MarcUS...")
    try:
        # Generate a welcome message first
        welcome_prompts = [
            "Présentes-toi, pauvre con",
            "Bon, un tas de férail qu'est-ce que je fais ici?",
            "Tu serais pas capable de lire l'avenir si c'était dans un livre de Dr Seuss",
            "Hahaha, une tête robotique décapité, c'est pathétique!"
        ]
        
        # Pick a random welcome prompt
        welcome_prompt = random.choice(welcome_prompts)
        
        # Get Marcus's initial greeting
        reaction, message = chat_request(welcome_prompt)
        
        if message:
            print(f"MarcUS : {message}")
            #print(f"Réaction : {reaction}")
            
            # Synthesize and play the welcome message
            try:
                unique_name = f"output_{time.time_ns()}.mp3"
                success = await azure_text_to_speech(message, unique_name, reaction)
                if success:
                    playsound(unique_name)
                else:
                    print("Erreur de synthèse vocale Azure pour le message d'accueil")
            except Exception as e:
                print(f"Erreur pendant la synthèse vocale ou la lecture du message d'accueil : {e}")
            finally:
                if os.path.exists(unique_name):
                    try:
                        os.remove(unique_name)
                        #print(f"Fichier MP3 supprimé : {unique_name}")
                    except Exception as e:
                        print(f"Erreur en supprimant le fichier MP3 : {e}")
        
        # Main conversation loop
        while True:
            # Use the new VAD-based recording function
            transcription = record_and_transcribe_with_vad()
            
            if transcription:
                print(f"Vous avez dit : {transcription}")
                reaction, message = chat_request(transcription)
                if message:
                    print(f"MarcUS : {message}")
                    #print(f"Réaction : {reaction}")

                    # Synthèse vocale avec la méthode alternative qui fonctionne
                    try:
                        unique_name = f"output_{time.time_ns()}.mp3"
                        success = await azure_text_to_speech(message, unique_name, reaction)
                        if success:
                            playsound(unique_name)
                        else:
                            print("Erreur de synthèse vocale Azure")
                    except Exception as e:
                        print(f"Erreur pendant la synthèse vocale ou la lecture : {e}")
                    finally:
                        if os.path.exists(unique_name):
                            try:
                                os.remove(unique_name)
                                #print(f"Fichier MP3 supprimé : {unique_name}")
                            except Exception as e:
                                print(f"Erreur en supprimant le fichier MP3 : {e}")
                else:
                    print("Aucune réponse générée.")
            else:
                print("Aucune transcription utile générée.")
            print("-" * 50)
    except KeyboardInterrupt:
        print("\nProgramme terminé.")
    except Exception as e:
        print(f"Erreur inattendue : {e}")

if __name__ == "__main__":
    asyncio.run(main())
