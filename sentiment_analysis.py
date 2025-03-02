from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def analyze_sentiment(entry_text):
    analyzer = SentimentIntensityAnalyzer()
    
    sentiment_scores = analyzer.polarity_scores(entry_text)
    
    compound_score = sentiment_scores['compound']
    
    if compound_score >= 0.05:
        return "Happy"
    elif compound_score <= -0.05:
        return "Sad"
    else:
        return "Neutral"

# print(analyze_sentiment("I just received some great news today! My project was accepted, and I'm so happy about it. I'm excited to see what happens next."))     
# print(analyze_sentiment("I woke up, went to work, had a regular lunch, and now I'm just resting. Nothing really special happened today."))     
# print(analyze_sentiment("It was a decent day. Not everything went perfectly, but I did manage to get a lot done. I'm feeling okay about it.."))     
