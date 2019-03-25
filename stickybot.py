"""StickyBot for Reddit.

Moderator tool for Reddit; sticky Reddit threads with titles matching
configurable patterns.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
import re
from typing import List

import praw
import prawcore.exceptions
import requests


__version__ = '1.1.0'


def _hours_since(start):
    return float((datetime.utcnow() - start).total_seconds()) / 60 / 60


def get_stickies(subreddit):
    stickies = []
    try:
        stickies.append(subreddit.sticky(number=1))
    except prawcore.exceptions.NotFound:
        pass
    try:
        stickies.append(subreddit.sticky(number=2))
    except prawcore.exceptions.NotFound:
        pass
    return stickies


@dataclass
class Rule(object):
    """Rule for lifecycling existing stickies and stickying new submissions."""

    label: str
    pattern: str
    min_score: int = 5
    min_karma: int = 50
    max_age_hrs: float = 0.5
    remove_age_hrs: float = 12
    comment: str = None
    sort_list: List[str] = ('new', 'best')
    sort_update_age_hrs: float = 4
    flair_id: str = None

    def check(self, submission: praw.models.Submission):
        """Check if a submission should be handled by this Rule."""
        pat = re.compile(self.pattern.lower())
        return bool(pat.search(submission.title.lower()))

    def apply(self, submission: praw.models.Submission):
        """Determine if a submission is eligible to be stickied for this Rule."""
        if not self.check(submission):
            return False

        created = datetime.utcfromtimestamp(submission.created_utc)
        if _hours_since(created) > self.max_age_hrs:
            return False

        user_karma = submission.author.comment_karma
        if user_karma < self.min_karma:
            submission.subreddit.message("[StickyBot] User Comment Karma Below Threshold", f"[This submission]({submission.permalink}) is eligible for sticky according to rule '{self.label}' but the user's comment karma is below the rule's threshold of {self.min_karma}. Please approve and manually sticky the submission if it is permissible.")
            submission.mod.remove()
            comment = submission.reply("Your submission is pending moderator approval due to your comment karma being below the threshold for this type of submission. Message the moderators if you have any questions.")
            comment.mod.distinguish()
            return False

        return True

    def lifecycle(self, sticky: praw.models.Submission):
        """Update an existing sticky according to this Rule."""
        created = datetime.utcfromtimestamp(sticky.created_utc)
        hours_since_created = _hours_since(created)

        if self.sort_list:
            sort_idx = min(int(hours_since_created // self.sort_update_age_hrs), len(self.sort_list) - 1)
            current_sort = sticky.suggested_sort or sticky.comment_sort
            new_sort = self.sort_list[sort_idx]

            if new_sort != current_sort:
                logging.info(f"Setting suggested sort from '{current_sort}' to '{new_sort}' for sticky '{sticky.fullname}'.")
                sticky.mod.suggested_sort(new_sort)

            if self.flair_id and not sticky.link_flair_template_id:
                sticky.flair.select(self.flair_id)

        if hours_since_created > self.remove_age_hrs:
            logging.info(f"Unstickying stale sticky '{sticky.fullname}'.")
            sticky.mod.sticky(False)
            return True

        return False


def _get_comment(reddit, submission):
    comments = reddit.user.me().comments.new(limit=100)
    relevant = list(filter(lambda c: c.submission.fullname == submission.fullname, comments))
    if relevant:
        return relevant[0]
    return None


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO)

    args = _parse_args()

    with open(args.config) as conf_fo:
        conf = json.load(conf_fo)

    reddit = praw.Reddit('stickybot')
    subreddit = reddit.subreddit(conf['subreddit'])
    logging.info(f"Running StickyBot against /r/{subreddit.display_name}.")

    stickies = get_stickies(subreddit)
    submissions = tuple(subreddit.new(limit=100))

    rules = [Rule(**r) for r in conf['rules']]
    for rule in rules:
        logging.info(f"Executing rule '{rule.label}'...")

        # Check current stickies for existing sticky matching rule.
        existing = filter(rule.check, stickies)
        if not all(map(rule.lifecycle, existing)):
            logging.info(f"Sticky already exists for rule '{rule.label}'.")
            continue

        # Identify eligible submissions according to this rule.
        eligible = list(filter(rule.apply, submissions))
        if not eligible:
            logging.info(f"No eligible submissions found for rule.")
            continue

        # Select the "best" submission from the eligible submissions.
        best = max(eligible, key=lambda s: s.score + s.num_comments)
        if best.score + best.num_comments < rule.min_score:
            logging.info(f"Best submission {best.fullname} for rule didn't meet combined score requirements, with score {best.score + best.num_comments}.")
            continue  # Don't sticky, let it marinate.

        best.mod.sticky()
        best.mod.suggested_sort(rule.sort_list[0])
        if rule.flair_id:
            best.flair.select(rule.flair_id)

        # Post comment to the submission if specified.
        if rule.comment and not _get_comment(reddit, best):
            reply = best.reply(rule.comment)
            reply.mod.distinguish()

        logging.info(f"Stickied submission {best.fullname}.")


if __name__ == '__main__':
    main()
