FROM        sunlightlabs/billy:latest
MAINTAINER  Paul R. Tagliamonte <paultag@sunlightfoundation.com>

ENV DEBIAN_FRONTEND noninteractive

RUN mkdir -p /opt/sunlightfoundation.com/
ADD . /opt/sunlightfoundation.com/openstates/

# Handle interactive part of MySQL server installation
RUN echo mysql-server mysql-server/root_password password nicetry | debconf-set-selections
RUN echo mysql-server mysql-server/root_password_again password nicetry | debconf-set-selections

# CA requires MySQL (python-dev, mysql-server, libmysqlclient-dev)
# NM and NJ require mdbtools
# KS requires Abiword
RUN apt-get clean && apt-get update && apt-get -y upgrade && apt-get install -y \
    poppler-utils \
    s3cmd \
    mongodb-clients \
    locales-all \
    python-dev \
    mysql-server \
    libmysqlclient-dev \
    mdbtools \
    abiword

RUN pip install -r /opt/sunlightfoundation.com/openstates/requirements.txt
RUN pip install -e /opt/sunlightfoundation.com/openstates/

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN echo "/opt/sunlightfoundation.com/openstates/openstates/" > /usr/lib/python2.7/dist-packages/openstates.pth
