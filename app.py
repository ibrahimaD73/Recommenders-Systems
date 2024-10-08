from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import os
from dotenv import load_dotenv
import openai
from loguru import logger
from google.cloud import storage
from google.oauth2 import service_account
from google.auth import default
import json
import base64


logger.add("pipeline.log", rotation="500 MB", level="DEBUG")

load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_storage_client():
    if os.environ.get('K_SERVICE'):  # Check if running on Cloud Run
        credentials, project = default()
    else:
        # We're running locally
        credentials_path = os.environ.get("GCP_CREDENTIALS")
        if not credentials_path:
            raise ValueError("GCP_CREDENTIALS environment variable is not set")
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        project = os.environ.get("GCP_PROJECT_ID")
    
    return storage.Client(credentials=credentials, project=project)

def download_from_gcs(bucket_name, source_blob_name, destination_file_name):
    storage_client = get_storage_client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    logger.info(
        f"Downloaded {source_blob_name} from {bucket_name} to {destination_file_name}."
    )

# Charger les données
def load_data():
    try:
        download_from_gcs(
            os.getenv("GCP_BUCKET_NAME"),
            "preprocessed_data.csv",
            "preprocessed_data.csv",
        )
        books_df = pd.read_csv("preprocessed_data.csv")
        logger.info("Data loaded successfully from GCS.")
        logger.info(f"DataFrame shape: {books_df.shape}")
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise
    return books_df


# Initialisation des données au démarrage de l'application
books_df = load_data()

# Création de la matrice TF-IDF
tfidf = TfidfVectorizer(stop_words="english")
tfidf_matrix = tfidf.fit_transform(books_df["content"])


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    query = request.json.get("query", "").lower()
    logger.debug(f"Recherche pour: {query}")

    query_vec = tfidf.transform([query])
    cosine_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    related_docs_indices = cosine_similarities.argsort()[:-6:-1]

    results = books_df.iloc[related_docs_indices].to_dict("records")

    if query.isdigit():
        year_query = int(query)
        year_results = books_df[books_df["Year-Of-Publication"] == year_query].to_dict(
            "records"
        )
        results.extend(year_results)

    unique_results = []
    seen = set()
    for book in results:
        if book["ISBN"] not in seen:
            seen.add(book["ISBN"])
            unique_results.append(book)

    logger.debug(f"Nombre de résultats: {len(unique_results)}")
    return jsonify(unique_results)


@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_input = request.json.get("message", "")
    if not user_input:
        return (
            jsonify(
                {
                    "response": "Je n'ai rien reçu. Pouvez-vous reformuler votre demande ?"
                }
            ),
            400,
        )

    logger.debug(f"Message reçu du chatbot: {user_input}")

    recommendations = get_book_recommendations(user_input)

    chatbot_response = generate_chatbot_response(user_input, recommendations)

    return jsonify({"response": chatbot_response, "books": recommendations})


def get_book_recommendations(query, n=5):
    query_vec = tfidf.transform([query])
    cosine_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    related_docs_indices = cosine_similarities.argsort()[: -n - 1 : -1]

    recommendations = books_df.iloc[related_docs_indices][
        [
            "ISBN",
            "Book-Title",
            "Book-Author",
            "Image-URL-L",
            "Year-Of-Publication",
            "Book-Rating",
        ]
    ]
    recommendations = recommendations.drop_duplicates(subset="Book-Title").head(n)

    # Générer un commentaire basé sur la note du livre
    for index, book in recommendations.iterrows():
        rating = book["Book-Rating"]
        if rating >= 4.5:
            comment = "Un chef-d'œuvre incontournable !"
        elif rating >= 4.0:
            comment = "Très apprécié par les lecteurs."
        elif rating >= 3.5:
            comment = "Une lecture intéressante."
        elif rating >= 3.0:
            comment = "Avis mitigés, mais vaut le détour."
        else:
            comment = "Un livre qui divise l'opinion."

        recommendations.at[index, "comment"] = comment

    return recommendations.to_dict("records")


def generate_chatbot_response(user_input, recommendations):
    formatted_recommendations = "\n".join(
        [
            f"• {book['Book-Title']} par {book['Book-Author']} (publié en {book['Year-Of-Publication']}) - {book['comment']}"
            for book in recommendations
        ]
    )

    prompt = f"""
    Vous êtes un assistant virtuel spécialisé dans la recommandation de livres. L'utilisateur a dit : '{user_input}'.
    Basé sur cette entrée, voici les livres suggérés :
    {formatted_recommendations}

    Fournissez une recommandation personnalisée pour chaque livre en 2-3 phrases. Structurez votre réponse ainsi :
    1. Une brève introduction expliquant la pertinence de ces livres.
    2. Pour chaque livre, donnez une recommandation personnalisée liée à la recherche de l'utilisateur.
    3. Une conclusion encourageant l'utilisateur à explorer ces livres et à poser d'autres questions.

    Si aucun livre n'est recommandé, donnez une réponse encourageante et pertinente à la requête de l'utilisateur.

    Assurez-vous que chaque recommandation est unique et attrayante pour le lecteur.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "Vous êtes un assistant qui recommande des livres de manière personnalisée et enthousiaste.",
                },
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": prompt},
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        answer = response["choices"][0]["message"]["content"].strip()
        logger.debug(f"Réponse du chatbot générée avec succès")
        return answer
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la réponse du chatbot: {e}")
        return "Je suis désolé, mais je n'ai pas pu trouver de recommandations spécifiques pour votre demande. Cependant, n'hésitez pas à explorer notre vaste collection de livres. Que diriez-vous de me parler un peu plus de vos goûts littéraires ? Je serai ravi de vous aider à trouver votre prochaine lecture passionnante !"


@app.route("/top_rated_books")
def top_rated_books():
    top_books = books_df.sort_values("Book-Rating", ascending=False).head(5)
    return jsonify(
        {
            "labels": top_books["Book-Title"].tolist(),
            "values": top_books["Book-Rating"].tolist(),
        }
    )


@app.route("/top_read_by_country")
def top_read_by_country():
    countries = ["USA", "UK", "France", "Germany", "Japan"]
    reads = [1000, 800, 600, 500, 400]
    return jsonify({"labels": countries, "values": reads})


@app.route("/popular_genres")
def popular_genres():
    genres = ["Fiction", "Non-fiction", "Science-fiction", "Romance", "Thriller"]
    popularity = [40, 30, 15, 10, 5]
    return jsonify({"labels": genres, "values": popularity})


@app.route("/reading_trends")
def reading_trends():
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    books_read = [50, 60, 55, 70, 65, 80]
    return jsonify({"labels": months, "values": books_read})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
    
