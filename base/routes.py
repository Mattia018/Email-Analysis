from base import app
from flask import render_template, redirect, url_for, flash, request, abort
from base.models import  User, Mails, MailAnalysisResult
from base.forms import RegisterForm, LoginForm, UploadForm
from base import db
from flask_login import login_user, logout_user, login_required, current_user
import pandas as pd
import spacy
from collections import Counter
import io
import re
import time
import os
from features.features import extract_ner, topic_Bert, sentiment_vader,summary_text_t5, plot_topic_frequencies_dash, plot_sentiment_counts


img = os.path.join('static', 'img')

@app.route('/')
@app.route('/home')
def home_page():
    img1= os.path.join(img, 'unoi.png')    
    return render_template('home.html', img1=img1)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard_page():

    form = UploadForm() 


    if request.method == "POST":
           
        if form.validate_on_submit():        
            file_data = form.file.data.read()            
            filename= Mails.query.filter_by(file_name=form.file_name.data).first()
            
            if filename is not None:
                if filename.file_name == form.file_name.data:
                    flash(f"File name already exist, Please try a different File Name", category='danger')
                    return redirect(url_for('dashboard_page'))

            if file_data is None:
                   flash(f"Please Upload a File", category='danger')
                   return redirect(url_for('dashboard_page')) 

            file_to_upload = Mails(file_name=form.file_name.data, file=file_data, owner=current_user.id)
            db.session.add(file_to_upload)
            db.session.commit()
            flash(f"File Upload successfully", category='success')
            return redirect(url_for('dashboard_page'))
        else:
            flash(f"Only csv or txt file are allowed !", category='danger')    
       
               

    owner_file_mail = Mails.query.filter_by(owner=current_user.id).all()

    if request.method == "GET":
       
        owner_file_mail = Mails.query.filter_by(owner=current_user.id).order_by(Mails.id.desc()).all()

        mails_analysis= MailAnalysisResult.query.filter_by(user_id=current_user.id)

        total_emails_analyzed = MailAnalysisResult.query.filter_by(user_id=current_user.id).count()
        if total_emails_analyzed is None:
            total_emails_analyzed = 0
        

        unique_senders_count = db.session.query(
                                db.func.count(db.func.distinct(MailAnalysisResult.mail_from))
                            ).join(Mails, MailAnalysisResult.file_id == Mails.id).filter(
                                Mails.owner == current_user.id
                            ).scalar()
        if unique_senders_count is None:
            unique_senders_count=0

        most_sender = db.session.query(
                                MailAnalysisResult.mail_from, 
                                db.func.count(MailAnalysisResult.id).label('email_count')
                            ).join(
                                Mails, MailAnalysisResult.file_id == Mails.id
                            ).filter(
                                Mails.owner == current_user.id
                            ).group_by(
                                MailAnalysisResult.mail_from
                            ).order_by(
                                db.desc('email_count')
                            ).all()
        
        if most_sender:
            top_sender = max(most_sender, key=lambda x: x[1])
            top_sender_email, top_sender_email_count = top_sender[0], top_sender[1]
        else:
            top_sender_email_count=0
            top_sender_email=0

        viewable_statuses = {mail.id: mail.viewable_status for mail in owner_file_mail}

        top_topics = db.session.query(MailAnalysisResult.mail_topic, db.func.count(MailAnalysisResult.mail_topic)) \
        .filter_by(user_id=current_user.id) \
        .group_by(MailAnalysisResult.mail_topic) \
        .order_by(db.func.count(MailAnalysisResult.mail_topic).desc()) \
        .limit(3) \
        .all()
    
        main_topic = top_topics if top_topics else []

        unique_topics_count = db.session.query(
            db.func.count(db.func.distinct(MailAnalysisResult.mail_topic))
            ).join(Mails, MailAnalysisResult.file_id == Mails.id).filter(
                Mails.owner == current_user.id
            ).scalar()

        top_topics = db.session.query(
        MailAnalysisResult.mail_topic,
                db.func.count(MailAnalysisResult.mail_topic)
            ).join(
                Mails, MailAnalysisResult.file_id == Mails.id
            ).filter(
                Mails.owner == current_user.id
            ).group_by(
                MailAnalysisResult.mail_topic
            ).order_by(
                db.func.count(MailAnalysisResult.mail_topic).desc()
            ).all()

        if top_topics:   
            topic_freq = {topic: freq for topic, freq in top_topics}
            graphJSON = plot_topic_frequencies_dash(topic_freq, 20)
            graphJSON = graphJSON.to_json()
        else:
            graphJSON=0

        # Conteggio dei sentimenti positivi per tutti i file_id dell'utente corrente
        positive_sentiment_count = MailAnalysisResult.query.join(Mails).filter(
            Mails.owner == current_user.id,
            MailAnalysisResult.mail_Sent == 'positive'
        ).count()
        pos_sent = positive_sentiment_count if positive_sentiment_count else 0

        # Conteggio dei sentimenti neutri per tutti i file_id dell'utente corrente
        neutral_sentiment_count = MailAnalysisResult.query.join(Mails).filter(
            Mails.owner == current_user.id,
            MailAnalysisResult.mail_Sent == 'neutral'
        ).count()
        neu_sent = neutral_sentiment_count if neutral_sentiment_count else 0

        # Conteggio dei sentimenti negativi per tutti i file_id dell'utente corrente
        negative_sentiment_count = MailAnalysisResult.query.join(Mails).filter(
            Mails.owner == current_user.id,
            MailAnalysisResult.mail_Sent == 'negative'
        ).count()
        neg_sent = negative_sentiment_count if negative_sentiment_count else 0

        if pos_sent:   
            
            graphJSON_Sent = plot_sentiment_counts(pos_sent, neu_sent, neg_sent)
            graphJSON_Sent = graphJSON_Sent.to_json()
        else:
            graphJSON_Sent=0
        
    return render_template('dashboard.html',
                            form=form,
                            file_mail=owner_file_mail,
                            mail_results=mails_analysis,
                            total_mail=total_emails_analyzed,
                            unique_sender=unique_senders_count,
                            top_sender= top_sender_email,
                            count_top_sender=top_sender_email_count,
                            viewable_statuses=viewable_statuses,
                            cur_user=current_user.id,
                            main_topic=main_topic,
                            unique_topics_count=unique_topics_count,
                            graphJSON=graphJSON,
                            pos_sent_count=pos_sent,
                            neu_sent_count=neu_sent,
                            neg_sent_count=neg_sent,
                            graphJSON_Sent=graphJSON_Sent,
                            
                            )

   

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        user_to_create = User(username=form.username.data,
                              email_address=form.email_address.data,
                              password=form.password1.data)
        db.session.add(user_to_create)
        db.session.commit()
        login_user(user_to_create)
        flash(f"Account created successfully! You are now logged in as {user_to_create.username}", category='success')
        return redirect(url_for('dashboard_page'))
    if form.errors != {}: #If there are not errors from the validations
        for err_msg in form.errors.values():
            flash(f'There was an error with creating a user: {err_msg}', category='danger')

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(username=form.username.data).first()              
        if attempted_user and attempted_user.check_password_correction(
                attempted_password=form.password.data
        ):
            
            login_user(attempted_user)
            flash(f'Success! You are logged in as: {attempted_user.username}', category='success')
            return redirect(url_for('dashboard_page'))
        else:
            flash('Username and password are not match! Please try again', category='danger')

    return render_template('login.html', form=form)

@app.route('/logout')
def logout_page():
    logout_user()
    flash("You have been logged out!", category='info')
    return redirect(url_for("home_page"))


@app.route('/delete_file/<id>/', methods=['GET', 'POST'])
def delete_file(id):
    file_to_delete = Mails.query.get(id)

    if not file_to_delete:
        flash("File not found!")
        return redirect(url_for('dashboard'))

    try:
        db.session.delete(file_to_delete)
        db.session.commit()
        flash("File and associated analysis results deleted successfully!", category="danger")

    except Exception as e:
        flash("Whoops, something went wrong: " + str(e))
        return redirect(url_for('dashboard_page'))

    return redirect(url_for('dashboard_page'))


@app.route('/process/<id>', methods=['POST'])
def process_file(id):
    # Verifica se l'utente è autenticato
    if current_user.is_authenticated:
        # Recupera la mail associata all'ID specificato
        mail = Mails.query.get(id)
        if mail:
            start_time = time.time()
            
            df = pd.read_csv(io.StringIO(mail.file.decode()))
            

            # Carica il modello NLP per l'analisi
            nlp = spacy.load("en_core_web_sm")

            # Processa il testo delle mail per ogni tupla nel DataFrame
            for _, row in df.iterrows():
                # Estrai il testo della mail
                mail_content = str(row['content'])
                mail_subject= row['Subject']
                mail_sender = row['X-From']

                # Processa il testo delle mail
                doc = nlp(mail_content)

                # Estrai le 10 parole più frequenti
                word_freq = Counter(token.text for token in doc if not token.is_stop and not token.is_punct)
                top_10_words = ' '.join([word for word, _ in word_freq.most_common(10)])
                top_10_words = re.sub(r'[^a-zA-Z0-9\s]', '', top_10_words)

                # Topic Extraction
                topics = topic_Bert(mail_content)
                
                # Analizza le entità nominate utilizzando StanfordNLP
                mail_ner = extract_ner(mail_content)

                # Summarization
                mail_summary = summary_text_t5(mail_content)

                #Sentiment
                mail_sentiment =sentiment_vader(mail_content) 

                # Salva i risultati dell'analisi delle mail nella tabella MailAnalysisResult
                analysis_result = MailAnalysisResult(
                    user_id=current_user.id,
                    file_id=mail.id,
                    analyzed_mail=mail_content,
                    top_10_words=top_10_words,
                    subject=mail_subject,
                    mail_from=mail_sender,
                    mail_topic=topics,
                    mail_NER=mail_ner,
                    mail_Sum=mail_summary,
                    mail_Sent=mail_sentiment,
                )
                db.session.add(analysis_result)

            

            # Aggiorna lo stato di elaborazione del file
            mail.processing_status = 'processed'

            # Aggiungi la logica per impostare lo stato di visualizzazione del file
            if not mail.viewable_status:
                mail.viewable_status = True
                flash("File Processed Successfully! Now it's viewable.", category="warning")
            else:
                flash("File Processed Successfully!", category="warning")
            
            # Committa le modifiche al database dopo aver elaborato tutte le mail
            db.session.commit()

            end_time = time.time()
            elapsed_time = (end_time - start_time)/60
            flash(f"Processing time: {elapsed_time:.2f} minute", category="info")

            return redirect(url_for('dashboard_page'))
        else:
            return 'Error: No mail found for the specified ID.'
    else:
        return 'Error: User not authenticated.'


@app.route('/view/<int:id>', methods=['GET','POST'])
def analysis_page(id):
    # Retrieve the specific mail entry by its id
    specific_mail = Mails.query.get_or_404(id)

    # Check if the current user is the owner of the mail
    if specific_mail.owner != current_user.id:
        abort(403)  # Forbidden 

    # Get the page number from the query parameters, default to 1 if not provided
    page = request.args.get('page', 1, type=int)
    per_page = 10  

    

    # Queries related to the specific file ID with pagination
    mails_analysis = MailAnalysisResult.query.filter_by(file_id=id).paginate(page=page, per_page=per_page)

    total_emails_analyzed = mails_analysis.total
    if total_emails_analyzed is None:
        total_emails_analyzed = 0

    unique_senders_count = db.session.query(db.func.count(db.func.distinct(MailAnalysisResult.mail_from))).filter_by(file_id=id).scalar()
    if unique_senders_count is None:
        unique_senders_count = 0

    most_sender = db.session.query(MailAnalysisResult.mail_from, db.func.count(MailAnalysisResult.id)).filter_by(file_id=id).group_by(MailAnalysisResult.mail_from).all()
    if most_sender:
        top_sender = max(most_sender, key=lambda x: x[1])
        top_sender_email, top_sender_email_count = top_sender[0], top_sender[1]
    else:
        top_sender_email_count = 0
        top_sender_email = None

    positive_sentiment_count = MailAnalysisResult.query.filter_by(file_id=id, mail_Sent='positive').count()
    if positive_sentiment_count:
        pos_sent= positive_sentiment_count
    else:
        pos_sent=0

    neutral_sentiment_count = MailAnalysisResult.query.filter_by(file_id=id, mail_Sent='neutral').count()
    if neutral_sentiment_count:
        neu_sent= neutral_sentiment_count
    else:
        neu_sent=0 

    negative_sentiment_count = MailAnalysisResult.query.filter_by(file_id=id, mail_Sent='negative').count()
    if negative_sentiment_count:
        neg_sent= negative_sentiment_count
    else:
        neg_sent=0

    top_topics = db.session.query(MailAnalysisResult.mail_topic, db.func.count(MailAnalysisResult.mail_topic)) \
    .filter_by(file_id=id) \
    .group_by(MailAnalysisResult.mail_topic) \
    .order_by(db.func.count(MailAnalysisResult.mail_topic).desc()) \
    .limit(3) \
    .all()
    if top_topics:
        main_topic= top_topics
    else:
        main_topic=0
    
   
    all_topics = db.session.query(MailAnalysisResult.mail_topic, db.func.count(MailAnalysisResult.mail_topic)) \
                .filter_by(file_id=id) \
                .group_by(MailAnalysisResult.mail_topic) \
                .order_by(db.func.count(MailAnalysisResult.mail_topic).desc()).all()
   
    
    if all_topics:   
            topic_freq = {topic: freq for topic, freq in all_topics}
            graphJSON = plot_topic_frequencies_dash(topic_freq, 10)
            graphJSON = graphJSON.to_json()
    else:
        graphJSON=0
    
    unique_topics_count = db.session.query(db.func.count(db.func.distinct(MailAnalysisResult.mail_topic))).filter_by(file_id=id).scalar()

    return render_template('view.html',
                           file_mail=specific_mail,
                           file_name=specific_mail.file_name,
                           mail_results=mails_analysis.items,
                           pagination=mails_analysis,
                           total_mail=total_emails_analyzed,
                           unique_sender=unique_senders_count,
                           top_sender=top_sender_email,
                           count_top_sender=top_sender_email_count,
                           pos_sent_count=pos_sent,
                           neu_sent_count=neu_sent,
                           neg_sent_count=neg_sent,
                           main_topic=main_topic,
                           graphJSON=graphJSON,
                           unique_topics_count=unique_topics_count,                           
                           )

@app.route('/filter/<int:id>', methods=['GET', 'POST'])
def filter_page(id):
    specific_mail = Mails.query.get_or_404(id)

    if specific_mail.owner != current_user.id:
        abort(403)

    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Recupero dei valori per i filtri
    selected_topic = request.args.get('topic')
    selected_sentiment = request.args.get('sentiment')
    selected_sender = request.args.get('sender')

    # Base query
    query = MailAnalysisResult.query.filter_by(file_id=id)

    # Aggiunta dei filtri se presenti
    if selected_topic:
        query = query.filter_by(mail_topic=selected_topic)
    if selected_sentiment:
        query = query.filter_by(mail_Sent=selected_sentiment)
    if selected_sender:
        query = query.filter_by(mail_from=selected_sender)

    # Conteggio delle mail filtrate
    total_filtered_mails = query.count()

    # Paginazione
    mails_analysis = query.paginate(page=page, per_page=per_page)

    # Valori unici per suggerimenti di filtri
    unique_topics = db.session.query(MailAnalysisResult.mail_topic).filter_by(file_id=id).distinct().all()
    unique_senders = db.session.query(MailAnalysisResult.mail_from).filter_by(file_id=id).distinct().order_by(MailAnalysisResult.mail_from.asc()).all()
    unique_sentiments = db.session.query(MailAnalysisResult.mail_Sent).filter_by(file_id=id).distinct().all()

    return render_template('filter.html',
                           file_mail=specific_mail,
                           mail_results=mails_analysis.items,
                           pagination=mails_analysis,
                           unique_topics=[t[0] for t in unique_topics],
                           unique_senders=[s[0] for s in unique_senders],
                           unique_sentiments=[sent[0] for sent in unique_sentiments],
                           selected_topic=selected_topic,
                           selected_sentiment=selected_sentiment,
                           selected_sender=selected_sender,
                           total_filtered_mails=total_filtered_mails) 


@app.route('/filtered-mails/<int:id>', methods=['GET', 'POST'])
@login_required
def filtered_mails_page(id):

    

    # Verifica se l'utente è autenticato
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Recupero dei valori per i filtri
    selected_topic = request.args.get('topic')
    selected_sentiment = request.args.get('sentiment')
    selected_sender = request.args.get('sender')

    # Base query
    query = MailAnalysisResult.query.filter_by(user_id=id)

    # Aggiunta dei filtri se presenti
    if selected_topic:
        query = query.filter_by(mail_topic=selected_topic)
    if selected_sentiment:
        query = query.filter_by(mail_Sent=selected_sentiment)
    if selected_sender:
        query = query.filter_by(mail_from=selected_sender)

    # Conteggio delle mail filtrate
    total_filtered_mails = query.count()

    # Paginazione
    mails_analysis = query.paginate(page=page, per_page=per_page)

    # Valori unici per suggerimenti di filtri
    unique_topics = db.session.query(MailAnalysisResult.mail_topic).filter_by( user_id=current_user.id).distinct().order_by(MailAnalysisResult.mail_topic.asc()).all()
    unique_senders = db.session.query(MailAnalysisResult.mail_from).filter_by( user_id=current_user.id).distinct().order_by(MailAnalysisResult.mail_from.asc()).all()
    unique_sentiments = db.session.query(MailAnalysisResult.mail_Sent).filter_by( user_id=current_user.id).distinct().all()

    return render_template('filtered-mails.html',
                           cur_user=current_user.id,                           
                           mail_results=mails_analysis.items,
                           pagination=mails_analysis,
                           unique_topics=[t[0] for t in unique_topics],
                           unique_senders=[s[0] for s in unique_senders],
                           unique_sentiments=[sent[0] for sent in unique_sentiments],
                           selected_topic=selected_topic,
                           selected_sentiment=selected_sentiment,
                           selected_sender=selected_sender,
                           total_filtered_mails=total_filtered_mails) 