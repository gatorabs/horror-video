#!/usr/bin/env bash
# Instala o que o motor precisa no WSL/Ubuntu (voz, mixagem, ffmpeg). O render na GPU roda no Windows (veja o README).
set -euo pipefail
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg sox fonts-dejavu-core fonts-freefont-ttf python3-pip
pip install --break-system-packages numpy pillow soundfile
echo "Pronto. Coloque a chave do ElevenLabs em ~/.elevenlabs_key e rode: python3 -m engine.build episodios/NN-nome"
