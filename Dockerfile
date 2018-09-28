FROM python:3.7-slim-stretch

RUN pip install pipenv

COPY Pipfile Pipfile.lock /src/

WORKDIR /src

RUN pipenv install --system --deploy

COPY stickybot /src/stickybot/

WORKDIR /stickybot

ENTRYPOINT [ "python", "/src/stickybot/stickybot.py" ]
