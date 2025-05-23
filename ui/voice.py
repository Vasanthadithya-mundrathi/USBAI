import speech_recognition as sr
import pyttsx3

class VoiceInterface:
    def __init__(self, engine):
        self.engine = engine
        self.recognizer = sr.Recognizer()
        self.speaker = pyttsx3.init()
        
    def listen_for_wake_word(self):
        with sr.Microphone() as source:
            audio = self.recognizer.listen(source)
            try:
                text = self.recognizer.recognize_google(audio, show_all=False)
                return text.lower() == "hey ai"
            except:
                return False

    def start(self):
        while True:
            if self.listen_for_wake_word():
                self.speaker.say("How can I help?")
                self.speaker.runAndWait()
                # Continue with voice interaction

def start(engine):
    voice = VoiceInterface(engine)
    voice.start()
