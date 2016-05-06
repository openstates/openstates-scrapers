FROM        sunlightlabs/billy:latest
MAINTAINER  Sunlight Labs <labs-contact@sunlightfoundation.com>

ARG DEBIAN_FRONTEND=noninteractive

# CA requires MySQL (python-dev, mysql-server, libmysqlclient-dev) and utilities (wget, unzip)
# NM and NJ require mdbtools
# KS requires Abiword
# NH requires FreeTDS
RUN apt-get update \
    && apt-get install -y \
        locales \
        poppler-utils \
        s3cmd \
        mongodb-clients \
        python-dev \
        mysql-server \
        libmysqlclient-dev \
        freetds-dev \
        mdbtools \
        abiword \
        wget \
        unzip \
    && apt-get autoremove \
    && apt-get clean

RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.utf-8

RUN mkdir -p /opt/sunlightfoundation.com/
ADD . /opt/sunlightfoundation.com/openstates/

RUN echo "/opt/sunlightfoundation.com/openstates/openstates/" > /usr/lib/python2.7/dist-packages/openstates.pth

RUN pip install -r /opt/sunlightfoundation.com/openstates/requirements.txt
RUN pip install -e /opt/sunlightfoundation.com/openstates/
