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
    description="Mirror of /reception/qr/status on the HDMI LCD (kiosk screens).",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "lcd_screen_node = evo_screen.lcd_screen_node:main",
        ],
    },
)
