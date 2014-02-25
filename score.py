from math import log, sqrt

from init import get_and_update
import init as g

small = pow(10,-100) # to avoid dividing by zero or doing log(0)
kw_correl_th = 0.4

def get_kw_correl(w1, w2):
    cm = get_and_update(4, None, (w1, w2), g.ts) + get_and_update(4, None, (w2, w1), g.ts)
    correl = cm / (small + sqrt(
            get_and_update(1, g.ww, w1, g.ts) * \
            get_and_update(1, g.ww, w2, g.ts)
    ))
    return correl

def get_expanded_keywords(keywords):
    expanded_keywords = set([])
    keywords = set(keywords)
    for k1 in keywords:
        for k2 in g.cm[k1].iterkeys():
            if k2 not in ('_S', '_E') and get_kw_correl(k1, k2) >= kw_correl_th:
                expanded_keywords.add(k2)
    return keywords.union(expanded_keywords)

def get_correl(words, word2, case):
    #TODO: do average here
    #(it doesn't matter in my usecase)
    if not words:
        return 1
    correl = 0
    for i in range(len(words)):
        word1 = words[i]
        word_pair = (word1, word2) if case == 1 else (word2, word1)
        try:
            correl += log(
                small + \
                (
                    get_and_update(4, None, word_pair, g.ts) / \
                    (small + sqrt( \
                        get_and_update(1, g.ww, word_pair[0], g.ts) * \
                        get_and_update(1, g.ww, word_pair[1], g.ts))
                    )
                )
            )
        except Exception, e:
            print word_pair
            raise e
            
    return correl

def get_score(words, bigram, trigram_count, previous_bigram, case, keywords):
    # case is forward (1) or reverse (2), used because word corelation matrix is not symmetrical

    # new word
    new_word = bigram[2 - case]
    importance_score = log(g.nw[bigram])
    frequent_word_penalty = log(g.ww[new_word])
    cont_score = log(trigram_count * 1.0 / g.nw[previous_bigram])
    sentence_score = get_correl(words, new_word, case)
    cluster_score = get_correl(keywords, new_word, case)
    #penalty_score = g.penalty[new_word] # use this for generating multi-sentence summaries
    penalty_score = 0
    if new_word in words:
        #penalty_score += g.penalty[new_word] + 5
        penalty_score = 4
        
    final_score = importance_score * 2 + \
                cont_score * 3 + \
                sentence_score * 3 + \
                cluster_score * 10 - \
                25 * penalty_score - \
                frequent_word_penalty
                
    return final_score
