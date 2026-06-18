from glob import glob
import os

from setuptools import setup

package_name = "evo_reception"

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
    description="Evo-Botics reception flow nodes.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "qr_reservation_bridge_node = evo_reception.qr_reservation_bridge_node:main",
        ],
    },
)
