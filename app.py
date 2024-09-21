from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import os
from dotenv import load_dotenv
import openai
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

# Charger les données
data_dir = "/workspaces/Recommenders-Systems/data"
books_path = os.path.join(data_dir, "merged_df.pkl")
books_df = pd.read_pickle(books_path)

# Nettoyage et prétraitement des données
books_df['Year-Of-Publication'] = books_df['Year-Of-Publication'].replace({'0': '2022', '2037': '2022'}).astype(int)
books_df['content'] = books_df['Book-Title'].fillna('') + ' ' + books_df['Book-Author'].fillna('') + ' ' + books_df['Publisher'].fillna('') + ' ' + books_df['Year-Of-Publication'].astype(str)

# Création de la matrice TF-IDF
tfidf = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(books_df['content'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query', '').lower()
    logging.debug(f"Recherche pour: {query}")

    query_vec = tfidf.transform([query])
    cosine_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    related_docs_indices = cosine_similarities.argsort()[:-6:-1]

    results = books_df.iloc[related_docs_indices].to_dict('records')

    if query.isdigit():
        year_query = int(query)
        year_results = books_df[books_df['Year-Of-Publication'] == year_query].to_dict('records')
        results.extend(year_results)

    unique_results = []
    seen = set()
    for book in results:
        if book['ISBN'] not in seen:
            seen.add(book['ISBN'])
            unique_results.append(book)

    logging.debug(f"Nombre de résultats: {len(unique_results)}")
    return jsonify(unique_results)

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_input = request.json.get('message', '')
    if not user_input:
        return jsonify({"response": "Je n'ai rien reçu. Pouvez-vous reformuler votre demande ?"}), 400

    logging.debug(f"Message reçu du chatbot: {user_input}")

    recommendations = get_book_recommendations(user_input)

    chatbot_response = generate_chatbot_response(user_input, recommendations)

    return jsonify({
        "response": chatbot_response,
        "books": recommendations
    })

def get_book_recommendations(query, n=5):
    query_vec = tfidf.transform([query])
    cosine_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    related_docs_indices = cosine_similarities.argsort()[:-n-1:-1]
    
    recommendations = books_df.iloc[related_docs_indices][['ISBN', 'Book-Title', 'Book-Author', 'Image-URL-L', 'Year-Of-Publication']]
    return recommendations.drop_duplicates(subset='Book-Title').head(n).to_dict('records')

def generate_chatbot_response(user_input, recommendations):
    formatted_recommendations = "\n".join([f"• {book['Book-Title']} par {book['Book-Author']} (publié en {book['Year-Of-Publication']})" for book in recommendations])
    
    prompt = f"""
    Vous êtes un assistant virtuel spécialisé dans la recommandation de livres. L'utilisateur a dit : '{user_input}'.
    Basé sur cette entrée, voici les livres suggérés :
    {formatted_recommendations}

    Fournissez une recommandation personnalisée pour chaque livre en 2-3 phrases. Structurez votre réponse ainsi :
    1. Une brève introduction expliquant la pertinence de ces livres.
    2. Pour chaque livre, donnez une recommandation personnalisée liée à la recherche de l'utilisateur.
    3. Une conclusion encourageant l'utilisateur à explorer ces livres et à poser d'autres questions.

    Assurez-vous que chaque recommandation est unique et attrayante pour le lecteur.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Vous êtes un assistant qui recommande des livres de manière personnalisée et enthousiaste."},
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        answer = response['choices'][0]['message']['content'].strip()
        logging.debug(f"Réponse du chatbot générée avec succès")
        return answer
    except Exception as e:
        logging.error(f"Erreur lors de la génération de la réponse du chatbot: {e}")
        return "Désolé, je ne peux pas traiter votre demande pour le moment."

@app.route('/top_rated_books')
def top_rated_books():
    top_books = books_df.sort_values('Book-Rating', ascending=False).head(5)
    return jsonify({
        'labels': top_books['Book-Title'].tolist(),
        'values': top_books['Book-Rating'].tolist()
    })

@app.route('/top_read_by_country')
def top_read_by_country():
    countries = ['USA', 'UK', 'France', 'Germany', 'Japan']
    reads = [1000, 800, 600, 500, 400]
    return jsonify({'labels': countries, 'values': reads})

@app.route('/popular_genres')
def popular_genres():
    genres = ['Fiction', 'Non-fiction', 'Science-fiction', 'Romance', 'Thriller']
    popularity = [40, 30, 15, 10, 5]
    return jsonify({'labels': genres, 'values': popularity})

@app.route('/reading_trends')
def reading_trends():
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    books_read = [50, 60, 55, 70, 65, 80]
    return jsonify({'labels': months, 'values': books_read})

if __name__ == '__main__':
    app.run(debug=True)