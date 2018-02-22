"""StickyBot for Reddit.

Moderator tool for Reddit; sticky Reddit threads with titles matching
configurable patterns.
"""

import datetime
import json
import logging
import os
import re

import praw
import prawcore.exceptions
import requests


logging.getLogger().setLevel(logging.INFO)


def _check_age(created_utc, max_age):
    created = datetime.datetime.fromtimestamp(created_utc)
    age = (datetime.datetime.utcnow() - created).total_seconds() / 3600
    return age < max_age


def _check_pattern(pattern, title):
    pat = re.compile(pattern.lower())
    return bool(pat.match(title.lower()))


class StickyBot(object):
    """Context object for running bot actions.

    Args:
        subreddit (str): Name of the subreddit to run against.
    """

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
        self.submissions = tuple(self.subreddit.new(limit=100))

    def _check_stickied(self, pattern):
        for sticky in self.stickied:
            if _check_pattern(pattern, sticky.title) and _check_age(sticky.created_utc, 12):
                return True
        return False

    def _matching_submissions(self, pattern):
        for submission in self.submissions:
            if not _check_pattern(pattern, submission.title):
                logging.debug(f"Skipping submission {submission.fullname}: didn't match pattern.")
                continue  # Didn't match, ignore.

            if not _check_age(submission.created_utc, 12):
                logging.debug(f"Skipping submission {submission.fullname}: older than 12 hours.")
                continue  # Too old, ignore.

            if submission.stickied:
                logging.info(f"Submission {submission.fullname} already stickied.")
                break  # Already stickied; abort.

            yield submission

    def run_pattern(self, pattern, min_score):
        """Run stickybot for a pattern.

        Sticky and set suggested sort to new a recent submission matching the
        pattern with the highest total activity score.

        No action is taken if:
            * No recent posts match the pattern.
            * The highest activity score submission does not meet the min_score
              threshold.
            * A recent post matching the pattern is already stickied.

        Args:
            pattern (str): Regex pattern to match against titles.
            min_score (int): Min. activity score threshold.
        """
        logging.info(f"Running StickyBot for pattern {pattern}.")
        if self._check_stickied(pattern):
            logging.info(f"A recent sticky already exists for pattern.")
            return  # Already have a recent stickied post with that pattern.

        submissions = list(self._matching_submissions(pattern))
        if not submissions:
            logging.info(f"No submissions found matching pattern")
            return

        best = max(submissions, key=lambda s: s.score + s.num_comments)
        if best.score + best.num_comments < min_score:
            logging.info(f"Best submission {best.fullname} for pattern didn't meet combined score requirements, with score {best.score + best.num_comments}.")
            return  # Don't sticky, let it marinate.

        best.mod.sticky()
        best.mod.suggested_sort('new')
        logging.info(f"Stickied submission {best.fullname}")

    def run(self, patterns, min_score=5):
        """Run stickybot against a list of patterns.

        Loop through a sequence of regex patterns, executing run_pattern
        against each pattern.

        Args:
            patterns (iter(str)): List of regex patterns to match against.
            min_score (int): Min. activity score threshold for stickying.
        """
        for pattern in patterns:
            self.run_pattern(pattern, min_score)


def main():
    """Create and run a StickyBot according to a config file."""
    root = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(root, 'config.json')) as conf_fo:
        conf = json.load(conf_fo)
    bot = StickyBot(conf['subreddit'])
    logging.info(f"Running StickyBot against /r/{bot.subreddit_name}.")
    bot.run(conf['patterns'], conf.get('min_score', 5))


if __name__ == '__main__':
    main()
