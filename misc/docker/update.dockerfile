FROM python:3-alpine

RUN mkdir /var/db
RUN mkdir /var/www
RUN mkdir /var/www/pkgs.void
WORKDIR /var/www/pkgs.void
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apk add bash
RUN apk add git rsync tar wget xbps zstd
RUN git clone --depth 1 https://github.com/leahneukirchen/xtools /var/www/xtools
COPY . .
COPY misc/docker/config-docker.ini config.ini
COPY misc/docker/cronjob.sh /etc/periodic/hourly

VOLUME /var/db
CMD /etc/periodic/hourly/cronjob.sh -T && crond -f
