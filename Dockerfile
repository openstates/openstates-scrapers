FROM        sunlightlabs/billy:latest
MAINTAINER  Paul R. Tagliamonte <paultag@sunlightfoundation.com>

RUN mkdir -p /opt/sunlightfoundation.com/
ADD . /opt/sunlightfoundation.com/openstates/
RUN apt-get update && apt-get install -y \
    poppler-utils s3cmd mongodb-clients locales locales-all
RUN pip install xlrd lxml pytz feedparser suds
RUN pip install -e /opt/sunlightfoundation.com/openstates/

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN echo "/opt/sunlightfoundation.com/openstates/openstates/" > /usr/lib/python2.7/dist-packages/openstates.pth
