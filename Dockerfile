FROM        alpine:3.7
MAINTAINER  James Turk <james@openstates.org>

ENV PYTHONIOENCODING 'utf-8'
ENV LANG 'en_US.UTF-8'
ENV BILLY_ENV /opt/openstates/venv-billy/
ENV PUPA_ENV /opt/openstates/venv-pupa/

ADD . /opt/openstates/openstates

RUN apk add --no-cache --virtual .build-dependencies \
    wget \
    build-base \
    glib \
    glib-dev \
    autoconf \
    automake \
    libtool && \
  apk add --no-cache \
    git \
    curl \
    unzip \
    libressl-dev \
    libffi-dev \
    freetds-dev \
    python \
    python-dev \
    python3 \
    python3-dev \
    py-virtualenv \
    libxml2-dev \
    libxslt-dev \
    poppler-utils \
    postgresql-dev \
    mariadb-dev && \
  apk add --no-cache \
    --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
    libressl2.7-libcrypto && \
  apk add --no-cache \
    --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
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
  virtualenv -p $(which python2) /opt/openstates/venv-billy/ && \
    /opt/openstates/venv-billy/bin/pip install -e git+https://github.com/openstates/billy.git#egg=billy && \
    /opt/openstates/venv-billy/bin/pip install python-dateutil && \
  virtualenv -p $(which python3) /opt/openstates/venv-pupa/ && \
    /opt/openstates/venv-pupa/bin/pip install -e git+https://github.com/opencivicdata/python-opencivicdata-django.git#egg=python-opencivicdata && \
    /opt/openstates/venv-pupa/bin/pip install -e git+https://github.com/opencivicdata/pupa.git#egg=pupa && \
    /opt/openstates/venv-pupa/bin/pip install -r /opt/openstates/openstates/requirements.txt && \
  apk del .build-dependencies

WORKDIR /opt/openstates/openstates/
ENTRYPOINT [/opt/openstates/openstates/pupa-scrape.sh]
