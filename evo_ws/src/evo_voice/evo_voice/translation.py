from __future__ import annotations


class TranslationConfigurationError(RuntimeError):
    """Raised when required offline Argos translation packages are absent."""


class OfflineTranslator:
    def __init__(self, language: str) -> None:
        import argostranslate.package
        import argostranslate.translate

        self._translate = argostranslate.translate.translate
        required_pairs = {
            "fr": {("fr", "en")},
            "en": {("en", "fr")},
            "auto": {("fr", "en"), ("en", "fr")},
        }[language]
        installed_pairs = {
            (package.from_code, package.to_code)
            for package in argostranslate.package.get_installed_packages()
        }
        missing_pairs = required_pairs - installed_pairs
        if missing_pairs:
            formatted = ", ".join(
                f"{source}->{target}" for source, target in sorted(missing_pairs)
            )
            raise TranslationConfigurationError(
                "Missing offline Argos translation package(s): "
                f"{formatted}. Install them before starting evo_voice; "
                "runtime downloads are disabled."
            )

    def translate(self, text: str, source: str, target: str) -> str:
        return self._translate(text, source, target)
