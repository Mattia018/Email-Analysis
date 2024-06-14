import spacy
import gensim
from gensim import corpora
from gensim.models import LdaModel
import re
from bertopic import BERTopic
from bertopic._utils import MyLogger
from transformers import AutoTokenizer,logging, BartForConditionalGeneration
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import plotly.express as px

logging.set_verbosity_error()


nlp = spacy.load("en_core_web_sm")
topic_model = BERTopic.load("MaartenGr/BERTopic_Wikipedia")
logger = MyLogger("ERROR")

def clean_text(text):
    # Rimuovi simboli non desiderati
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return cleaned_text

def extract_topics(text, num_words=4):
    # Pulizia del testo
    cleaned_text = clean_text(text)
    
    # Tokenizzazione e preprocessamento del testo pulito
    tokens = [token.text for token in nlp(cleaned_text) if not token.is_stop and not token.is_punct]
    
    # Creazione del dizionario e del corpus
    dictionary = corpora.Dictionary([tokens])
    corpus = [dictionary.doc2bow(tokens)]
    
    # Creazione del modello LDA
    lda_model = LdaModel(corpus, num_topics=1, id2word=dictionary, passes=10)
    
    # Estrazione dei topic
    topics = lda_model.print_topics(num_words=num_words)
    
    # Solo i termini senza i pesi
    topic_terms = topics[0][1]
    terms_only = ' '.join([term.split('*')[1].replace('"', '') for term in topic_terms.split(' + ')])
    
    return terms_only




def extract_ner(text):
   
    # Applica il modello SpaCy al testo
    doc = nlp(text)
    
    named_entities_set = set()
    for ent in doc.ents:
        # Escludi entità con tipo errato come "PERSON" per numeri di telefono
        if ent.label_ not in ['PHONE', 'EMAIL']:
            named_entities_set.add(f'{ent.text} ({ent.label_})')

    # Usa regex per trovare email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    for email in emails:
        named_entities_set.add(f'{email} (EMAIL)')

    # Usa regex per trovare numeri di telefono
    phone_pattern = r'\b(\d{3}[-.\s]??\d{3}[-.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-.\s]??\d{4}|\d{3}[-.\s]??\d{4})\b'
    phone_numbers = re.findall(phone_pattern, text)
    for number in phone_numbers:
        named_entities_set.add(f'{number} (PHONE)')

    # Converti il set in una stringa separata da virgole
    named_entities_str = ', '.join(named_entities_set)

    return named_entities_str



def topic_Bert(text):        
    
    topic_model.verbose = False
    topics, probs = topic_model.transform([text])
    topic = topics[0]        
    topic_label = topic_model.topic_labels_[topic]

    return topic_label


def summary_text_t5(text):
    
    model = BartForConditionalGeneration.from_pretrained("sshleifer/distilbart-xsum-12-1")
    tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-xsum-12-1")
    inputs = tokenizer([text], max_length=768, return_tensors="pt")
    summary_ids = model.generate(inputs["input_ids"], num_beams=3, min_length=10, max_length=40,do_sample=False)
    result= tokenizer.batch_decode(summary_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    summary_text = ' '.join(result)

    return summary_text



def sentiment_vader(text, pos_threshold=0.55, neg_threshold=-0.05):
    analyzer = SentimentIntensityAnalyzer()
    result = analyzer.polarity_scores(text)
    
    # Usa il punteggio 'compound' per determinare il sentiment principale
    compound_score = result['compound']
    if compound_score >= pos_threshold:
        main_sentiment = 'Positive'
    elif compound_score <= neg_threshold:
        main_sentiment = 'Negative'
    else:
        main_sentiment = 'Neutral'
    
    return main_sentiment



def plot_topic_frequencies_dash(topic_freq, top_n):
    topics = list(topic_freq.keys())[:top_n]
    frequencies = list(topic_freq.values())[:top_n]   
   
    fig = px.bar(
        x=frequencies,
        y=topics,
        orientation='h',
        color=frequencies,
        color_continuous_scale=[[0, 'gray'], [1, 'lightgray']],        
        labels={'x': 'Frequencies', 'y': 'Topics'}
    )

    fig.update_layout(
        plot_bgcolor='#343a40',  
        paper_bgcolor='#343a40',  
        font=dict(color='white'),  
        title=dict(font=dict(color='white')),  
        xaxis=dict(title=dict(font=dict(color='white')), tickfont=dict(color='white'), tickmode='linear',tick0=0,dtick=1),  
        yaxis=dict(
            title=dict(font=dict(color='white')), 
            tickfont=dict(color='white'),
            automargin=True
        ),
        margin=dict(l=150),  
        coloraxis_showscale=False,
        height=300 + 50 * top_n  
    )

    return fig

def plot_sentiment_counts(pos_sent, neu_sent, neg_sent):
    data = {
        'Sentiment': ['Positive', 'Neutral', 'Negative'],
        'Count': [pos_sent, neu_sent, neg_sent]        
    }
    
    colors = ['#f0f0f0', '#d9d9d9', '#bdbdbd']

    fig = px.bar(
        data,
        x='Sentiment',
        y='Count',
        color_discrete_sequence=colors,
        title='Sentiment Counts',
        labels={'Count': 'Count'}
    )

    fig.update_layout(
        plot_bgcolor='#343a40',  
        paper_bgcolor='#343a40',  
        font=dict(color='white'),  
        title=dict(font=dict(color='white')),  
        xaxis=dict(title=dict(font=dict(color='white')), tickfont=dict(color='white')),  
        yaxis=dict(
            title=dict(font=dict(color='white')), 
            tickfont=dict(color='white'), 
            type='log',
            showgrid=False
        ),    
        margin=dict(l=50, r=50, t=50, b=50),  
        showlegend=False
    )

    return fig



