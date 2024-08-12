#the conditions for sorting are set and working for naukri , timesjobs , foundit. in jobs.html 
# the output is sorted even for jobs,  resume 
#its not sprting for content


import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
import os
import re
import csv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from pdfminer.high_level import extract_text
import docx

app = Flask(__name__)
df = pd.read_csv(r'C:\Users\SUMEDHA\final project\flaskapp\scraping_ntf.csv')
nlp = spacy.load('en_core_web_sm')

# Function to preprocess text data
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text

# Function to preprocess experience
def preprocess_experience(exp):
    exp_years = re.search(r'\d+', str(exp))
    if exp_years:
        return int(exp_years.group())
    else:
        return None

# Preprocess the 'Job Title' column
df['Job Title'] = df['Job Title'].apply(preprocess_text)

def extract_text_from_resume(file_path):
    text = ''
    if file_path.endswith('.pdf'):
        text = extract_text(file_path)
    elif file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text
    return text

def extract_skills_from_text(text):
    doc = nlp(text)
    skills = set()
    for chunk in doc.noun_chunks:
        if len(chunk.text.split()) <= 3:  # Limit to 3 words for now
            if chunk.text.lower() in known_skills:
                skills.add(chunk.text.lower())
    return list(skills)


def convert_to_days_ago(date_str):
    if 'few' in date_str:
        return -5  # Consider 'few days ago' as 3 days ago
    elif 'today' in date_str or 'now' in date_str or 'hour' in date_str:
        return 0  # Consider 'today' or 'now' as 0 day ago
    elif 'month' in date_str or 'within' in date_str or 'in' in date_str:
        return -30  # Consider 'a month ago' or 'within' or 'in' as 30 days ago
    elif '+' in date_str:
        return -30  # Consider '30+ days ago' as 30 days ago
    else:
        days_ago = re.findall(r'\d+', date_str)
        if days_ago:
            return -int(days_ago[0])  # Extract number of days ago from the string
        else:
            return 0  # Return 0 if unable to extract


def recommend_jobs(skills):
    uploaded_skills = " ".join(skills)
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(df['Skills'])
    uploaded_skills_vector = tfidf_vectorizer.transform([uploaded_skills])
    cosine_similarities = cosine_similarity(uploaded_skills_vector, tfidf_matrix).flatten()
    top_indices = cosine_similarities.argsort()[-10:][::-1]
    recommendations = []
    for index in top_indices:
        job_skills = df['Skills'][index].split(', ')  # Get the skills mentioned in the job
        recommendations.append({
            'Job Title': df['Job Title'][index],
            'Company Name': df['Company Name'][index],
            'Experience': df['Experience'][index],
            'Salary': df['Salary'][index],
            'Date Posted': df['Date Posted'][index],
            'Location': df['Location'][index],
            'Skills': job_skills,  # Include the job skills in the recommendations
            'URL': df['URL'][index]
        })
    # Sort the recommendations by date posted in descending order (most recent first)
    recommendations.sort(key=lambda x: convert_to_days_ago(x['Date Posted']))
    return recommendations

def filter_jobs_by_experience(df, exp):
    processed_exp = df['Experience'].apply(preprocess_experience)
    valid_indices = processed_exp.notnull() & (processed_exp <= exp)
    filtered_df = df[valid_indices]
    return filtered_df

def recommend_jobs_content(job_title, experience, num_recommendations=10):
    filtered_df = filter_jobs_by_experience(df, experience)
    if len(filtered_df) == 0:
        return pd.DataFrame(columns=['Job Title', 'Company Name', 'Experience', 'Salary', 'Date Posted', 'Location', 'Skills','URL'])
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(filtered_df['Job Title'])
    job_title_tfidf = tfidf_vectorizer.transform([job_title])
    cosine_similarities = cosine_similarity(job_title_tfidf, tfidf_matrix).flatten()
    similar_indices = cosine_similarities.argsort()[::-1][:num_recommendations]
    recommended_jobs = filtered_df.iloc[similar_indices].copy()
    recommended_jobs['Days Ago'] = recommended_jobs['Date Posted'].apply(convert_to_days_ago)
    recommended_jobs = recommended_jobs.sort_values(by='Days Ago', ascending=False)
    recommended_jobs = recommended_jobs.sort_values(by='Date Posted', ascending=False)
    return recommended_jobs[['Job Title', 'Company Name', 'Experience', 'Salary', 'Date Posted', 'Location', 'Skills','URL']]

@app.route('/')
def index():
    return render_template('basic.html')

@app.route('/content', methods=['GET', 'POST'])
def content():
    if request.method == 'POST':
        job_title = request.form['job_title']
        experience = int(request.form['experience'])
        recommended_jobs = recommend_jobs_content(job_title, experience)
        recommended_jobs = recommended_jobs.sort_values(by='Date Posted', ascending=True).reset_index(drop=True)
        return render_template('content.html', jobs=recommended_jobs.to_dict(orient='records'))
    else:
        return render_template('content.html')

@app.route('/resume')
def resume():
    return render_template('resume.html')

@app.route('/submit_resume', methods=['POST'])
def submit_resume():
    if request.method == 'POST':
        file = request.files['resume']
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)
        text = extract_text_from_resume(file_path) 

        skills = extract_skills_from_text(text)
        print("extracted skills :", skills)

        recommendations = recommend_jobs(skills)
        recommendations = sorted(recommendations, key=lambda x: convert_to_days_ago(x['Date Posted']), reverse=True)

        return render_template('resume.html', jobs=recommendations)
    return render_template('resume.html')

@app.route('/jobs/<job_title>')
def get_jobs(job_title):
    with open('scraping_ntf.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        jobs = [row for row in reader if job_title.lower() in row['Job Title'].lower()]
    unique_jobs = []
    unique_entries = set()
    for job in jobs:
        job_entry = (job['Job Title'], job['Company Name'], job['Experience'], job['Salary'], job['Date Posted'], job['Location'], job['Skills'], job['URL'])
        if job_entry not in unique_entries:
            unique_jobs.append(job)
            unique_entries.add(job_entry)
            
    # Sort the jobs based on the date posted
    unique_jobs.sort(key=lambda x: convert_to_days_ago(x['Date Posted']), reverse=True)  # Reverse to get descending order
  
    return render_template('jobs.html', jobs=unique_jobs)


if __name__ == '__main__':
    # Initialize the set of known skills from the CSV file
    known_skills = set()
    for index, row in df.iterrows():
        skills_str = row['Skills']
        skills_list = [skill.strip().lower() for skill in skills_str.split(',')]
        known_skills.update(skills_list)

    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.run(debug=True)