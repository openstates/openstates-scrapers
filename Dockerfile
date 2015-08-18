FROM        sunlightlabs/billy:latest
MAINTAINER  Paul R. Tagliamonte <paultag@sunlightfoundation.com>

ENV DEBIAN_FRONTEND noninteractive

RUN mkdir -p /opt/sunlightfoundation.com/
ADD . /opt/sunlightfoundation.com/openstates/

RUN echo mysql-server mysql-server/root_password password nicetry | debconf-set-selections
RUN echo mysql-server mysql-server/root_password_again password nicetry | debconf-set-selections
RUN apt-get update && apt-get install -y \
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
