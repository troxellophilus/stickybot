FROM python:3.6-slim-stretch

RUN pip install "praw>=5.3.0,<5.4" "requests>=2.18.4,<2.19"

COPY stickybot.py praw.ini config.json /root

WORKDIR /root

ENTRYPOINT [ "python", "stickybot.py" ]
