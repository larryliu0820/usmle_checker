FROM ubuntu:18.04
COPY . /app
RUN apt-get -y update
RUN apt-get install -y python3.7
RUN apt-get install -y python3-pip python3-virtualenv

RUN apt-get install -y firefox wget

RUN wget -P /app/ https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
RUN tar -C /app -xzvf /app/geckodriver-v0.24.0-linux64.tar.gz

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m virtualenv --python=/usr/bin/python3 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip3 install -r /app/requirements.txt 


