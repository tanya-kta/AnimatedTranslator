FROM python:3.9.12

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mrdir /AnimatedTranslator

WORKDIR /AnimatedTranslator

COPY . /AnimatedTranslator/

RUN pip install --upgrade pip && pip install pip-tools && pip install -r requirements.txt