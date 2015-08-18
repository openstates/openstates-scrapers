FROM        sunlightlabs/billy:latest
MAINTAINER  Paul R. Tagliamonte <paultag@sunlightfoundation.com>

RUN mkdir -p /opt/sunlightfoundation.com/
ADD . /opt/sunlightfoundation.com/openstates/

ENV DEBIAN_FRONTEND noninteractive
RUN echo mysql-server mysql-server/root_password password notasecret | debconf-set-selections
RUN echo mysql-server mysql-server/root_password_again password notasecret | debconf-set-selections
RUN apt-get update && apt-get install -y \
    poppler-utils s3cmd mongodb-clients locales locales-all python-dev mysql-server libmysqlclient-dev
RUN pip install -r /opt/sunlightfoundation.com/openstates/requirements.txt
RUN pip install -e /opt/sunlightfoundation.com/openstates/

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN echo "/opt/sunlightfoundation.com/openstates/openstates/" > /usr/lib/python2.7/dist-packages/openstates.pth
