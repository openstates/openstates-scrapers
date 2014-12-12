FROM        sunlightlabs/billy:latest
MAINTAINER  Paul R. Tagliamonte <paultag@sunlightfoundation.com>

RUN mkdir -p /opt/sunlightfoundation.com/
ADD . /opt/sunlightfoundation.com/openstates/
RUN pip install xlrd lxml pytz feedparser suds
RUN pip install -e /opt/sunlightfoundation.com/openstates/

RUN echo "/opt/sunlightfoundation.com/openstates/openstates/" > /usr/lib/python2.7/dist-packages/openstates.pth
