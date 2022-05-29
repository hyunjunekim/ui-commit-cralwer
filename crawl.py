#!/usr/bin/env python

from bs4 import BeautifulSoup
import os
import pickle
import requests
import subprocess
from datetime import date

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




class DirectorySwitcher(object):
    def __init__(self, origin, target):
        self.origin = origin
        self.target = target

    def __enter__(self):
        os.chdir(self.target)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.origin)


if __name__ == "__main__":
    current_dir = os.getcwd()
    script_dir = os.path.dirname(os.path.realpath(__file__))

    token_path = os.path.join(script_dir, "message.token")
    if os.path.exists(token_path):
        with open(token_path, 'r') as file:
            MESSAGE_TOKEN = file.read().strip()

    pickle_path = os.path.join(script_dir, "commits.pickle")

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
                    anchor_elements = item.select('a');
                    title = anchor_elements[1].get_text()
                    NEW_COMMITS[sha] = Commit(sha, target, title)
                else:
                    NEW_COMMITS[sha].add_target(target)
        else:
            print(response.status_code)

    today = date.today().strftime("%Y-%m-%d")
    markdown = "# Daily reports for Desktop folks\n"
    markdown += "## {}\n".format(today);
    if NEW_COMMITS:
        for sha in NEW_COMMITS:
            commit = NEW_COMMITS[sha]
            markdown += "### {}\n".format(commit.title)
            markdown += "* Affected: {}\n".format(", ".join(commit.targets))
            markdown += "* {}\n\n".format(commit.link)
    else:
        markdown += "* Nothing has been commited today :)\n"

    markdown = markdown.replace("`", "\\`");

    page_path = os.path.join(script_dir, "reports/{}.html".format(today))

    with open(page_path, 'w') as page:
        page_template = '''<!doctype html>
        <html>
        <head>
          <meta charset="utf-8"/>
            <title>Marked in the browser</title>
            </head>
            <body>
              <div id="content"></div>
              <script src="https://cdn.jsdelivr.net/npm/marked@3.0.8/marked.min.js"></script>
              <script>
                 document.getElementById("content").innerHTML = marked.parse(`{}`);
              </script>
            </body>
        </html>'''
        page.write(page_template.format(markdown))

    COMMITS.update(NEW_COMMITS)

    with open(pickle_path, 'wb') as file:
        pickle.dump(COMMITS, file)

    with DirectorySwitcher(current_dir, script_dir):
        try:
            subprocess.check_output(["git", "add", "reports"])
            subprocess.check_output(["git", "add", "commits.pickle"])
            subprocess.check_output(["git", "commit", "-m", "'Reports on {}'".format(today)])
            subprocess.check_output(["git", "push", "origin", "main"])
        except:
            pass


    message = "# Daily reports for Desktop folks\n"
    if NEW_COMMITS:
        message += "* New commits: {}\n".format(len(NEW_COMMITS))
    else:
        message += "* There's no commit today :)\n"
    message += "https://hyunjunekim.github.io/ui-commit-cralwer/reports/{}.html".format(today)

    if DRY_RUN:
        print(markdown)
    else:
        subprocess.check_output(["curl", "-v", "-X", "POST", "-H", "Authorization: Bearer " + MESSAGE_TOKEN,
                                 "-F", "message=" + message, "https://notify-api.line.me/api/notify"]);


    exit(0)


