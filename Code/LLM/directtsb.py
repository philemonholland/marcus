# Module pour gérer tout ce qui est lié à la synthèse vocale avec Azure.
# Ce module utilise la bibliothèque azure.cognitiveservices.speech pour la synthèse vocale.
import azure.cognitiveservices.speech as speechsdk
import asyncio
import tempfile
import os
import threading
import time
import platform
import traceback
if platform.system() == 'Windows':
    import winsound

# --- Direct Text-to-Speech ---
class DirectTextToSpeech:
    def __init__(self, config, recorder=None):
        self.config = config
        self.current_audio_file = None
        self.is_speaking = False
        self.speech_canceled = False
        self.recorder = recorder  # Reference to the AudioRecorder for muting
        
        try:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=config.SPEECH_KEY, 
                region=config.SPEECH_REGION
            )
            print("Azure Speech SDK initialized")
        except Exception as e:
            print(f"Error initializing Azure Speech SDK: {e}")
            traceback.print_exc()
            self.speech_config = None
    
    def _format_ssml(self, text, emotion):
        """Format text with SSML for natural speech with emotional styling"""
        voice_config = self.config.VOICE_CONFIG.get(emotion, self.config.VOICE_CONFIG["angry"])
        voice_name = voice_config["voice"]
        style = voice_config["style"]
        rate = voice_config["rate"]
        pitch = voice_config["pitch"]
        
        print(f"Using voice config for {emotion}: {voice_name}, style={style}, rate={rate}, pitch={pitch}")
        
        """Format text with SSML for natural speech with emotional styling"""
        voice_config = self.config.VOICE_CONFIG.get(emotion, self.config.VOICE_CONFIG["angry"])
        voice_name = voice_config["voice"]
        style = voice_config["style"]
        styledegree = voice_config["styledegree"]
        rate = voice_config["rate"]
        pitch = voice_config["pitch"]

        
        # Add pauses at punctuation marks
        enhanced_text = text
        enhanced_text = enhanced_text.replace('. ', '. <break time="300ms"/> ')
        enhanced_text = enhanced_text.replace('! ', '! <break time="400ms"/> ')
        enhanced_text = enhanced_text.replace('? ', '? <break time="350ms"/> ')
        enhanced_text = enhanced_text.replace(', ', ', <break time="200ms"/> ')
        
        # Create SSML
        ssml = (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="fr-CA">'
            f'<voice name="{voice_name}">'
            f'<mstts:express-as style="{style}" styledegree="{styledegree}">'
            f'<prosody rate="{rate}" pitch="{pitch}">'
            f'{enhanced_text}'
            f'</prosody>'
            f'</mstts:express-as>'
            f'</voice>'
            f'</speak>'
        )
        
        return ssml
    
    async def synthesize_speech(self, text, emotion="terrified"):
        # Reset flags
        self.is_speaking = True
        self.speech_canceled = False
        
        # Mute the microphone unless listen-while-speaking is enabled
        if self.recorder and not self.config.LISTEN_WHILE_SPEAKING:
            self.recorder.mute_microphone()
        
        # For testing without Azure
        if os.environ.get("MARCUS_DEBUG") == "1" or self.speech_config is None:
            print(f"DEBUG MODE: Speech would say: '{text}'")
            await asyncio.sleep(1)  # Simulate delay
            self.is_speaking = False
            
            # Unmute microphone after speaking
            if self.recorder and not self.config.LISTEN_WHILE_SPEAKING:
                self.recorder.unmute_microphone()
            return
        
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            output_file = temp_file.name
            self.current_audio_file = output_file
        
        # Configure the synthesizer for direct output to WAV
        if emotion == "posessed" or "not impressed":
            emotion = "neutral"
        self.speech_config.speech_synthesis_voice_name = self.config.VOICE_CONFIG[emotion]["voice"]
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )
        
        # Set up audio config
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
        
        # Create the synthesizer and save reference for cancellation
        self.synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        # Get the SSML 
        ssml = self._format_ssml(text, emotion)
        
        print("Synthesizing speech...")
        
        # Use synchronous synthesis to avoid async issues
        result = self.synthesizer.speak_ssml(ssml)
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # Check if synthesis was canceled midway
            if self.speech_canceled:
                print("Speech synthesis was canceled")
                if os.path.exists(output_file):
                    os.remove(output_file)
                self.is_speaking = False
                
                # Unmute microphone if necessary
                if self.recorder and not self.config.LISTEN_WHILE_SPEAKING:
                    self.recorder.unmute_microphone()
                return
            
            # Define play function with better cleanup
            def play_audio_native():
                try:
                    # Set a flag that this thread is running
                    current_thread = threading.current_thread()
                    current_thread._running = True
                    current_thread._audio_file = output_file
                    
                    # Check if we're on Windows
                    if platform.system() == 'Windows':
                        try:
                            # Use winsound for Windows (built-in)
                            winsound.PlaySound(output_file, winsound.SND_FILENAME)
                        except Exception as e:
                            print(f"Windows playback error: {e}")
                    else:
                        try:
                            # For other platforms, use playsound
                            from playsound import playsound
                            playsound(output_file)
                        except ImportError:
                            # Fallback if playsound is not available
                            print("Warning: playsound not available, trying alternate playback")
                            try:
                                import subprocess
                                if platform.system() == 'Darwin':  # macOS
                                    subprocess.call(['afplay', output_file])
                                else:  # Linux
                                    subprocess.call(['aplay', '-q', output_file])
                            except Exception as e:
                                print(f"Alternate playback failed: {e}")
                except Exception as e:
                    print(f"Error playing audio: {e}")
                    traceback.print_exc()
                finally:
                    # Mark that we're no longer speaking
                    self.is_speaking = False
                    
                    # Unmute microphone if necessary
                    if self.recorder and not self.config.LISTEN_WHILE_SPEAKING:
                        self.recorder.unmute_microphone()
                    
                    # Clean up the audio file
                    try:
                        if os.path.exists(output_file):
                            os.remove(output_file)
                            print(f"Removed temporary audio file: {output_file}")
                        else:
                            print(f"Audio file already removed: {output_file}")
                    except Exception as e:
                        print(f"Could not remove audio file: {e}")
                    
                    # Clear the reference to the current audio file
                    self.current_audio_file = None
                    
                    # For debugging
                    print("Audio playback complete")
            
            # Use a thread for playing to avoid blocking
            print(f"Starting audio playback thread for file: {output_file}")
            self.player_thread = threading.Thread(target=play_audio_native)
            self.player_thread.daemon = True
            self.player_thread.start()
            
            # Return the thread so the caller can track it
            return self.player_thread
        else:
            print(f"Speech synthesis failed: {result.reason}")
            self.is_speaking = False
            
            # Unmute microphone if necessary
            if self.recorder and not self.config.LISTEN_WHILE_SPEAKING:
                self.recorder.unmute_microphone()
            
            # Clean up
            if os.path.exists(output_file):
                os.remove(output_file)
                
    def stop_speaking(self):
        """Cancel the current speech synthesis"""
        if self.is_speaking:
            self.speech_canceled = True
            
            # Try to cancel the synthesizer if it exists
            if hasattr(self, 'synthesizer'):
                try:
                    self.synthesizer.stop_speaking()
                except Exception as e:
                    print(f"Error stopping speech: {e}")
            
            # Try to stop audio playback if there's a file
            if self.current_audio_file and os.path.exists(self.current_audio_file):
                try:
                    # Stop and close any players
                    if platform.system() == 'Windows':
                        winsound.PlaySound(None, winsound.SND_PURGE)
                    
                    # Attempt to remove the file
                    os.remove(self.current_audio_file)
                except Exception as e:
                    print(f"Error cleaning up audio file: {e}")
            
            # Reset speaking flags
            self.is_speaking = False
            
            # Unmute microphone if needed
            if self.recorder and not self.config.LISTEN_WHILE_SPEAKING:
                self.recorder.unmute_microphone()
            
            print("Speech stopped")



VOICE_CONFIG = {
    "angry": {
        "voice": "fr-CA-AntoineNeural",
        "style": "angry",
        "styledegree": "3.0",
        "rate": "+30%",
        "pitch": "-4Hz"
    },
    "happy": {
        "voice": "fr-CA-AntoineNeural",
        "style": "happy",
        "styledegree": "3.0",
        "rate": "+25%",
        "pitch": "+4Hz"
    },
    "sad": {
        "voice": "fr-CA-AntoineNeural",
        "style": "sad",
        "styledegree": "3.0",
        "rate": "-10%",
        "pitch": "-3Hz"
    },
    "surprise": {
        "voice": "fr-CA-AntoineNeural",
        "style": "excited",
        "styledegree": "3.0",
        "rate": "+15%",
        "pitch": "+3Hz"
    },
    "neutral": {
        "voice": "fr-CA-AntoineNeural",
        "style": "neutral",
        "styledegree": "3.0",
        "rate": "+15%",
        "pitch": "+4Hz"
    },
    "fear": {
        "voice": "fr-CA-AntoineNeural",
        "style": "terrified",
        "styledegree": "3.0",
        "rate": "-5%",
        "pitch": "-2Hz"
    },
    "disgust": {
        "voice": "fr-CA-AntoineNeural",
        "style": "disgusted",
        "styledegree": "3.0",
        "rate": "-10%",
        "pitch": "-4Hz"
    }
}

# # List of available EMOTIONS
# EMOTIONS = ["fear", "neutral", "surprise", "sad", "happy", "angry", "disgust"]
EMOTIONS = ["not impressed", "posessed", "angry", "sad", "fear", "surprise", "neutral"]
REACTIONS=["not impressed", "posessed", "angry", "sad", "fear", "surprise", "neutral"]

