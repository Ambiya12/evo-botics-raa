import os
import sys
import speech_recognition as sr
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
from gtts import gTTS
import subprocess

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

CONFIG = {
    "model_size": "base",
    "device": "cpu",
    "temp_audio": "/dev/shm/temp_capture.wav",
    "speech_mp3": "/dev/shm/speech.mp3",
}

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log_system(msg):
    print(f"{YELLOW}{BOLD}[SYSTÈME]{RESET} {msg}")


def log_robot(lang, msg):
    print(f"{CYAN}{BOLD}[ROBOT ({lang})]{RESET} {msg}")


def log_user(lang, msg, prob):
    print(f"{GREEN}{BOLD}[USER ({lang})]{RESET} {msg} ({prob:.1%})")


class TranslatorNode(Node):
    def __init__(self):
        super().__init__("translator_node")

        self.declare_parameter("model_size", CONFIG["model_size"])
        self.declare_parameter("device", CONFIG["device"])
        self.declare_parameter("language", "fr")

        model_size = self.get_parameter("model_size").value
        device = self.get_parameter("device").value
        self.target_lang = self.get_parameter("language").value

        self.publisher_ = self.create_publisher(String, "/voice/translation", 10)

        log_system("Chargement du modèle Whisper...")
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    def parler(self, texte, langue):
        try:
            log_robot(langue, texte)
            tts = gTTS(text=texte, lang=langue)
            tts.save(CONFIG["speech_mp3"])
            subprocess.run(["mpv", "--no-video", "--really-quiet", CONFIG["speech_mp3"]])
        except Exception as e:
            print(f"Erreur TTS : {e}")

    def annoncer_demarrage(self):
        log_system("Démarrage...")
        self.parler("Système de traduction activé.", "fr")
        self.parler("Translation system activated.", "en")

    def nettoyer(self):
        for path in [CONFIG["temp_audio"], CONFIG["speech_mp3"]]:
            if os.path.exists(path):
                os.remove(path)

    def boucle_traduction(self):
        self.annoncer_demarrage()

        with sr.Microphone() as source:
            log_system("Calibrage micro (silence)...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.2)
            print(f"{GREEN}=== ROBOT PRÊT À TRADUIRE ==={RESET}\n")

            while rclpy.ok():
                try:
                    print(f"{YELLOW}À l'écoute...{RESET}", end="\r")
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=10)

                    print(f"{CYAN}Analyse...      {RESET}", end="\r")
                    with open(CONFIG["temp_audio"], "wb") as f:
                        f.write(audio.get_wav_data())

                    segments, info = self.model.transcribe(
                        CONFIG["temp_audio"],
                        beam_size=5,
                        vad_filter=True,
                        initial_prompt="User speaks French or English."
                    )

                    texte = "".join([s.text for s in segments]).strip()

                    if texte and info.language_probability > 0.4:
                        log_user(info.language, texte, info.language_probability)

                        if info.language == "fr":
                            traduction = GoogleTranslator(source='fr', target='en').translate(texte)
                            self.parler(traduction, "en")
                        elif info.language == "en":
                            traduction = GoogleTranslator(source='en', target='fr').translate(texte)
                            self.parler(traduction, "fr")
                        else:
                            continue

                        msg = String()
                        msg.data = traduction
                        self.publisher_.publish(msg)
                    else:
                        print(".", end="", flush=True)

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    log_system(f"Erreur : {e}")
                    continue


def main(args=None):
    rclpy.init(args=args)
    node = TranslatorNode()

    try:
        node.boucle_traduction()
    except KeyboardInterrupt:
        pass
    finally:
        node.parler("Désactivation. Au revoir.", "fr")
        node.parler("Shutting down. Goodbye.", "en")
        node.nettoyer()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
