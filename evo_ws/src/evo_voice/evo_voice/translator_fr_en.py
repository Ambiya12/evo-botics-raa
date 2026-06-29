from __future__ import annotations

import os
import subprocess
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from evo_voice.config import ConfigurationError, VoiceConfig
from evo_voice.translation import OfflineTranslator, TranslationConfigurationError


class TranslatorNode(Node):
    """Legacy translation prototype, kept separate from the reception workflow."""

    def __init__(self) -> None:
        super().__init__("translator_node")
        self.config = VoiceConfig.from_node(self)
        self.publisher_ = self.create_publisher(String, "/voice/translation", 10)
        self.model: Any = None
        self.recognizer: Any = None
        self.translator: OfflineTranslator | None = None

        if self.config.mock_audio:
            self.get_logger().warning(
                "Mock audio mode is active; microphone capture, transcription, "
                "translation, and playback are disabled."
            )
            return

        self._initialize_hardware_mode()

    def _initialize_hardware_mode(self) -> None:
        import speech_recognition as sr
        from faster_whisper import WhisperModel

        self.get_logger().info("Loading installed offline translation packages")
        self.translator = OfflineTranslator(self.config.language)

        self.get_logger().info(f"Loading Whisper model from {self.config.model_path}")
        self.model = WhisperModel(
            str(self.config.model_path),
            device=self.config.device,
            compute_type="int8",
            local_files_only=True,
        )

        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    def translate(self, text: str, source: str, target: str) -> str:
        if self.translator is None:
            raise RuntimeError("Translation is unavailable in mock audio mode")
        return self.translator.translate(text, source, target)

    def speak(self, text: str, language: str) -> None:
        if self.config.mock_audio:
            self.get_logger().info(f"[MOCK ROBOT ({language})] {text}")
            return

        model_path = (
            self.config.french_voice_path
            if language == "fr"
            else self.config.english_voice_path
        )
        self.get_logger().info(f"[ROBOT ({language})] {text}")
        subprocess.run(
            [
                "piper",
                "--model",
                str(model_path),
                "--output_file",
                str(self.config.playback_path),
            ],
            input=text,
            text=True,
            check=True,
        )
        subprocess.run(
            [
                "mpv",
                "--no-video",
                "--really-quiet",
                str(self.config.playback_path),
            ],
            check=True,
        )

    def announce_startup(self) -> None:
        self.speak("Système de traduction activé.", "fr")
        self.speak("Translation system activated.", "en")

    def cleanup(self) -> None:
        for path in (self.config.capture_path, self.config.playback_path):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    def listen_loop(self) -> None:
        if self.config.mock_audio:
            self.get_logger().info("Mock translator ready; spinning without audio hardware")
            rclpy.spin(self)
            return

        import speech_recognition as sr

        self.announce_startup()
        device_index = (
            None if self.config.audio_device == -1 else self.config.audio_device
        )
        with sr.Microphone(device_index=device_index) as source:
            self.get_logger().info("Translator ready")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

            while rclpy.ok():
                try:
                    audio = self.recognizer.listen(
                        source, timeout=None, phrase_time_limit=10
                    )
                    self.config.capture_path.write_bytes(audio.get_wav_data())

                    language = (
                        None if self.config.language == "auto" else self.config.language
                    )
                    segments, info = self.model.transcribe(
                        str(self.config.capture_path),
                        beam_size=5,
                        vad_filter=True,
                        language=language,
                    )
                    text = "".join(segment.text for segment in segments).strip()
                    if not text or info.language_probability <= 0.4:
                        continue

                    if info.language == "fr":
                        translated = self.translate(text, "fr", "en")
                        self.speak(translated, "en")
                    elif info.language == "en":
                        translated = self.translate(text, "en", "fr")
                        self.speak(translated, "fr")
                    else:
                        continue

                    self.publisher_.publish(String(data=translated))
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    self.get_logger().error(f"Legacy translator cycle failed: {exc}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node: TranslatorNode | None = None
    try:
        node = TranslatorNode()
        node.listen_loop()
    except (ConfigurationError, TranslationConfigurationError) as exc:
        rclpy.logging.get_logger("translator_node").fatal(str(exc))
        raise SystemExit(2) from exc
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.cleanup()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
