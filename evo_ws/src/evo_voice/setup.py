from glob import glob
import os

from setuptools import setup

package_name = "evo_voice"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Evo-Botics",
    maintainer_email="evobotics@example.com",
    description="Evo-Botics speech translation node.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "intent_detector_node = evo_voice.intent_detector_node:main",
            "stt_node = evo_voice.stt_node:main",
            "tts_node = evo_voice.tts_node:main",
            "translator_node = evo_voice.translator_fr_en:main",
        ],
    },
)
