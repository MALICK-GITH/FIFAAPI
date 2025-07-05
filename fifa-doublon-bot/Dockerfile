# Base Python
FROM python:3.10-slim

# Création du dossier
WORKDIR /app

# Dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code
COPY fifa_doublon_bot.py .
CMD ["python", "fifa_doublon_bot.py"]
