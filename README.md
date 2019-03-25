# Sticky Bot

Automatically sticky Reddit posts from users based on rules.

## Why?

On /r/Dodgers, we have a tradition of community members posting the daily discussion threads rather than a bot. This allows the community to offer discussion topics for the day and make funny/witty titles. StickyBot ensures these daily discussion threads are stickied in a timely manner according to specific rules.

## Getting Started

Create a praw.ini with your reddit api credentials (follow PRAW's requirements). Use the bot name "stickybot".

Create a configuration JSON file with a subreddit and rules for Sticky Bot. See Rule Attributes below for all attributes.

```json
{
    "subreddit": "subreddit_name",
    "rules": [
        {
            "label": "Example",
            "pattern": "daily[ -]discussion thread"
        }
    ]
}
```

The provided Pipfile.lock can be used to retrieve stable dependencies for running StickyBot directly in Python.

```bash
pipenv install
pipenv run python stickybot.py /path/to/config.json
```

## Rule Attributes

The label and pattern attributes are required, but additional rule attributes are supported or defaulted for each rule.

* label - Label for logging purposes (required).
* pattern - RegEx pattern to match against submission titles (required).
* min_score - Minimum total comment + vote score to be stickied (default 5).
* min_karma - Minimum comment karma of submission author (default 50).
* max_age_hrs - Maximum age of submission (default 0.5).
* remove_age_hrs - Age at which a submission is unstickied (default 12).
* comment - Comment to post when stickying a submission (default none).
* sort_list - Ordered list of sorts to update through (default ['new', 'best']).
* sort_update_age_hrs - Amount of time between sort updates (default 4).

An example rules configuration from /r/Dodgers:
```json
{
    "subreddit": "Dodgers",
    "rules": [
        {
            "label": "GDT/ODT",
            "pattern": "gdt|odt|game[ -]day thread|off[ -]day thread",
            "min_score": 5,
            "min_karma": 50,
            "max_age_hrs": 6,
            "remove_age_hrs": 12,
            "comment": "This submission was automatically stickied as a Game Day or Off-Day Thread.",
            "sort_list": ["new", "best"],
            "sort_update_age_hrs": 4
        }
    ]
}
```
