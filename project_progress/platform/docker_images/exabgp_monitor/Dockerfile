# syntax=docker/dockerfile:1.4

# how to build and run exabgp using docker (using the local copy)
# this dockerfile install exabgp in the container /opt

# docker build -t exabgp-main ./
# docker run -p 179:1790 --mount type=bind,source=`pwd`/etc/exabgp,target=/etc/exabgp exabgp-main version
# docker run -it exabgp-main version
# docker run -it exabgp-main etc/exabgp/exabgp.conf

# debug the build
# docker build --progress=plain --no-cache -t exabgp ./

FROM python:3-slim

# install deps
RUN apt-get update \
    && apt-get install -y net-tools iproute2 git dumb-init \
    && apt-get clean

RUN apt install -y traceroute iputils-ping gcc libffi-dev libssl-dev
RUN pip install --no-cache-dir --upgrade pip

# Add ExaBGP
ADD ./exabgp /opt/exabgp
RUN useradd -r exa \
    && mkdir /etc/exabgp \
    && mkfifo /run/exabgp.in \
    && mkfifo /run/exabgp.out \
    && chown exa /run/exabgp.in \
    && chown exa /run/exabgp.out \
    && chmod 600 /run/exabgp.in \
    && chmod 600 /run/exabgp.out

RUN echo "[exabgp.daemon]" > /opt/exabgp/etc/exabgp/exabgp.env \
    && echo "user = 'exa'" >> /opt/exabgp/etc/exabgp/exabgp.env

ENV PYTHONPATH=/opt/exabgp/src
ENV PATH=$PATH:/opt/exabgp/sbin/

COPY ./server /server

# RUN apk update && apk add --no-cache openssl-dev; libffi-dev py-openssl
RUN pip install --no-cache-dir -r /server/requirements.txt


ENV PATH /home/exabgp/bin:/home/exabgp/sbin:$PATH


ENTRYPOINT [ \
    "/usr/bin/dumb-init", "--",\ 
    "/opt/exabgp/sbin/exabgp" \
]
