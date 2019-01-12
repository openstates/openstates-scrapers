FROM        alpine:3.8
MAINTAINER  James Turk <james@openstates.org>

ENV PYTHONIOENCODING 'utf-8'
ENV LANG 'en_US.UTF-8'
ENV PUPA_ENV /opt/openstates/venv-pupa/

ADD . /opt/openstates/openstates

RUN apk add --no-cache --virtual .build-dependencies \
    wget \
    build-base \
    autoconf \
    automake \
    libtool && \
  apk add --no-cache \
    git \
    curl \
    unzip \
    glib \
    glib-dev \
    libressl-dev \
    libffi-dev \
    freetds-dev \
    python3 \
    python3-dev \
    py-virtualenv \
    libxml2-dev \
    libxslt-dev \
    yaml-dev \
    poppler-utils \
    postgresql-dev \
    postgresql-client \
    mariadb \
    mariadb-dev \
    mysql-client && \
  apk add --no-cache \
    --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
    libcrypto1.1 && \
  apk add --no-cache \
    --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
    aws-cli \
    gdal-dev \
    geos-dev && \
  cd /tmp && \
    wget "https://github.com/brianb/mdbtools/archive/0.7.1.zip" && \
    unzip 0.7.1.zip && rm 0.7.1.zip && \
    cd mdbtools-0.7.1 && \
    autoreconf -i -f && \
    ./configure --disable-man && make && make install && \
    cd /tmp && \
    rm -rf mdbtools-0.7.1 && \
  virtualenv -p $(which python3) /opt/openstates/venv-pupa/ && \
    /opt/openstates/venv-pupa/bin/pip install -e git+https://github.com/opencivicdata/python-opencivicdata-django.git#egg=opencivicdata && \
    /opt/openstates/venv-pupa/bin/pip install -e git+https://github.com/opencivicdata/pupa.git#egg=pupa && \
    /opt/openstates/venv-pupa/bin/pip install -r /opt/openstates/openstates/requirements.txt && \
  apk del .build-dependencies

WORKDIR /opt/openstates/openstates/
ENTRYPOINT ["/opt/openstates/openstates/pupa-scrape.sh"]
