import whisper
import openai
import sounddevice as sd
import numpy as np
import tempfile
import os
from scipy.io.wavfile import write
import asyncio
import edge_tts
from playsound import playsound
import time
import json
import paho.mqtt.client as mqtt

# 1. RÉSOLUTION DU PROBLÈME FFMPEG
# Définir le chemin vers ffmpeg si nécessaire (décommentez et configurez si nécessaire)
# Téléchargez ffmpeg depuis https://ffmpeg.org/download.html et indiquez le chemin
# import whisper.audio
# whisper.audio.SAMPLE_RATE = 16000
# whisper.audio.N_FFT = 400
# whisper.audio.HOP_LENGTH = 160
# whisper.audio.CHUNK_LENGTH = 30
# whisper.audio.N_SAMPLES = whisper.audio.CHUNK_LENGTH * whisper.audio.SAMPLE_RATE  # 480000 samples
# whisper.audio.N_FRAMES = whisper.audio.N_SAMPLES // whisper.audio.HOP_LENGTH  # 3000 frames
# whisper.audio.FFMPEG_PATH = r"C:\chemin\vers\ffmpeg.exe"  # MODIFIER AVEC VOTRE CHEMIN

# Clé API OpenAI et modèle Whisper
openai.api_key = ""  # Insérez votre clé ici
model = whisper.load_model("base")
print("Modèle Whisper chargé.")

# 2. FONCTION POUR TESTER TOUS LES MICROPHONES
def test_microphones():
    print("Test de tous les microphones disponibles...")
    devices = sd.query_devices()
    mic_indices = []

    # Trouver tous les périphériques d'entrée
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            print(f"Index {i}: {dev['name']} - {dev['max_input_channels']} canaux d'entrée")
            mic_indices.append(i)

    best_mic = None
    best_level = -1

    # Tester chaque microphone
    for idx in mic_indices:
        try:
            dev_info = sd.query_devices(idx)
            num_channels = min(dev_info['max_input_channels'], 2)
            
            print(f"\nTest du microphone {idx}: {dev_info['name']} avec {num_channels} canaux")
            print("Parlez maintenant pendant 2 secondes...")
            
            # Enregistrement
            audio = sd.rec(int(2 * 16000), samplerate=16000, 
                          channels=num_channels, dtype='float32', device=idx)
            sd.wait()
            
            # Vérification du niveau audio
            audio_level = np.abs(audio).mean()
            print(f"Niveau audio moyen: {audio_level:.6f}")
            
            # Garder le meilleur
            if audio_level > best_level:
                best_level = audio_level
                best_mic = idx
                
        except Exception as e:
            print(f"Erreur avec le périphérique {idx}: {e}")
            
    if best_mic is not None:
        print(f"\nMeilleur microphone détecté: Index {best_mic} avec niveau {best_level:.6f}")
        return best_mic
    else:
        print("Aucun microphone fonctionnel trouvé.")
        return None

# 3. FONCTION D'ENREGISTREMENT AMÉLIORÉE AVEC FALLBACK
def record_and_transcribe(duration=6, device_index=None):
    # Si aucun périphérique n'est spécifié, utiliser celui par défaut
    if device_index is None:
        device_index = sd.default.device[0]  # Utiliser l'entrée par défaut
    
    # Variables pour stocker le fichier temporaire
    temp_wav = None
    temp_np = None
    
    try:
        print(f"Enregistrement en cours sur le périphérique {device_index}... Parlez maintenant !")
        
        # Obtenir les infos du périphérique pour connaître le nombre de canaux
        device_info = sd.query_devices(device_index)
        channels = min(device_info['max_input_channels'], 2)  # Limiter à 2 canaux
        
        # Enregistrement
        audio = sd.rec(int(duration * 16000), samplerate=16000, 
                      channels=channels, dtype='float32', device=device_index)
        
        # Feedback visuel
        for i in range(duration):
            print(f"Enregistrement en cours... {i+1}/{duration} secondes", end='\r')
            time.sleep(1)
        print()
        
        sd.wait()
        print("Enregistrement terminé.")
        
        # Vérification du niveau audio
        audio_level = np.abs(audio).mean()
        print(f"Niveau audio détecté: {audio_level:.6f}")
        
        if audio_level < 0.001:  # Seuil très bas
            print("⚠️ Le niveau audio est trop bas. Vérifiez votre microphone.")
        
        # 4. MÉTHODE DIRECTE SANS UTILISER FFMPEG
        # Convertir l'audio en mono si nécessaire et le stocker en mémoire
        if channels > 1:
            audio_mono = audio.mean(axis=1)
        else:
            audio_mono = audio.flatten()
            
        # Normaliser l'audio pour augmenter le niveau si c'est trop bas
        if audio_level > 0 and audio_level < 0.01:
            gain = min(0.01 / audio_level, 10)  # Limiter le gain maximum
            audio_mono = audio_mono * gain
            print(f"Audio normalisé avec gain: {gain:.2f}")
            
        # Stocker les données numpy pour whisper
        temp_np = audio_mono
            
        # Sauvegarder également en .wav pour fallback si nécessaire
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_wav = temp_file.name
            write(temp_wav, 16000, (audio_mono * 32767).astype(np.int16))
        
        # 5. RÉSOLUTION PROBLÈME WHISPER
        # Essayer d'abord d'utiliser directement les données numpy (meilleure solution)
        try:
            # Utiliser directement l'array numpy avec Whisper
            result = model.transcribe(temp_np, language="French")
            transcription = result["text"]
            print("Transcription réussie avec méthode directe.")
        except Exception as e:
            print(f"Erreur avec la méthode directe: {e}")
            
            try:
                # Fallback: essayer avec le fichier temporaire
                result = model.transcribe(temp_wav, language="French")
                transcription = result["text"]
                print("Transcription réussie avec fichier temporaire.")
            except Exception as e2:
                print(f"Erreur avec fichier temporaire: {e2}")
                
                # Solution de secours ultime: retourner un texte vide
                print("⚠️ Échec de la transcription. Vérifiez l'installation de ffmpeg.")
                return None
        
        return transcription.strip() if transcription else None
        
    except Exception as e:
        print(f"Erreur pendant l'enregistrement: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        # Nettoyage du fichier temporaire
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
                print(f"Fichier temporaire supprimé: {temp_wav}")
            except Exception as e:
                print(f"Erreur en supprimant le fichier: {e}")

# 6. FONCTION PRINCIPALE MODIFIÉE
async def main():
    print("Initialisation de l'assistant vocal...")
    
    # Détecter automatiquement le meilleur microphone
    best_mic = test_microphones()
    
    if best_mic is None:
        print("Aucun microphone détecté. Utilisation du périphérique par défaut.")
    else:
        print(f"Utilisation du microphone {best_mic}.")
    
    print("Appuyez sur Ctrl+C pour quitter.")
    try:
        while True:
            # Utiliser le microphone détecté ou celui par défaut
            transcription = record_and_transcribe(device_index=best_mic)
            
            if transcription:
                print(f"Vous avez dit: {transcription}")
                reaction, message = chat_request(transcription)
                if message:
                    print(f"MarcUS: {message}")

                    # Réaction de l'assistant
                    print(f"Réaction: {reaction}")

                    # Synthèse vocale
                    try:
                        unique_name = f"output_{time.time_ns()}.mp3"
                        communicate = edge_tts.Communicate(message, voice="fr-CA-AntoineNeural")
                        await communicate.save(unique_name)
                        playsound(unique_name)
                    except Exception as e:
                        print(f"Erreur synthèse vocale: {e}")
                    finally:
                        if os.path.exists(unique_name):
                            try:
                                os.remove(unique_name)
                            except Exception as e:
                                print(f"Erreur suppression MP3: {e}")
                else:
                    print("Aucune réponse générée.")
            else:
                print("Aucune transcription générée.")
            print("-" * 50)

    except KeyboardInterrupt:
        print("\nProgramme terminé.")
    except Exception as e:
        print(f"Erreur inattendue: {e}")

if __name__ == "__main__":
    asyncio.run(main())