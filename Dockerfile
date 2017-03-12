FROM        openstates/billy:latest
MAINTAINER  James Turk <james@openstates.org>

ARG DEBIAN_FRONTEND=noninteractive

# add mongo 3.4 packages
RUN echo "deb http://repo.mongodb.org/apt/debian jessie/mongodb-org/3.4 main" > /etc/apt/sources.list.d/mongodb-org-3.4.list
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6

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
        mongodb-org-tools \
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
ADD . ${PROJECT_PATH}
RUN find ${PROJECT_PATH} -name '*.pyc' -delete
RUN echo "${PROJECT_PATH}/openstates/" > /usr/lib/python2.7/dist-packages/openstates.pth

RUN pip install -U pip
RUN /usr/local/bin/pip install -U -r ${PROJECT_PATH}/requirements.txt
RUN /usr/local/bin/pip install -e ${PROJECT_PATH}
