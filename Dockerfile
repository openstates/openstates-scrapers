FROM        sunlightlabs/billy:latest
MAINTAINER  Sunlight Labs <labs-contact@sunlightfoundation.com>

ARG DEBIAN_FRONTEND=noninteractive

# CA requires MySQL (python-dev, mysql-server, libmysqlclient-dev) and utilities (wget, unzip)
# NM and NJ require mdbtools
# KS requires Abiword
# NH requires FreeTDS
RUN apt-get clean \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
        locales \
        python-dev \
        libssl-dev \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        poppler-utils \
        s3cmd \
        mongodb-clients \
        mysql-server \
        libmysqlclient-dev \
        freetds-dev \
        mdbtools \
        abiword \
        curl \
        wget \
        unzip

RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=C.UTF-8

ENV PROJECT_PATH="/srv/openstates-web/"
RUN mkdir -p ${PROJECT_PATH}
ADD . ${PROJECT_PATH}
RUN echo "${PROJECT_PATH}/openstates/" > /usr/lib/python2.7/dist-packages/openstates.pth

RUN pip install -U -r ${PROJECT_PATH}/requirements.txt
RUN pip install -e ${PROJECT_PATH}
