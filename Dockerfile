FROM python:3.13-slim
LABEL maintainer="Jesse Mortenson <Jesse.Mortenson@sai360.com>"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING='utf-8'
ENV LANG='C.UTF-8'

RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
      ca-certificates \
      curl \
      wget \
      unzip \
      mdbtools \
      libpq5 \
      gdal-bin \
      git \
      libssl-dev \
      libffi-dev \
      freetds-dev \
      libxml2-dev \
      libxslt-dev \
      libyaml-dev \
      poppler-utils \
      libgdal-dev \
      libgeos-dev \
      gnupg \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*
RUN pip --no-cache-dir --disable-pip-version-check install crcmod
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

# venv lives outside the workdir so docker-compose's source mount doesn't hide it
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_NO_CACHE=1
ENV PATH="/opt/venv/bin:$PATH"

ADD uv.lock /opt/openstates/openstates/
ADD pyproject.toml /opt/openstates/openstates/
WORKDIR /opt/openstates/openstates/
ENV PYTHONPATH=./scrapers

# build deps are removed in the same layer they're installed in, or the image keeps them
RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
      build-essential \
      libpq-dev \
    && uv sync --frozen --no-dev \
    && apt-get remove -y -qq \
      build-essential \
      libpq-dev \
    && apt-get autoremove -y -qq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ADD . /opt/openstates/openstates/

ENV OPENSSL_CONF=/opt/openstates/openstates/openssl.cnf

# Entrypoint enables proper support of Google Application Credentials as env variable
COPY docker_entrypoint.sh /opt/openstates/entrypoint.sh
ENTRYPOINT ["/bin/bash", "/opt/openstates/entrypoint.sh"]
