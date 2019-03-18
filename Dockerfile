FROM python:3.7-slim-stretch

RUN pip install pipenv

COPY Pipfile Pipfile.lock /usr/src/stickybot/

WORKDIR /usr/src/stickybot

RUN pipenv install --system --deploy

COPY stickybot.py /usr/src/stickybot/

WORKDIR /stickybot

ENTRYPOINT [ "python", "/usr/src/stickybot/stickybot.py" ]
