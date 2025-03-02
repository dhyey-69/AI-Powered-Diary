import nltk
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import sent_tokenize

nltk.download('punkt')

def tfidf_summary(text, num_sentences=2):
    sentences = sent_tokenize(text)
    if len(sentences) < num_sentences:
        return text

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(sentences)
    sentence_scores = np.sum(tfidf_matrix.toarray(), axis=1)
    top_sentence_indices = np.argsort(sentence_scores)[-num_sentences:]
    top_sentence_indices.sort()

    summary = ' '.join([sentences[i] for i in top_sentence_indices])
    return summary
