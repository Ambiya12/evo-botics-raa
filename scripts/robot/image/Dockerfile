ARG BASE_IMAGE=192.168.2.51.5000/rosmaster-m3pro-nano:1.1.0
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libasound2-plugins \
      libzbar0 \
      mpv \
      python3-numpy \
      python3-opencv \
      python3-pyaudio \
      python3-pip \
      python3-pyzbar \
      python3-yaml \
      ros-humble-cv-bridge \
      ros-humble-foxglove-bridge \
      ros-humble-nav2-bringup \
      ros-humble-robot-state-publisher \
      ros-humble-rosbridge-server \
      ros-humble-rviz2 \
      ros-humble-slam-toolbox \
      ros-humble-xacro \
    && apt-get install -y --reinstall --no-install-recommends \
      libasound2-plugins \
    && python3 -m pip install --no-cache-dir \
      faster-whisper \
      SpeechRecognition \
    && rm -rf /var/lib/apt/lists/*

COPY jetson/evo-ros-entrypoint.sh /root/joy.sh
RUN chmod 0755 /root/joy.sh \
    && printf '%s\n' \
      'pcm.!default {' \
      '  type pulse' \
      '}' \
      'ctl.!default {' \
      '  type pulse' \
      '}' \
      > /root/.asoundrc \
    && python3 -c "import cv2, numpy, yaml; from pyzbar.pyzbar import decode" \
    && bash -lc "source /opt/ros/humble/setup.bash \
      && ros2 pkg prefix cv_bridge \
      && ros2 pkg prefix foxglove_bridge \
      && ros2 pkg prefix nav2_bringup \
      && ros2 pkg prefix rosbridge_server \
      && ros2 pkg prefix rviz2 \
      && ros2 pkg prefix slam_toolbox"

CMD ["/bin/bash", "/root/joy.sh"]
