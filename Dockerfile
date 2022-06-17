FROM python:3.9-slim
LABEL maintainer="James Turk <dev@jamesturk.net>"

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING='utf-8' LANG='C.UTF-8'

RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
      curl \
      wget \
      unzip \
      mdbtools \
      libpq5 \
      libgdal28 \
      build-essential \
      git \
      libssl-dev \
      libffi-dev \
      freetds-dev \
      libxml2-dev \
      libxslt-dev \
      libyaml-dev \
      poppler-utils \
      libpq-dev \
      libgdal-dev \
      libgeos-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ADD . /opt/openstates/openstates
WORKDIR /opt/openstates/openstates/
ENV PYTHONPATH=./scrapers

# the last step cleans out temporarily downloaded artifacts for poetry, shrinking our build
RUN pip --no-cache-dir --disable-pip-version-check install poetry \
    && poetry install \
    && rm -r /root/.cache/pypoetry/cache /root/.cache/pypoetry/artifacts/ \
    && apt-get remove -y -qq \
      build-essential \
      git \
      libpq-dev \
    && apt-get autoremove -y -qq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["poetry", "run", "os-update"]
