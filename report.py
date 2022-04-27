import requests
import sys
import subprocess
import datetime
import re

def parse_time(time_str):
    # time_str = '2016-12-04T21:16:31Z'
    return datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")

# Try to get token from git config --global user.ghtoken
def gh_token(args):
    if len(args) >= 3:
        token = args[2]
    else:
        token = subprocess.run(["git", "config", "--global", "--get", "user.ghtoken"], stdout=subprocess.DEVNULL)
    if len(args) >=2:
        user = args[1]
    else:
        user = "sanket1729"
    # get from config assuming bitcoin-maintainer tools
    return (user, token)

# Sadly no support for events after some time
def page_events(user, token, page):
    headers = {'Accept': 'application/vnd.github.v3+json'}
    url = "https://api.github.com/users/sanket1729/events"
    params = {
        'per_page': 100,
        'page': page,
    }
    response = requests.get(url, headers=headers, auth=(user, token), params=params)
    return response.json()

class Event:
    def __init__(self):
        self.repo = ""
        self.act_type = ""
        self.title = ""
        self.time = ""

    def __eq__(self, other):
        if isinstance(other, Event):
            return ((self.repo == other.repo) and (self.title == other.title))
        else:
            return False
    def __ne__(self, other):
        return (not self.__eq__(other))

    def __repr__(self):
        return ('{:25s} {:35s} {:75s} '.format(self.act_type[:25], self.repo[:35], self.title[:75]))

    def __hash__(self):
        return hash(self.__repr__())


'''
CommitCommentEvent
CreateEvent
DeleteEvent
ForkEvent
GollumEvent
IssueCommentEvent
IssuesEvent
MemberEvent !
PublicEvent
PullRequestEvent
PullRequestReviewEvent
PullRequestReviewCommentEvent
PullRequestReviewThreadEvent
PushEvent
ReleaseEvent
SponsorshipEvent
WatchEvent
'''

def gen_report(curr_report, events, start):
    for event in events:
        created = parse_time(event["created_at"])
        if created > start:
            e = Event()
            e.repo = event["repo"]["name"]
            e.act_type = event["type"]
            if e.act_type == "CreateEvent" or e.act_type == "ForkEvent" or e.act_type == "GollumEvent"\
                or e.act_type == "WatchEvent":
                e.title = "New Repo of interest"
            elif e.act_type == "PushEvent":
                e.title = event["payload"]["commits"][0]["message"]
            else:
                if "pull_request" in event["payload"]:
                    e.title = event["payload"]["pull_request"]["title"]
                elif "issue" in event["payload"]:
                        e.title = event["payload"]["issue"]["title"]
                else:
                    print("ignored some event at:", e.repo)
            e.time = event["created_at"]
            e.title = e.title.replace("\n", " ")
            curr_report.add(e)
    return curr_report

def print_report(events):
    events = list(events)
    events = sorted(events, key=lambda e: e.repo)
    print("_"*125)
    print('{:25s} {:35s} {:75s} '.format("Action","Repo","Title"))
    prev_event = None
    for e in events:
        if prev_event is None or e.repo != prev_event.repo:
            print("_"*125)
        print(e)
        prev_event = e
    print("_"*125)

def get_new_page_report(curr_report, user, token, page):
    events = page_events(user, token, page)
    duration = datetime.timedelta(days = 7, hours = 1)
    start = datetime.datetime.now() - duration
    new_page_report = gen_report(curr_report, events, start)
    return new_page_report

if __name__ == "__main__":
    (user, token) = gh_token(sys.argv)
    page = 1
    curr_report = set()
    curr_report = get_new_page_report(curr_report, user, token, page)
    while True:
        page = page + 1
        prev_len = len(curr_report)
        curr_report = get_new_page_report(curr_report, user, token, page)
        if prev_len == len(curr_report):
            break
    print_report(curr_report)
    # Figure out all interesting events