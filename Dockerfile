
FROM python:3.9


ENV DEBIAN_FRONTEND=noninteractive

# Installazione pacchetti iniziali
RUN apt-get update -qq && \
    apt-get install -y -qq pkg-config gcc libc-dev default-libmysqlclient-dev


WORKDIR /app

COPY requirements.txt requirements.txt

# Dipendenze MySQL
ENV MYSQLCLIENT_CFLAGS="-I/usr/include/mysql" \
    MYSQLCLIENT_LDFLAGS="-L/usr/lib/x86_64-linux-gnu -lmysqlclient"

# Installazione librerie
RUN pip install -r requirements.txt

# Copia del codice dell'app nell'immagine 
COPY . .

# Esposizione porta
ENV PORT=8080

# Avvio app Flask
CMD ["python", "main.py"]


# Build Docker
# docker build -t gcr.io/emails-analysis/flask-webapp .
# docker run -p 8080:8080 gcr.io/emails-analysis/flask-webapp

# Avvio con VM
# python3 -m venv venv
# source venv/bin/activate
# python main.py