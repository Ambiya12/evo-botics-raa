from glob import glob
import os

from setuptools import setup

package_name = "evo_web"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "web"), glob("web/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Evo-Botics",
    maintainer_email="evobotics@example.com",
    description="Evo-Botics rosbridge and camera HTTP bridge.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "arm_command_relay_node = evo_web.arm_command_relay_node:main",
            "web_server_node = evo_web.web_server_node:main",
        ],
    },
)
