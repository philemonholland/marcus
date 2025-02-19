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

# Clé API OpenAI
openai.api_key = "J'ai enlevé la clé API pour des raisons de sécurité..."

# Charger le modèle Whisper
model = whisper.load_model("base")
print("Modèle Whisper chargé.")

# Personnalité de l'assistant
conversation = [
    {"role": "system", "content": "Tu es MarcUS, un assistant IA amical et plein d'humour qui aide les utilisateurs avec leurs questions."}
]

def chat_request(request: str):
    conversation.append({"role": "user", "content": request})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation,
        max_tokens=100
    )
    reply = response.choices[0].message.content
    conversation.append({"role": "assistant", "content": reply})
    return reply

# Paramètres audio
SAMPLERATE = 16000
DURATION = 6

def record_and_transcribe():
    temp_filename = None
    try:
        print("Enregistrement en cours... Parlez maintenant !")
        audio = sd.rec(int(DURATION * SAMPLERATE), samplerate=SAMPLERATE, channels=4, dtype='float32')
        sd.wait()
        print("Enregistrement terminé.")

        # Création d'un fichier temporaire pour enregistrer l'audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
            write(temp_filename, SAMPLERATE, (audio * 32767).astype(np.int16))

        # Transcription avec Whisper
        result = model.transcribe(temp_filename, language="French")
        transcription = result["text"]

        return transcription.strip() if transcription else None

    except Exception as e:
        print(f"Erreur pendant l'enregistrement ou la transcription : {e}")
        return None

    finally:
        # Supprimer le fichier temporaire .wav
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
                print(f"Fichier temporaire supprimé : {temp_filename}")
            except Exception as e:
                print(f"Erreur en supprimant le fichier temporaire : {e}")


async def main():
    print("Appuyez sur Ctrl+C pour quitter.")
    try:
        while True:
            transcription = record_and_transcribe()
            if transcription:
                print(f"Vous avez dit : {transcription}")
                chat_response = chat_request(transcription)
                if chat_response:
                    print(f"MarcUS : {chat_response}")

                    # Synthèse vocale
                    try:
                        # 1) Générer un nom de fichier unique (timestamp)
                        #    pour éviter de réutiliser "output.mp3" qui peut rester verrouillé.
                        unique_name = f"output_{time.time_ns()}.mp3"

                        # 2) Générer le fichier MP3
                        communicate = edge_tts.Communicate(chat_response, voice="fr-CA-AntoineNeural")
                        await communicate.save(unique_name)

                        # 3) Lecture
                        playsound(unique_name)

                        # 4) (Facultatif) Ajouter une petite pause pour laisser MCI libérer le fichier
                        #    time.sleep(0.5)

                    except Exception as e:
                        print(f"Erreur pendant la synthèse vocale ou la lecture : {e}")

                    finally:
                        # 5) Supprimer le fichier MP3
                        if os.path.exists(unique_name):
                            try:
                                os.remove(unique_name)
                                print(f"Fichier MP3 supprimé : {unique_name}")
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
