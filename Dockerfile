FROM python:3.7-slim
LABEL maintainer="James Turk <james@openstates.org>"

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING 'utf-8'
ENV LANG 'C.UTF-8'

RUN apt update && apt install -y --no-install-recommends \
      git \
      build-essential \
      curl \
      unzip \
      libssl-dev \
      libffi-dev \
      freetds-dev \
      python3-virtualenv \
      libxml2-dev \
      libxslt-dev \
      libyaml-dev \
      poppler-utils \
      libpq-dev \
      libgdal-dev \
      libgeos-dev \
      libmariadb-dev \
#     mariadb \
#     mariadb-client \
#     libcrypto1.1 \
      mdbtools && \
      rm -rf /var/lib/apt/lists/*

ADD . /opt/openstates/openstates
WORKDIR /opt/openstates/openstates/

RUN set -ex \
    && pip install poetry \
    && poetry install

ENTRYPOINT ["/opt/openstates/openstates/pupa-scrape.sh"]
