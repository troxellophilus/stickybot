# Sticky Bot

Automatically sticky Reddit posts from users based on rules.

## Why?

On /r/Dodgers, we have a tradition of community members posting the daily discussion threads rather than a bot. This allows the community to offer discussion topics for the day and make funny/witty titles. StickyBot ensures these daily discussion threads are stickied in a timely manner according to specific rules.

## Getting Started

Create a praw.ini with your reddit api credentials (follow PRAW's requirements). Use the bot name "stickybot".

Create a configuration JSON file with rules for Sticky Bot.

An example rules configuration from /r/Dodgers:
```json
{
    "subreddit": "Dodgers",
    "rules": [
        {
            "label": "GDT/ODT",  # Label for logging purposes.
            "pattern": "gdt|odt|game[ -]day thread|off[ -]day thread",  # RegEx pattern to match against submission titles.
            "min_score": 5,  # Minimum total comment + vote score to be stickied.
            "min_karma": 50,  # Minimum comment karma of submission author.
            "max_age_hrs": 6,  # Maximum age of submission.
            "remove_age_hrs": 12,  # Age at which a submission is unstickied.
            "comment": "This submission was automatically stickied as a Game Day or Off-Day Thread.",  # Comment to post when stickying a submission.
            "sort_list": ["new", "best"],  # List of sorts to move through sequentially.
            "sort_update_age_hrs": 4  # Amount of time between sort updates.
        }
    ]
}
```

Build the docker container.

```bash
$ docker build -t stickybot/latest .
```

Run the docker container with the configuration and authentication praw.ini files. In this example, the files 'praw.ini' and 'config.json' would be in the /path/to/workdir directory.

```bash
$ docker run -v "/path/to/workdir:/stickybot" stickybot/latest config.json
```

## Running Without Docker

The provided Pipfile.lock can be used to retrieve stable dependencies for running StickyBot directly in Python.

```
$ pipenv install
$ pipenv run python stickybot/stickybot.py /path/to/config.json
```
