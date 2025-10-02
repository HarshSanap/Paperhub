from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
import sqlite3
import PyPDF2
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from collections import Counter
import re
import hashlib
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    stop_words = set(stopwords.words('english'))
except:
    stop_words = set()

def init_db():
    with sqlite3.connect('papers.db') as conn:
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
    except:
        pass
    return text

def extract_keywords(text, num_keywords=10):
    if not text:
        return "No keywords available"
    try:
        words = word_tokenize(text.lower())
        words = [word for word in words if word.isalpha() and word not in stop_words and len(word) > 3]
        word_freq = Counter(words)
        keywords = [word for word, freq in word_freq.most_common(num_keywords)]
        return ', '.join(keywords) if keywords else "No keywords found"
    except:
        return "Error extracting keywords"

def extract_summary(text, num_sentences=3):
    if not text:
        return "No summary available"
    try:
        sentences = sent_tokenize(text)
        if len(sentences) <= num_sentences:
            return text[:500]
        return ' '.join(sentences[:num_sentences])[:500]
    except:
        return text[:500] if text else "No summary available"

def extract_author_title(text):
    if not text:
        return "Unknown Title", "Unknown Author"
    
    lines = [line.strip() for line in text.split('\n')[:15] if line.strip()]
    title = lines[0][:200] if lines else "Unknown Title"
    author = "Unknown Author"
    
    for line in lines[1:5]:
        if any(word in line.lower() for word in ['author', 'by', '@']):
            author = line[:100]
            break
    
    return title, author

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.')
            return render_template('register.html')
        
        hashed_password = hash_password(password)
        
        try:
            with sqlite3.connect('papers.db') as conn:
                conn.execute(
                    'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                    (username, email, hashed_password)
                )
                conn.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists.')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        
        with sqlite3.connect('papers.db') as conn:
            user = conn.execute(
                'SELECT id, username FROM users WHERE username = ? AND password = ?',
                (username, hashed_password)
            ).fetchone()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Welcome back!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    with sqlite3.connect('papers.db') as conn:
        papers = conn.execute(
            'SELECT * FROM papers WHERE user_id = ? ORDER BY id DESC LIMIT 5',
            (session['user_id'],)
        ).fetchall()
        total_papers = conn.execute(
            'SELECT COUNT(*) FROM papers WHERE user_id = ?',
            (session['user_id'],)
        ).fetchone()[0]
    
    return render_template('dashboard.html', papers=papers, total_papers=total_papers)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'GET':
        return render_template('upload.html')
    
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and file.filename.lower().endswith('.pdf'):
        filename = f"{session['user_id']}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            text = extract_text_from_pdf(filepath)
            title, author = extract_author_title(text)
            keywords = extract_keywords(text)
            summary = extract_summary(text)
            
            with sqlite3.connect('papers.db') as conn:
                conn.execute(
                    'INSERT INTO papers (title, author, keywords, summary, filepath, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                    (title, author, keywords, summary, filepath, session['user_id'])
                )
                conn.commit()
            
            flash('File uploaded and processed successfully!')
            return redirect(url_for('papers'))
        
        except Exception as e:
            flash(f'Error processing file: {str(e)}')
            return redirect(request.url)
    
    else:
        flash('Please upload a PDF file')
        return redirect(request.url)

@app.route('/papers')
@login_required
def papers():
    with sqlite3.connect('papers.db') as conn:
        user_papers = conn.execute(
            'SELECT * FROM papers WHERE user_id = ? ORDER BY id DESC',
            (session['user_id'],)
        ).fetchall()
    return render_template('papers.html', papers=user_papers)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    papers = []
    
    if query:
        with sqlite3.connect('papers.db') as conn:
            papers = conn.execute(
                'SELECT * FROM papers WHERE user_id = ? AND (title LIKE ? OR author LIKE ? OR keywords LIKE ?) ORDER BY id DESC',
                (session['user_id'], f'%{query}%', f'%{query}%', f'%{query}%')
            ).fetchall()
    
    return render_template('search.html', papers=papers, query=query)

@app.route('/api/papers')
@login_required
def api_papers():
    with sqlite3.connect('papers.db') as conn:
        papers = conn.execute(
            'SELECT * FROM papers WHERE user_id = ? ORDER BY id DESC',
            (session['user_id'],)
        ).fetchall()
        return jsonify([{
            'id': p[0], 'title': p[1], 'author': p[2], 
            'keywords': p[3], 'summary': p[4]
        } for p in papers])

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=True)