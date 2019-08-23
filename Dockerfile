FROM python:3-alpine

WORKDIR /opt

COPY . .

RUN python ./setup.py install

ENTRYPOINT ["docker-autocompose"]
