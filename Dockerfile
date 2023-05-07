FROM python:3.9.12

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt /requirements.txt

RUN pip install --upgrade pip && \
    pip install pip-tools && \
    pip install -r /requirements.txt

RUN mkdir /app
COPY . /app
WORKDIR /app

RUN adduser --disabled-password --no-create-home django
USER django

CMD ["uwsgi", "--socket", ":9000", "--workers", "4", "--master", "--enable-threads", "--module", "app.wsgi"]
