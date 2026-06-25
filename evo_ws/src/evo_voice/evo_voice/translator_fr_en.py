import os
import sys
import subprocess
import speech_recognition as sr
from faster_whisper import WhisperModel
import argostranslate.package
import argostranslate.translate

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# CONFIGURATION
MODEL_SIZE = "small"
DEVICE = "cpu"
TEMP_AUDIO = "/dev/shm/temp_capture.wav"
SPEECH_WAV = "/dev/shm/voice.wav"

# Couleurs terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


class TranslatorNode(Node):
    def __init__(self):ß
        super().__init__("translator_node")

        self.declare_parameter("model_size", MODEL_SIZE)
        self.declare_parameter("device", DEVICE)

        self.publisher_ = self.create_publisher(String, "/voice/translation", 10)

        self.get_logger().info("Configuration du traducteur local...")
        self._setup_translation()

        self.get_logger().info("Chargement de Whisper...")
        model_size = self.get_parameter("model_size").value
        device = self.get_parameter("device").value
        self.model = WhisperModel(model_size, device=device, compute_type="int8")

        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True

    def _setup_translation(self):
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()
        for from_c, to_c in [("fr", "en"), ("en", "fr")]:
            pkg = next(
                filter(
                    lambda x: x.from_code == from_c and x.to_code == to_c,
                    available,
                )
            )
            argostranslate.package.install_from_path(pkg.download())

    def traduire(self, texte, source, cible):
        return argostranslate.translate.translate(texte, source, cible)

    def parler(self, texte, langue):
        self.get_logger().info(f"[ROBOT ({langue})] {texte}")
        cmd = f"echo '{texte}' | piper --model fr_FR-siwis-low --output_file {SPEECH_WAV}"
        if langue == "en":
            cmd = f"echo '{texte}' | piper --model en_GB-vctk-medium --output_file {SPEECH_WAV}"
        os.system(cmd)
        subprocess.run(["mpv", "--no-video", "--really-quiet", SPEECH_WAV])

    def nettoyer(self):
        for path in [TEMP_AUDIO, SPEECH_WAV]:
            if os.path.exists(path):
                os.remove(path)

    def boucle_ecoute(self):
        self.parler("Système de traduction activé.", "fr")
        self.parler("Translation system activated.", "en")

        with sr.Microphone() as source:
            self.get_logger().info("Calibrage micro...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print(f"{GREEN}=== PRÊT (OFFLINE) ==={RESET}")

            while rclpy.ok():
                try:
                    print(f"{YELLOW}Écoute...{RESET}", end="\r")
                    audio = self.recognizer.listen(
                        source, timeout=None, phrase_time_limit=10
                    )

                    with open(TEMP_AUDIO, "wb") as f:
                        f.write(audio.get_wav_data())

                    segments, info = self.model.transcribe(
                        TEMP_AUDIO, beam_size=5
                    )
                    texte = "".join([s.text for s in segments]).strip()

                    if texte and info.language_probability > 0.4:
                        print(
                            f"{GREEN}[{info.language}]{RESET} {texte} "
                            f"({info.language_probability:.1%})"
                        )

                        if info.language == "fr":
                            trad = self.traduire(texte, "fr", "en")
                            self.parler(trad, "en")
                        elif info.language == "en":
                            trad = self.traduire(texte, "en", "fr")
                            self.parler(trad, "fr")
                        else:
                            continue

                        msg = String()
                        msg.data = trad
                        self.publisher_.publish(msg)
                    else:
                        print(".", end="", flush=True)

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.get_logger().error(f"Erreur : {e}")
                    continue


def main(args=None):
    rclpy.init(args=args)
    node = TranslatorNode()

    try:
        node.boucle_ecoute()
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
