# Utiliser l'image Jenkins officielle comme base
FROM jenkins/jenkins:lts-jdk11

# Passer à l'utilisateur root pour installer des paquets
USER root

# Installer les dépendances de base
RUN apt-get update && apt-get install -y \
    curl \
    lsb-release \
    && apt-get clean

# Ajouter le dépôt NVIDIA CUDA et installer cuda-toolkit
RUN curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb -o cuda-keyring.deb \
    && dpkg -i cuda-keyring.deb \
    && rm cuda-keyring.deb \
    && apt-get update && apt-get install -y cuda-toolkit-13-0 \
    && apt-get clean

# Ajouter le dépôt Docker et installer le client Docker
RUN curl -fsSLo /usr/share/keyrings/docker-archive-keyring.asc \
    https://download.docker.com/linux/debian/gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.asc] \
    https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y docker-ce-cli \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Revenir à l'utilisateur jenkins par défaut
USER jenkins