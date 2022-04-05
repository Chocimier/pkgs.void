FROM python:3-alpine

RUN mkdir /var/db
RUN mkdir /var/www
RUN mkdir /var/www/pkgs.void
WORKDIR /var/www/pkgs.void
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apk add bash
RUN apk add git rsync tar wget xbps zstd
RUN echo '20,50 * * * * sh /var/www/pkgs.void/misc/docker/cronjob.sh' >> /var/spool/cron/crontabs/root
RUN git clone --depth 1 https://github.com/leahneukirchen/xtools /var/www/xtools
COPY . .
COPY misc/docker/config-docker.ini config.ini

VOLUME /var/db
CMD /var/www/pkgs.void/misc/docker/cronjob.sh -T -B && crond -f
