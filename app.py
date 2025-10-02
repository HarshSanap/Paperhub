from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import sqlite3
import PyPDF2
import spacy
import pytextrank
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from collections import Counter
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe("textrank")
except:
    nlp = None

def init_db():
    with sqlite3.connect('papers.db') as conn:
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())

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
    if not nlp or not text:
        return "No keywords available"
    try:
        doc = nlp(text[:5000])  # Limit text length
        keywords = [phrase.text for phrase in doc._.phrases[:num_keywords]]
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
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and file.filename.lower().endswith('.pdf'):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            text = extract_text_from_pdf(filepath)
            title, author = extract_author_title(text)
            keywords = extract_keywords(text)
            summary = extract_summary(text)
            
            with sqlite3.connect('papers.db') as conn:
                conn.execute(
                    'INSERT INTO papers (title, author, keywords, summary, filepath) VALUES (?, ?, ?, ?, ?)',
                    (title, author, keywords, summary, filepath)
                )
                conn.commit()
            
            flash('File uploaded and processed successfully!')
            return redirect(url_for('list_papers'))
        
        except Exception as e:
            flash(f'Error processing file: {str(e)}')
            return redirect(request.url)
    
    else:
        flash('Please upload a PDF file')
        return redirect(request.url)

@app.route('/papers')
def list_papers():
    with sqlite3.connect('papers.db') as conn:
        papers = conn.execute('SELECT * FROM papers ORDER BY id DESC').fetchall()
    return render_template('list.html', papers=papers)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    papers = []
    
    if query:
        with sqlite3.connect('papers.db') as conn:
            papers = conn.execute(
                'SELECT * FROM papers WHERE title LIKE ? OR author LIKE ? OR keywords LIKE ? ORDER BY id DESC',
                (f'%{query}%', f'%{query}%', f'%{query}%')
            ).fetchall()
    
    return render_template('search.html', papers=papers, query=query)

@app.route('/api/papers')
def api_papers():
    with sqlite3.connect('papers.db') as conn:
        papers = conn.execute('SELECT * FROM papers ORDER BY id DESC').fetchall()
        return jsonify([{
            'id': p[0], 'title': p[1], 'author': p[2], 
            'keywords': p[3], 'summary': p[4]
        } for p in papers])

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)