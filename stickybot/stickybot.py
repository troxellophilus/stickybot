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


logging.getLogger().setLevel(logging.INFO)


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

    label: str
    pattern: str
    min_score: int = 5
    min_karma: int = 50
    max_age_hrs: float = 30
    remove_age_hrs: float = 12
    comment: str
    sort_list: List[str] = ['new', 'best']
    sort_update_age_hrs: float = 4

    def sticky_filter(self, submission: praw.models.Submission):
        pat = re.compile(self.pattern.lower())
        if not pat.search(submission.title.lower()):
            return False
        return True

    def submission_filter(self, submission: praw.models.Submission):
        pat = re.compile(self.pattern.lower())
        if not pat.search(submission.title.lower()):
            return False

        created = datetime.utcfromtimestamp(submission.created_utc)
        if _hours_since(created) > self.max_age_hrs:
            return False

        user_karma = submission.author  # TODO: Filter by user karma.

        return True

    def lifecycle(self, sticky: praw.models.Submission):
        created = datetime.utcfromtimestamp(sticky.created_utc)
        hours_since_created = _hours_since(created)
        if self.sort_list:
            sort_idx = min(hours_since_created // self.sort_update_age_hrs, len(self.sort_list) - 1)
            current_sort = sticky.suggested_sort or sticky.comment_sort
            new_sort = self.sort_list[sort_idx]
            if new_sort != current_sort:
                logging.info(f"Setting suggested sort from '{current_sort}' to '{new_sort}' for sticky '{sticky.fullname}'.")
                sticky.mod.suggested_sort(new_sort)
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
    args = _parse_args()

    with open(args.config) as conf_fo:
        conf = json.load(conf_fo)

    reddit = praw.Reddit('stickybot')
    subreddit = reddit.subreddit(conf['subreddit'])
    logging.info(f"Running StickyBot against /r/{subreddit.name}.")

    stickies = get_stickies(subreddit)
    submissions = tuple(subreddit.new(limit=100))

    rules = [Rule(**r) for r in conf['rules']]
    for rule in rules:
        logging.info(f"Executing rule '{rule.label}'...")

        # Check current stickies for existing sticky matching rule.
        existing = filter(rule.sticky_filter, stickies)
        if not all(rule.lifecycle(s) for s in existing):
            logging.info(f"Sticky already exists for rule '{rule.label}'.")
            continue

        # Identify eligible submissions according to this rule.
        eligible = list(filter(rule.submission_filter, submissions))
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

        # Post comment to the submission if specified.
        if rule.comment and not _get_comment(reddit, best):
            reply = best.reply(rule.comment)
            reply.mod.distinguish()

        logging.info(f"Stickied submission {best.fullname}.")


if __name__ == '__main__':
    main()
