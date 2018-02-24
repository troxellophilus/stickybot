# Sticky Bot

Create a praw.ini with your reddit api credentials (follow PRAW's requirements). Use the bot name "stickybot".

Create a config.json with options for Sticky Bot.

```json
{
    "subreddit": "subreddit-name",
    "stickies": [
        {
            "pattern": "[A-z]Regex Pattern.+",
            "min_score": 1,
            "max_age": 8,
            "comment": "Optional comment to post and distinguish after stickying."
        },
        {
            "pattern": "[A-z]Another Pattern.+",
            "min_score": 1,
            "max_age": 16
        }
    ]
}
```

Build and run with Docker.

```bash
$ docker build -t stickybot/latest .
$ docker run stickybot/latest
```
