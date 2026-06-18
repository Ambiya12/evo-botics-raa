from glob import glob
import os

from setuptools import setup

package_name = "evo_screen"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Evo-Botics",
    maintainer_email="evobotics@example.com",
    description="Affiche la page web /kiosk en plein écran (chromium) sur le LCD du robot.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "kiosk = evo_screen.kiosk_node:main",
        ],
    },
)
