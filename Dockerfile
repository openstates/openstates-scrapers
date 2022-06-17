FROM python:3.9-slim
LABEL maintainer="James Turk <dev@jamesturk.net>"

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING='utf-8' LANG='C.UTF-8'

RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
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
      wget \
      unzip \
#     libcrypto1.1 \
      mdbtools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ADD . /opt/openstates/openstates
WORKDIR /opt/openstates/openstates/
ENV PYTHONPATH=./scrapers

# the last step cleans out temporarily downloaded artifacts for poetry, shrinking our build
RUN pip --no-cache-dir --disable-pip-version-check install poetry \
    && poetry install \
    && rm -r /root/.cache/pypoetry/cache /root/.cache/pypoetry/artifacts/

ENTRYPOINT ["poetry", "run", "os-update"]
