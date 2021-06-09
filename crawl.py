#!/usr/bin/env python

from bs4 import BeautifulSoup
import os
import pickle
import requests
import subprocess

TARGETS = ['ui', 'chrome/browser/ui', 'chrome/browser/about_flags.cc']
DRY_RUN = False
MESSAGE_TOKEN = ''

COMMITS = {}
NEW_COMMITS = {}

class Commit(object):
    def __init__(self, sha, target, title):
        self.sha = sha
        self.targets = [target]
        self.title = title
        self.link = 'https://chromium.googlesource.com/chromium/src/+/{}'.format(sha)

    def add_target(self, target):
        self.targets.append(target)



if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.realpath(__file__))

    token_path = os.path.join(current_dir, "message.token")
    if os.path.exists(token_path):
        with open(token_path, 'r') as file:
            MESSAGE_TOKEN = file.read().strip()

    pickle_path = os.path.join(current_dir, "commits.pickle")

    if os.path.exists(pickle_path) and os.path.getsize(pickle_path) > 0:
        with open(pickle_path, 'rb') as file:
              COMMITS = pickle.load(file)


    for target in TARGETS:
        url = 'https://chromium.googlesource.com/chromium/src/+log/main/{}'.format(target)
        response = requests.get(url)

        if response.status_code == 200:
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('li.CommitLog-item')
            for item in items:
                sha = item.select_one('.u-sha1').get_text()
                if sha in COMMITS:
                    continue

                if sha not in NEW_COMMITS:
                    title = item.select_one(':nth-child(2)').get_text()
                    NEW_COMMITS[sha] = Commit(sha, target, title)
                else:
                    NEW_COMMITS[sha].add_target(target)
        else:
            print(response.status_code)

    message = "# Daily reports for Desktop folks\n"
    for sha in NEW_COMMITS:
        commit = NEW_COMMITS[sha]
        message += "### {}\n".format(commit.title)
        message += "* Affected: {}\n".format(", ".join(commit.targets))
        message += "* {}\n\n".format(commit.link)
    else:
        message += "* Nothing has been commited today :)"

    if DRY_RUN:
        print(message)
    else:
        subprocess.check_output(["curl", "-v", "-X", "POST", "-H", "Authorization: Bearer " + MESSAGE_TOKEN,
                                                         "-F", "message=" + message, "https://notify-api.line.me/api/notify"]);

    COMMITS.update(NEW_COMMITS)

    with open(pickle_path, 'wb') as file:
        pickle.dump(COMMITS, file)

    exit(0)


