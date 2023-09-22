FROM python:3-slim

# install deps
RUN apt-get update \
    && apt-get install -y dumb-init \
    && apt-get clean

# install debug tools
RUN apt-get install -y net-tools iproute2 \
    && apt-get clean
RUN apt install -y htop traceroute iputils-ping

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

COPY ./parser /parser

ENV PATH /home/exabgp/bin:/home/exabgp/sbin:$PATH

# ENTRYPOINT [ \
#     "/usr/bin/dumb-init", "--",\ 
#     "/opt/exabgp/sbin/exabgp" \
# ]
