from glob import glob
import os

from setuptools import setup

package_name = "evo_vision"

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
    description="Evo-Botics camera perception nodes.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "human_approach_node = evo_vision.human_approach_node:main",
            "qr_scanner_node = evo_vision.qr_scanner_node:main",
            "depth_obstacle_scan_node = evo_vision.depth_obstacle_scan_node:main",
            "object_detector_node = evo_vision.object_detector_node:main",
        ],
    },
)
