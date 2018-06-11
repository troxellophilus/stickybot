"""StickyBot for Reddit.

Moderator tool for Reddit; sticky Reddit threads with titles matching
configurable patterns.
"""

from datetime import datetime
import json
import logging
import os
import re

import praw
import prawcore.exceptions
import requests


logging.getLogger().setLevel(logging.INFO)


def _seconds_since(start):
    return int((datetime.utcnow() - start).total_seconds())


def _check_pattern(pattern, title):
    pat = re.compile(pattern.lower())
    return bool(pat.search(title.lower()))


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

    def _check_stickied(self, pattern, max_age):
        for sticky in self.stickied:
            if _check_pattern(pattern, sticky.title):
                return sticky
        return None

    def _matching_submissions(self, pattern, max_age):
        for submission in self.submissions:
            if not _check_pattern(pattern, submission.title):
                logging.debug(f"Skipping submission {submission.fullname}: didn't match pattern.")
                continue  # Didn't match, ignore.

            created = datetime.utcfromtimestamp(submission.created_utc)
            if _seconds_since(created) > max_age:
                logging.debug(f"Skipping submission {submission.fullname}: older than {max_age} hours.")
                continue  # Too old, ignore.

            if len(self.stickied) == 2:
                if submission.created_utc < self.stickied[1].created_utc:
                    logging.debug(f"Skipping submission {submission.fullname}: older than existing bottom sticky.")
                    continue

            if submission.stickied:
                logging.info(f"Submission {submission.fullname} already stickied.")
                break  # Already stickied; abort.

            yield submission

    def _get_comment(self, submission):
        comments = self.reddit.user.me().comments.new(limit=100)
        relevant = list(filter(lambda c: c.submission.fullname == submission.fullname, comments))
        if relevant:
            return relevant[0]
        return None

    def _lifecycle(self, sticky, max_age, sorts, sort_wait):
        created = datetime.utcfromtimestamp(sticky.created_utc)
        seconds_since_created = _seconds_since(created)
        if sorts:
            supported_sorts = ('new', 'best', 'top', 'controversial', 'old', 'q&a')
            if not all(s in supported_sorts for s in sorts):
                logging.error(f"Sorts must be one of {supported_sorts}")
                raise ValueError(f"Sorts must be one of {supported_sorts}")
            sort_idx = min(seconds_since_created // sort_wait, len(sorts) - 1)
            current_sort = sticky.suggested_sort or sticky.comment_sort
            new_sort = sorts[sort_idx]
            if new_sort != current_sort:
                logging.info(f"Setting suggested sort from '{current_sort}' to '{new_sort}' for sticky '{sticky.fullname}'.")
                sticky.mod.suggested_sort(new_sort)
                comment = self._get_comment(sticky)
                body = f"{comment.body}  \n^(*Suggested sort updated at {datetime.utcnow().isoformat()}Z.*)"
                comment.edit(body)
        if seconds_since_created > max_age:
            logging.info(f"Unstickying stale sticky '{sticky.fullname}'.")
            sticky.mod.sticky(False)

    def run(self, pattern, min_score=5, max_age=12, comment=None, sorts=('new',), sort_wait=60):
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
            max_age (int): Max. post age in seconds for sticky/unsticky.
            comment (str): Optional comment to post after stickying.
            sort (list[str]): Sorts to set at sort_weight intervals.
            sort_wait (int): Time in seconds between each sort.
        """
        logging.info(f"Running StickyBot for pattern {pattern}.")
        existing = self._check_stickied(pattern, max_age)
        if existing:
            logging.info(f"A recent sticky already exists for pattern. Lifecycling existing sticky...")
            self._lifecycle(existing, max_age, sorts, sort_wait)
            return  # Already have a recent stickied post with that pattern.

        submissions = list(self._matching_submissions(pattern, max_age))
        if not submissions:
            logging.info(f"No new submissions found matching pattern.")
            return

        best = max(submissions, key=lambda s: s.score + s.num_comments)
        if best.score + best.num_comments < min_score:
            logging.info(f"Best submission {best.fullname} for pattern didn't meet combined score requirements, with score {best.score + best.num_comments}.")
            return  # Don't sticky, let it marinate.

        best.mod.sticky()
        best.mod.suggested_sort(sorts[0])

        if comment and not self._get_comment(best):
            reply = best.reply(comment)
            reply.mod.distinguish()
        logging.info(f"Stickied submission {best.fullname}")


def main():
    """Create and run a StickyBot according to a config file."""
    root = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(root, 'config.json')) as conf_fo:
        conf = json.load(conf_fo)
    bot = StickyBot(conf['subreddit'])
    logging.info(f"Running StickyBot against /r/{bot.subreddit_name}.")
    for sticky in conf['stickies']:
        bot.run(sticky['pattern'], sticky.get('min_score', 5), sticky.get('max_age', 12), sticky.get('comment'), sticky.get('sorts', ('new',)), sticky.get('sort_wait', 3600))


if __name__ == '__main__':
    main()
