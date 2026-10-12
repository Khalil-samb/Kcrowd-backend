# Je veux construire mon application à partir d'une image
# qui contient déjà Python 3.12
FROM python:3.12-slim

# Docker va utiliser /app comme dossier principal de ton projet.
WORKDIR /app

# Essentiel pour voir les print() en direct (comme le code OTP affiché
# par ConsoleOtpSender) : sans ça, Python met sa sortie en mémoire tampon
# dès qu'elle ne va pas vers un vrai terminal — ce qui est toujours le cas
# à l'intérieur d'un conteneur Docker. Les messages finissent par
# apparaître, mais en retard, parfois bien après coup, ou jamais si le
# tampon ne se remplit jamais assez pour se vider tout seul.
ENV PYTHONUNBUFFERED=1

# Votre requirements.txt utilise psycopg-binary (psycopg 3, variante
# binaire) : contrairement à MySQL (default-libmysqlclient-dev) ou à
# psycopg2 classique, cette variante embarque déjà tout ce qu'il faut pour
# PostgreSQL — aucune bibliothèque système à installer ici.

# Copie requirements.txt dans /app/
COPY requirements.txt .

# Installation des dépendances Python.
RUN pip install --no-cache-dir -r requirements.txt

# Copie le projet Django dans /app/
COPY . .

# Port corrigé : votre commande ci-dessous lance Django sur le port
# 8001, mais EXPOSE indiquait 8000 — les deux doivent correspondre.
EXPOSE 8001

# Lance Django.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]