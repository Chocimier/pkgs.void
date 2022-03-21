FROM python:3-alpine

RUN mkdir /var/db
RUN mkdir /var/www
RUN mkdir /var/www/pkgs.void
WORKDIR /var/www/pkgs.void
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apk add bash
COPY . .
COPY misc/docker/config-docker.ini config.ini

VOLUME /var/db
EXPOSE 4001
CMD [ "python", "serve.py", "flup_bind", "0.0.0.0", "4001" ]
