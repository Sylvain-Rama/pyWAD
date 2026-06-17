#!/usr/bin/env bash
set -euxo pipefail

# Remove problematic Yarn repository if present
sudo rm -f /etc/apt/sources.list.d/yarn.list || true

# Install dependencies
sudo apt-get update
sudo apt-get install -y \
    libfluidsynth-dev \
    cmake \
    build-essential \
    libglib2.0-dev \
    libsndfile1-dev \
    libasound2-dev \
    libpulse-dev

# Download and build FluidSynth
wget -q \
    https://github.com/FluidSynth/fluidsynth/archive/refs/tags/v2.4.5.tar.gz \
    -O /tmp/fluidsynth.tar.gz

tar -xf /tmp/fluidsynth.tar.gz -C /tmp

cmake \
    -S /tmp/fluidsynth-2.4.5 \
    -B /tmp/fluidsynth-build \
    -DCMAKE_INSTALL_PREFIX=/workspaces/pyWAD/fluidsynth \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_LIBDIR=lib

cmake --build /tmp/fluidsynth-build --target install -j"$(nproc)"

rm -rf \
    /tmp/fluidsynth-2.4.5 \
    /tmp/fluidsynth-build \
    /tmp/fluidsynth.tar.gz

echo "FluidSynth built and installed"

