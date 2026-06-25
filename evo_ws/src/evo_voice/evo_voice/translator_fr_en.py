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

# --- CONFIGURATION ---
MODEL_SIZE = "small"
DEVICE = "cpu"
TEMP_AUDIO = "/dev/shm/temp_capture.wav"
VOICE_FR = "~/piper_models/fr_FR-siwis-low.onnx"
VOICE_EN = "~/piper_models/en_US-arctic-medium.onnx"

# Couleurs terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


class TranslatorNode(Node):
    def __init__(self):
        super().__init__("translator_node")

        self.publisher_ = self.create_publisher(String, "/voice/translation", 10)

        self.get_logger().info("Initialisation des dictionnaires locaux...")
        self._setup_translation()

        model_size = MODEL_SIZE
        self.get_logger().info(f"Chargement de Whisper ({model_size})...")
        self.model = WhisperModel(model_size, device=DEVICE, compute_type="int8")

        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    def _setup_translation(self):
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()
        for from_c, to_c in [("fr", "en"), ("en", "fr")]:
            installed = argostranslate.package.get_installed_packages()
            if not any(p.from_code == from_c and p.to_code == to_c for p in installed):
                self.get_logger().info(f"Installation du pack {from_c} -> {to_c}...")
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
        model_path = os.path.expanduser(VOICE_FR if langue == "fr" else VOICE_EN)
        out_wav = "/dev/shm/voice.wav"

        self.get_logger().info(f"[ROBOT ({langue})] {texte}")
        cmd = f"echo '{texte}' | piper --model {model_path} --output_file {out_wav}"
        os.system(cmd)
        subprocess.run(["mpv", "--no-video", "--really-quiet", out_wav])

    def annoncer_demarrage(self):
        print(f"\n{GREEN}{BOLD}--- DÉMARRAGE DU ROBOT ---{RESET}")
        self.parler("Système de traduction activé.", "fr")
        self.parler("Translation system activated.", "en")

    def nettoyer(self):
        if os.path.exists(TEMP_AUDIO):
            os.remove(TEMP_AUDIO)

    def boucle_ecoute(self):
        self.annoncer_demarrage()

        with sr.Microphone() as source:
            print(f"\n{GREEN}=== ROBOT PRÊT ==={RESET}")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

            while rclpy.ok():
                try:
                    print(f"{YELLOW}Écoute...{RESET}", end="\r")
                    audio = self.recognizer.listen(
                        source, timeout=None, phrase_time_limit=10
                    )

                    with open(TEMP_AUDIO, "wb") as f:
                        f.write(audio.get_wav_data())

                    segments, info = self.model.transcribe(
                        TEMP_AUDIO, beam_size=5, vad_filter=True
                    )
                    texte = "".join([s.text for s in segments]).strip()

                    if texte and info.language_probability > 0.4:
                        print(f"{GREEN}{BOLD}[MOI ({info.language})]{RESET} {texte}")

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
                    print(f"\n{RED}Erreur : {e}{RESET}")


def main(args=None):
    rclpy.init(args=args)
    node = TranslatorNode()

    try:
        node.boucle_ecoute()
    except KeyboardInterrupt:
        pass
    finally:
        node.parler("Fermeture du traducteur. Au revoir.", "fr")
        node.parler("Shutting down. Goodbye.", "en")
        node.nettoyer()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
