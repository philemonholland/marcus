import azure.cognitiveservices.speech as speechsdk
import tempfile
import os
from playsound import playsound
import time

# --- API Keys & Client Initialization ---
speech_key = "2m8rgVMevYUQveKu0u36BVdHM7Ta1LJT9D7k5ILq5R4Su6LtouVWJQQJ99BCACREanaXJ3w3AAAYACOGgoUI"
speech_region = "canadaeast"



# 1. First, let's create a simple test function to verify voice selection is working

def test_azure_voices():
    """
    A simple test function to check if different Azure voices are accessible
    and working correctly with your subscription.
    """

    
    # List of voices to test
    voices_to_test = [
        "fr-CA-SylvieNeural",
        "fr-CA-JeanNeural",
        "fr-CA-AntoineNeural"
    ]
    
    test_text = "Ceci est un test pour vérifier que la voix est correctement sélectionnée."
    
    for voice in voices_to_test:
        try:
            # Configure speech service
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
            speech_config.speech_synthesis_voice_name = voice
            
            # Print clear indication of which voice is being tested
            print(f"\n{'='*50}")
            print(f"TESTING VOICE: {voice}")
            print(f"{'='*50}")
            
            # Create a temporary file for output
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()
            
            # Configure audio output
            audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_file.name)
            
            # Create speech synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            # Basic SSML without any extra formatting that might interfere
            simple_ssml = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="fr-CA">
                <voice name="{voice}">
                    {test_text}
                </voice>
            </speak>
            """
            
            # Perform synthesis
            print(f"Synthesizing speech with voice: {voice}")
            result = synthesizer.speak_ssml_async(simple_ssml).get()
            
            # Check result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"Speech synthesis succeeded for voice: {voice}")
                print(f"Playing audio for voice: {voice}")
                playsound(temp_file.name)
            else:
                print(f"Speech synthesis failed for voice: {voice}")
                print(f"Reason: {result.reason}")
                if result.reason == speechsdk.ResultReason.Canceled:
                    cancellation_details = speechsdk.SpeechSynthesisCancellationDetails(result)
                    print(f"CANCELED: Reason={cancellation_details.reason}")
                    print(f"CANCELED: Error details={cancellation_details.error_details}")
            
            # Clean up
            time.sleep(1)  # Give some time before removing the file
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
                
        except Exception as e:
            print(f"Error testing voice {voice}: {str(e)}")

# 2. Now let's create a modified version of your _azure_tts_sync function with better error handling

def improved_azure_tts_sync(text, output_file, voice_name="fr-CA-SylvieNeural"):
    """
    An improved version of the Azure TTS function with better error handling
    and debugging information.
    """
    
    # Print what we're trying to do
    print(f"Attempting to synthesize speech with voice: {voice_name}")
    
    # Create the speech config
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
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
    
    # Create SSML without any unnecessary elements that might interfere
    ssml = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="fr-CA">
        <voice name="{voice_name}">
            {text}
        </voice>
    </speak>
    """
    
    # Print the SSML we're using (for debugging)
    print("Using SSML:")
    print(ssml)
    
    # Perform synthesis
    result = speech_synthesizer.speak_ssml_async(ssml).get()
    
    # Check result with detailed error information
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesis succeeded with voice: {voice_name}")
        return True
    else:
        print(f"Speech synthesis failed with voice: {voice_name}")
        print(f"Reason: {result.reason}")
        
        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speechsdk.SpeechSynthesisCancellationDetails(result)
            print(f"CANCELED: Reason={cancellation_details.reason}")
            print(f"CANCELED: Error details={cancellation_details.error_details}")
        
        return False

# 3. Alternative approach: try using a different synthesis method

def alternative_azure_tts(text, output_file, voice_name="fr-CA-SylvieNeural"):
    """
    An alternative approach using the speak_text_async method instead of SSML.
    This can sometimes resolve issues when SSML processing is problematic.
    """
    # Create the speech config with explicit voice selection
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
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
    
    # Use simple text-to-speech instead of SSML
    print(f"Attempting simple text synthesis with voice: {voice_name}")
    result = speech_synthesizer.speak_text_async(text).get()
    
    # Check result
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Simple text synthesis succeeded with voice: {voice_name}")
        return True
    else:
        print(f"Simple text synthesis failed with voice: {voice_name}")
        print(f"Reason: {result.reason}")
        
        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speechsdk.SpeechSynthesisCancellationDetails(result)
            print(f"CANCELED: Reason={cancellation_details.reason}")
            print(f"CANCELED: Error details={cancellation_details.error_details}")
        
        return False

# 4. Function to list available voices in your region
def list_available_voices():
    """
    Lists all available voices in your Azure region.
    This requires the azure-cognitiveservices-speech SDK version 1.20.0 or later.
    """

    
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    
    try:
        # This requires SDK version 1.20.0 or later
        result = speech_synthesizer.get_voices_async().get()
        
        if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
            french_voices = [voice for voice in result.voices 
                            if voice.locale.startswith('fr-')]
            
            print(f"Found {len(french_voices)} French voices:")
            for voice in french_voices:
                print(f"- {voice.name} ({voice.locale}, {voice.gender})")
                print(f"  Short name: {voice.short_name}")
                print(f"  Local name: {voice.local_name}")
                if hasattr(voice, 'style_list') and voice.style_list:
                    print(f"  Styles: {', '.join(voice.style_list)}")
                print()
                
            return french_voices
        else:
            print(f"Voice list retrieval failed, reason: {result.reason}")
            return []
        
    except Exception as e:
        print(f"Error retrieving voice list: {str(e)}")
        print("Note: This function requires Azure Speech SDK version 1.20.0 or later.")
        return []

# Example of how to use these functions in your main code:
"""
# To test all voices
test_azure_voices()

# To list available voices
list_available_voices()

# To use improved TTS function in your main loop
try:
    unique_name = f"output_{time.time_ns()}.mp3"
    success = improved_azure_tts_sync(message, unique_name, "fr-CA-SylvieNeural")
    if success:
        playsound(unique_name)
    else:
        print("Trying alternative method...")
        success = alternative_azure_tts(message, unique_name, "fr-CA-SylvieNeural")
        if success:
            playsound(unique_name)
        else:
            print("Both synthesis methods failed")
except Exception as e:
    print(f"Error during speech synthesis or playback: {e}")
"""

import argparse

def main():
    """
    Main function to run the Azure voice tests with command line arguments
    to choose which tests to run.
    """
    parser = argparse.ArgumentParser(description='Test Azure Text-to-Speech voices')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--list', action='store_true', help='List available voices')
    parser.add_argument('--test', action='store_true', help='Test specific voices')
    parser.add_argument('--improved', action='store_true', help='Test improved TTS function')
    parser.add_argument('--alternative', action='store_true', help='Test alternative TTS function')
    parser.add_argument('--text', type=str, default="Ceci est un test de synthèse vocale. Est-ce que vous m'entendez bien?", 
                        help='Text to synthesize')
    parser.add_argument('--voice', type=str, default="fr-CA-SylvieNeural", 
                        help='Voice to use (default: fr-CA-SylvieNeural)')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    # If --all flag is used, run all tests
    if args.all:
        print("\n=== LISTING ALL AVAILABLE VOICES ===")
        list_available_voices()
        
        print("\n=== TESTING SPECIFIC VOICES ===")
        test_azure_voices()
        
        print("\n=== TESTING IMPROVED TTS FUNCTION ===")
        test_improved_tts(args.text, args.voice)
        
        print("\n=== TESTING ALTERNATIVE TTS FUNCTION ===")
        test_alternative_tts(args.text, args.voice)
        return
    
    # Otherwise run individual tests as requested
    if args.list:
        print("\n=== LISTING ALL AVAILABLE VOICES ===")
        list_available_voices()
    
    if args.test:
        print("\n=== TESTING SPECIFIC VOICES ===")
        test_azure_voices()
    
    if args.improved:
        print("\n=== TESTING IMPROVED TTS FUNCTION ===")
        test_improved_tts(args.text, args.voice)
    
    if args.alternative:
        print("\n=== TESTING ALTERNATIVE TTS FUNCTION ===")
        test_alternative_tts(args.text, args.voice)

def test_improved_tts(text, voice):
    """Helper function to test the improved TTS function"""
    import time
    import os
    from playsound import playsound
    
    unique_name = f"output_improved_{time.time_ns()}.mp3"
    success = improved_azure_tts_sync(text, unique_name, voice)
    
    if success:
        try:
            print(f"Playing audio file: {unique_name}")
            playsound(unique_name)
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    # Cleanup
    try:
        if os.path.exists(unique_name):
            time.sleep(1)  # Give some time before removing
            os.remove(unique_name)
            print(f"Removed temporary file: {unique_name}")
    except Exception as e:
        print(f"Error removing file: {e}")

def test_alternative_tts(text, voice):
    """Helper function to test the alternative TTS function"""
    import time
    import os
    from playsound import playsound
    
    unique_name = f"output_alternative_{time.time_ns()}.mp3"
    success = alternative_azure_tts(text, unique_name, voice)
    
    if success:
        try:
            print(f"Playing audio file: {unique_name}")
            playsound(unique_name)
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    # Cleanup
    try:
        if os.path.exists(unique_name):
            time.sleep(1)  # Give some time before removing
            os.remove(unique_name)
            print(f"Removed temporary file: {unique_name}")
    except Exception as e:
        print(f"Error removing file: {e}")

if __name__ == "__main__":
    main()