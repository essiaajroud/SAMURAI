# Utiliser l'image Jenkins officielle comme base
FROM jenkins/jenkins:lts-jdk11

# Passer à l'utilisateur root pour installer des paquets
USER root

# Installer le client Docker et ses dépendances
RUN apt-get update && apt-get install -y lsb-release
RUN curl -fsSLo /usr/share/keyrings/docker-archive-keyring.asc \
    https://download.docker.com/linux/debian/gpg
RUN echo "deb [arch=$(dpkg --print-architecture) \
    signed-by=/usr/share/keyrings/docker-archive-keyring.asc] \
    https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
RUN apt-get update && apt-get install -y docker-ce-cli

# Revenir à l'utilisateur jenkins par défaut
USER jenkins