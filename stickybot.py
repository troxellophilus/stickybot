import datetime
import json
import logging
import os
import re

import praw
import prawcore.exceptions
import requests


logging.getLogger().setLevel(logging.INFO)


class StickyBot(object):

    def __init__(self, subreddit):
        self.subreddit_name = subreddit
        self.reddit = praw.Reddit('stickybot')
        self.subreddit = self.reddit.subreddit(self.subreddit_name)
        stickies = []
        try:
            stickies.append(self.subreddit.sticky(number=1))
        except prawcore.exceptions.NotFound:
            pass
        try:
            stickies.append(self.subreddit.sticky(number=2))
        except prawcore.exceptions.NotFound:
            pass
        self.stickied = tuple(stickies)
        self.submissions = tuple(self.subreddit.new(limit=10))

    def _check_stickied(self, pattern):
        for sticky in self.stickied:
            if re.match(pattern.lower(), sticky.title.lower()):
                time_diff = datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(sticky.created_utc)
                if time_diff.total_seconds() / 3600 < 12:
                    return True
        return False

    def run_pattern(self, pattern, min_score):
        logging.info(f"Running StickyBot for pattern {pattern}.")
        if self._check_stickied(pattern):
            logging.info(f"A recent sticky already exists for pattern.")
            return  # Already have a recent stickied post with that pattern.
        submissions = []
        for submission in self.submissions:
            if not re.match(pattern.lower(), submission.title.lower()):
                logging.debug(f"Submission {submission.fullname} didn't match pattern.")
                continue  # Didn't match, ignore.
            if submission.stickied:
                logging.info(f"Submission {submission.fullname} already stickied, stopping run for pattern.")
                return  # Already stickied; abort.
            logging.info(f"Found submission {submission.fullname} matching pattern.")
            submissions.append(submission)
        if not submissions:
            logging.info(f"No submissions found matching pattern")
            return
        best = max(submissions, key=lambda s: s.score + s.num_comments)
        if best.score + best.num_comments < min_score:
            logging.info(f"Best submission {submission.fullname} for pattern didn't meet combined score requirements, with score {best.score + best.num_comments}.")
            return  # Don't sticky, let it marinate.
        best.mod.sticky()
        logging.info(f"Stickied submission {submission.fullname}")

    def run(self, patterns, min_score=5):
        for pattern in patterns:
            self.run_pattern(pattern, min_score)


def main():
    root = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(root, 'config.json')) as conf_fo:
        conf = json.load(conf_fo)
    bot = StickyBot(conf['subreddit'])
    logging.info(f"Running StickyBot against /r/{bot.subreddit_name}.")
    bot.run(conf['patterns'], conf.get('min_score', 5))


if __name__ == '__main__':
    main()
