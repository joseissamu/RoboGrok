FROM nginx:stable
LABEL maintainer 'ITA Junior'

ARG NBOTS=3
ENV NBOTS=${NBOTS}

RUN apt update && \
    apt install -y python3 python3-pip 

RUN pip3 install --break-system-packages jinja2

WORKDIR /app

RUN mkdir -p /nginx_template

COPY default.conf.j2 /app/nginx_template/default.conf.j2
COPY setup.py .
COPY /html/*.html /usr/share/nginx/html/

RUN python3 /app/setup.py

EXPOSE 80