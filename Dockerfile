FROM alpine:3.7

RUN apk add --update python py-pip py-mysqldb
RUN pip install --upgrade pip

RUN mkdir /code
WORKDIR /code
COPY . .

RUN pip install py-mysqldb