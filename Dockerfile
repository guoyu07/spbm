FROM python:3-alpine
MAINTAINER Thor K. Høgås <thor@roht.no>

# postgresql-dev required to build psycopg2 with pip
RUN apk --update add \
      ca-certificates \
      build-base \
      libxml2-dev \
      libxslt-dev \
      postgresql-dev \ 
		# required by pillow
		jpeg-dev \ 
		zlib-dev

# SAML: xmlsec is only available in the testing repo
RUN apk add --no-cache \
      --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ \
      --allow-untrusted \
      xmlsec-dev

RUN mkdir -p /usr/src/app
RUN mkdir -p /usr/src/static
WORKDIR /usr/src/app


# Install wheel to speed things up
RUN pip install wheel

# We use gunicorn
RUN pip install gunicorn

# handle that saml-stuff first because it takes very long to install (compile)
#COPY src/requirements_saml.txt /usr/src/app/
#RUN pip install --no-cache-dir -r requirements_saml.txt

COPY requirements.txt /usr/src/app/
RUN LIBRARY_PATH=/lib:/usr/lib /bin/sh -c "pip install --no-cache-dir -r requirements.txt"

COPY . /usr/src/app
COPY utils/scripts/container/start.sh /start.sh
#COPY utils/scripts/container/gunicorn.conf /gunicorn.conf

EXPOSE 8080 8080
CMD ["/start.sh"]
