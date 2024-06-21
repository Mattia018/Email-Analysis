# Usa l'immagine di Python ufficiale come base
FROM python:3.9


# Imposta la variabile d'ambiente non interattiva
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update -qq && \
    apt-get install -y -qq pkg-config gcc libc-dev default-libmysqlclient-dev


# Imposta la directory di lavoro nell'immagine del contenitore
WORKDIR /app

# Copia il file requirements.txt nella directory di lavoro
COPY requirements.txt requirements.txt

# Specifica manualmente le variabili d'ambiente per indicare al sistema dove trovare le dipendenze MySQL
ENV MYSQLCLIENT_CFLAGS="-I/usr/include/mysql" \
    MYSQLCLIENT_LDFLAGS="-L/usr/lib/x86_64-linux-gnu -lmysqlclient"

# Installa le dipendenze
RUN pip install -r requirements.txt

# Copia il codice dell'app nell'immagine del contenitore
COPY . .

# Esporta la variabile di ambiente per indicare al server di Flask su quale porta ascoltare
ENV PORT=8080

# Avvia l'app Flask
CMD ["python", "main.py"]

# docker build -t gcr.io/emails-analysis/flask-webapp .
# docker run -p 8080:8080 gcr.io/emails-analysis/flask-webapp


# python3 -m venv venv
# source venv/bin/activate
# python main.py