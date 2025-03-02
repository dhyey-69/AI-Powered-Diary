from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from summary_generator import tfidf_summary
from sentiment_analysis import analyze_sentiment
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
from PIL import Image
import pandas as pd
import matplotlib.dates as mdates


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'


def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='ai_diary'
    )
    return connection


@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

def get_entry_by_id(entry_id):
    username = session.get('user')
    if not username:
        return None
    
    table_name = f"{username}_diary"

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='ai_diary'
    )
    cursor = conn.cursor()
    
    query = f"SELECT * FROM {table_name} WHERE entry_id = %s"
    
    cursor.execute(query, (entry_id,))
    entry = cursor.fetchone()
    cursor.close()
    conn.close()

    return entry


def update_entry(entry_id, new_entry_text):
    username = session.get('user')
    if not username:
        return None

    table_name = f"{username}_diary"

    conn = get_db_connection()
    cur = conn.cursor()

    query = f"UPDATE {table_name} SET entry_text = %s WHERE entry_id = %s"
    
    cur.execute(query, (new_entry_text, entry_id))
    conn.commit()
    cur.close()
    conn.close()
    


@app.route('/edit_entry/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):

    entry = get_entry_by_id(entry_id)
    
    if not entry:
        return "Entry not found", 404
    
    if request.method == 'POST':
        new_entry_text = request.form['entry_text']
        
        update_entry(entry_id, new_entry_text)
        
        return redirect(url_for('view_entries'))
    
    return render_template('edit_entry.html', entry=entry, entry_id=entry[0])


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('You must be logged in to view this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/add_entry', methods=['GET', 'POST'])
@login_required
def add_entry():
    if request.method == 'POST':
        entry_text = request.form['entry_text']

        if len(entry_text.split()) > 20:
            summary = tfidf_summary(entry_text)
        else:
            summary = entry_text

        sentiment = analyze_sentiment(entry_text)
        
        created_at = datetime.now()

        user_email = session['user']
        user_diary_table = f"{user_email}_diary"

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            INSERT INTO {user_diary_table} (entry_text, sentiment, summary, created_at)
            VALUES (%s, %s, %s, %s)
        """, (entry_text, sentiment, summary, created_at))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Diary entry saved successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_entry.html')


@app.route('/view_entries', methods=['GET'])
@login_required
def view_entries():
    username = session.get('user')
    if not username:
        return redirect(url_for('login'))
    diary_table = f"{username}_diary"
    search_type = request.args.get('search_type')
    search_value = request.args.get('search_value')
    query = f"SELECT * FROM {diary_table}"
    params = []

    if search_type and search_value:
        if search_type == "keyword":
            query += " WHERE entry_text LIKE %s"
            params.append(f"%{search_value}%")
        elif search_type == "date":
            query += " WHERE DATE(created_at) = %s"
            params.append(search_value)
        elif search_type == "mood":
            query += " WHERE sentiment = %s"
            params.append(search_value)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    entries = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('view_entries.html', entries=entries)


@app.route('/view_analytics', methods=['GET'])
@login_required
def view_analytics():
    username = session['user']
    
    user_diary_table = f"{username}_diary"
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute(f"SELECT created_at, sentiment FROM {user_diary_table} ORDER BY created_at DESC")
    data = cursor.fetchall()
    cursor.close()
    connection.close()

    if not data:
        flash("No data available for sentiment analysis.", 'warning')
        return redirect(url_for('dashboard'))

    df = pd.DataFrame(data, columns=['timestamp', 'sentiment'])

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    df = df.dropna(subset=['timestamp'])

    if df.empty:
        flash("No valid date data available for sentiment analysis.", 'warning')
        return redirect(url_for('dashboard'))

    search_type = request.args.get('search_type', default='daily')
    
    df['date'] = df['timestamp'].dt.date

    grouped_df = df.groupby('date')['sentiment'].agg(lambda x: x.mode()[0]).reset_index()

    fig, ax = plt.subplots(figsize=(12, 6))

    sentiment_values = grouped_df['sentiment'].unique()
    sentiment_map = {value: i for i, value in enumerate(sentiment_values)}

    grouped_df['sentiment_value'] = grouped_df['sentiment'].map(sentiment_map)

    ax.plot(grouped_df['date'], grouped_df['sentiment_value'], marker='o', linestyle='-', color='b')

    ax.set_title(f'Sentiment Changes Over Time ({search_type.capitalize()})')
    ax.set_xlabel('Date')
    ax.set_ylabel('Sentiment')

    ax.set_yticks(range(len(sentiment_values)))
    ax.set_yticklabels(sentiment_values)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'))

    plt.xticks(rotation=45)

    if ax.get_legend() is not None:
        ax.get_legend().remove()

    img = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img, format='png')
    img.seek(0)
    
    plot_url = base64.b64encode(img.getvalue()).decode()

    return render_template('view_analytics.html', plot_url=plot_url)


@app.route('/generate_wordcloud')
@login_required
def generate_wordcloud():
    user_email = session['user']
    user_diary_table = f"{user_email}_diary"
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT entry_text FROM {user_diary_table}")
    entries = cursor.fetchall()
    conn.close()

    combined_text = " ".join([entry['entry_text'] for entry in entries])

    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(combined_text)

    img = wordcloud.to_image()
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

    return render_template('generate_wordcloud.html', word_data=img_base64)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
            session['user'] = user[1]
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            return redirect(url_for('login'))

        cursor.close()
        conn.close()

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        name = request.form['name']

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('signup'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email already exists. Please login.', 'danger')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )
        conn.commit()

        user_id = cursor.lastrowid

        table_name = f"{name.replace(' ', '_').lower()}_diary"
        create_table_query = f"""
            CREATE TABLE {table_name} (
                entry_id INT AUTO_INCREMENT PRIMARY KEY,
                entry_text TEXT,
                sentiment VARCHAR(255),
                summary VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        cursor.execute(create_table_query)
        conn.commit()

        cursor.close()
        conn.close()

        flash('Successfully signed up! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/delete_entry/<int:entry_id>', methods=['GET'])
def delete_entry(entry_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session['user']
    table_name = f"{username}_diary"

    delete_entry_from_db(table_name, entry_id)
    
    return redirect(url_for('view_entries'))

def delete_entry_from_db(table_name, entry_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(f"DELETE FROM {table_name} WHERE entry_id = %s", (entry_id,))
    
    conn.commit()
    conn.close()



@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('home'))


@app.route('/about_us')
def about_us():
    return render_template('about_us.html')


@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')


if __name__ == '__main__':
    app.run(debug=True)