from math import log
from heapq import heappush, heappop, nlargest
from collections import defaultdict

from init import show_summaries, get_and_update, initialize, read_data, add_tweets_to_graph
from score import get_score, get_expanded_keywords
import init as g
import frequency

def build_summary(starting_summary, parent_keywords=[]):

    partial_summary = (
        list(starting_summary),  # summary until this point
        0,                       # score until this point
        list(starting_summary)   # starting summary
    )

    partial_summaries = []
    heappush(partial_summaries, (-partial_summary[1], partial_summary))
    completed_summaries = []

    while partial_summaries:

        # generate potential summaries
        # expand them and keep the best ones
        _, (summary, summary_score, keywords) = heappop(partial_summaries)

        # add words to summary
        add_forward = g.ng.get((summary[-2], summary[-1]), {}).keys()
        add_reverse = g.ing.get((summary[0], summary[1]), {}).keys()

        # compute score for possible next moves 
        # also updates ng
        previous_bigram = tuple(summary[-2:])
        next_options = [
            (
                summary + list(bigr)[1:], 
                get_score(
                    summary, 
                    bigr, 
                    get_and_update(3, None, previous_bigram + (bigr[1],), g.ts), 
                    previous_bigram,
                    1,
                    list(keywords) + list(parent_keywords)
                ),
                bigr[1]
            )
            for bigr in add_forward
        ]

        # repeat for reverse links (not elegant, refactor?)
        previous_bigram = tuple(summary[:2])
        next_options += [
            (
                list(bigr)[:1] + summary, 
                get_score(
                    summary, 
                    bigr, 
                    get_and_update(3, None, (bigr[0],) + previous_bigram, g.ts), 
                    previous_bigram,
                    2,
                    list(keywords) + list(parent_keywords)
                ),
                bigr[0]
            )
            for bigr in add_reverse
        ]

        next_options = nlargest(5, next_options, key=lambda x: x[1])

        for next in next_options:
            summary, score = (
                    next[0], 
                    summary_score + next[1]
            )

            
            if summary[-1] == '_E' and summary[0] == '_S' and len(summary) > 8:
                # this summary looks good, we keep it
                # update penalties
                for w in summary:
                    g.penalty[w] += 1
                print score
                return summary

            elif (summary[-1] == '_E' and summary[0] == '_S'):
                # this summary is too short, discard it
                for w in summary:
                    g.penalty[w] += 1
            else:
                partial_summaries.append((-score, (summary, score, keywords)))

    # no summary could be built
    return None


#initialize('nycdataset', limit=100000)
#initialize('elclasico')

#g.prune(g.ts)

#for item in g.nw.items():
#    get_and_update(2, g.nw, item[0], g.ts)

def summarize_top(n=10):
    summaries = []
    g.penalty = defaultdict(lambda: 0)

    while len(summaries) < n:

        # select top starting bigrams
        # to use as seeds for the sentences
        start = max(
                g.nw.items(), 
                key=lambda x: x[1] - 10 * g.penalty[x[0][0]] - 10 * g.penalty[x[0][1]]
        )[0]
        print "start: %s" % list(start)

        summary = build_summary(start)

        if summary:
            summaries.append(summary)
            show_summaries([summary], keywords=start)
    
def summarize_partial(start, n=3):
    summaries = []
    g.penalty = defaultdict(lambda: 0)
    start = tuple(start)

    while len(summaries) < n:
        summary = build_summary(start)

        if summary:
            summaries.append(summary)
            show_summaries([summary], keywords=start)

def summarize_keywords(keywords, n=10, expand=True):
    summaries = []
    g.penalty = defaultdict(lambda: 0)
    keywords = set(keywords)
    if expand:
        try:
            keywords = get_expanded_keywords(keywords)
        except Exception, e:
            print e
            return

    while len(summaries) < n:

        # select top starting bigrams that contain one of the keywords
        # to use as seeds for the sentences
        # put bigrams containing '_S' or '_E' further down the list
        bigrams = [b for b in g.nw.items() if b[0][0] in keywords or b[0][1] in keywords]
        start = max(bigrams, key=lambda x: \
                x[1] - 10 * g.penalty[x[0][0]] - 10 * g.penalty[x[0][1]] - 
                (0 if x[0][0] != '_S' and x[0][1] != '_E' else 100))
        start = start[0]

        summary = build_summary(start, keywords)

        if summary:
            summaries.append(summary)
            show_summaries([summary], keywords=start)

def get_trending_topics_summary(n=10):
    words = frequency.word_frequency.keys()
    counts = {w: frequency.get_wf(w, g.ts) for w in words}
    counts = {w: fl for w, fl in counts.iteritems()
            if fl[1] > 0 and fl[1] > 3 * fl[0]}
    mcounts = [(w, log((fl[1] + 0.003) / (max(fl[0],1) + 0.003))) for w, fl in counts.iteritems()]
    mcounts.sort(key = lambda x: -x[1])

    summaries = []
    g.penalty = defaultdict(lambda: 0)
    i = 0
    while len(summaries) < n:
        keyword = mcounts[i][0]
        #keywords = get_expanded_keywords([keyword])
        keywords = set([keyword])
        print keywords

        # select top starting bigrams that contain one of the keywords
        # to use as seeds for the sentences
        bigrams = [b for b in g.nw.items() if b[0][0] in keywords or b[0][1] in keywords]
        start = max(
                bigrams, 
                key=lambda x: x[1] - 10 * g.penalty[x[0][0]] - 10 * g.penalty[x[0][1]]
        )[0]

        summary = build_summary(start)

        if summary:
            summaries.append(summary)
            show_summaries([summary], keywords=start)
        
        i += 1

import time
import simplejson as json

start_ts = 1383516000 + 9 * 3600
day = 6
tweets = read_data('nycdata2014', ts_limit=[
        start_ts + day * 86400, 
        start_ts + (day + 1) * 86400])

def event_tweet(tweet, keywords):
    for kw in keywords:
        if kw in tweet['text']:
            return 1
    return 0

# these are keywords representing the events to be summarized
# the code generating them is not included
# (if interested in it, please let me know)
event_keywords = [
    {
        1: [u'packers', u'rodgers', u'bears'], 
        2: [u'duty', u'release', u'midnight', u'ghost', u'code'], 
        3: [u'safe', u'ccsu'], 
        4: [u'shoot', u'gsp', u'mall', u'plaza'], 
        5: [u'report'], 
        6: [u'incognito'], 
        7: [u'vote'], 
        8: [u'freezing']
    }, {
        1: [u'duty', u'ghost', u'code'], 
        2: [u'album', u'mmlp2', u'eminem'], 
        3: [u'5th'], 
        4: [u'mayor', u'crack'], 
        5: [u'election', u'elections', u'christie'], 
        6: [u'major'], 
        7: [u'cold'], 
        8: [u'bruins'], 
        9: [u'knicks']}, 
    {
        1: [u'sunset', u'sky'], 
        2: [u'rangers'], 
        3: [u'voted', u'vote', u'votes', u'artist'], 
        4: [u'election', u'mayor'], 
        5: [u'taylor', u'cma', u'cmas', u'music', u'awards', u'country', u'swift'], 
        6: [u'luke', u'bryan'], 
        7: [u'performance', u'cmaaward'], 
        8: [u'george'], 
        9: [u'carrie', u'underwood'], 
        10: [u'blake', u'miranda'], 
        11: [u'tim'], 
        12: [u'hayes'], 
        13: [u'wcw'], 
        14: [u'horror', u'american'], 
        15: [u'ahscoven']
    }, {
        1: [u'lakers'], 
        2: [u'blake'], 
        3: [u'oregon', u'stanford'], 
        4: [u'redskins', u'httr', u'vikes'], 
        5: [u'voted', u'vote', u'votes', u'artist'], 
        6: [u'scandal'], 
        7: [u'glee'], 
        8: [u'thor']
    }, {
        1: [u'emazing', u'bieber'], 
        2: [u'voteaustinmahone'], 
        3: [u'maryland', u'uconn'], 
        4: [u'basketball'], 
        5: [u'snow', u'snowing'], 
        6: [u'thor']
    }, {
        1: [u'emazing', u'bieber', u'justin'], 
        5: [u'alabama', u'lsu', u'bama'], 
        6: [u'missuniverse2013'], 
        7: [u'universe'], 
        8: [u'celtics', u'green', u'jeff'], 
    }, {
        1: [u'veteranjob', u'hospital', u'starbucks', u'barista'], 
        2: [u'miley', u'emas',u'ema', u'cyrus'], 
        3: [u'eminem'], 
        4: [u'exo', u'justin', u'emazing', u'direction', u'bieber'], 
        5: [u'voted', u'vote', u'votes', u'voteaustinmahone', u'austin'], 
        6: [u'ravens', u'bengals'], 
        7: [u'packers', u'qb', u'eagles'], 
        8: [u'giants', u'raiders'], 
        9: [u'colts'], 
        10: [u'veteran', u'veterans'], 
        11: [u'governor', u'thewalkingdead'], 
        12: [u'episode', u'dead'], 
        13: [u'arsenal'], 
    }]

event_keywords = event_keywords[day]
event_cut_points = {}

batch_size = 5000

for key, keywords in event_keywords.iteritems():
    apps = [event_tweet(t, keywords) for t in tweets]
    max_count = 0
    max_ind = 0
    for i in range(len(tweets) / batch_size + 1):
        s = sum(apps[(i-1) * batch_size: i * batch_size])
        if s > max_count:
            max_count = s
            max_ind = i
    if max_ind not in event_cut_points:
        event_cut_points[max_ind] = []
    event_cut_points[max_ind].append(key)

initialize(tweets[:batch_size])

for i in range(1, len(tweets) / batch_size + 1):
    chunk_tweets = tweets[(i-1) * batch_size: i * batch_size]

    if i == 1:
        initialize(chunk_tweets)
    else:
        add_tweets_to_graph(chunk_tweets)

    if i in event_cut_points:
        g.prune(g.ts)
        for item in g.nw.items():
            get_and_update(2, g.nw, item[0], g.ts)

        for kw_id in event_cut_points[i]:
            keyword_set = event_keywords[kw_id]
            print keyword_set
            runtime = time.time()
            summarize_keywords(keyword_set, n=1)
            runtime = time.time() - runtime
            print '(%s)' % runtime
            print '----------------------------'
