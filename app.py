from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
from dotenv import load_dotenv
import openai
from loguru import logger
from google.cloud import storage
from google.oauth2 import service_account
from google.auth import default
from functools import lru_cache
from io import StringIO

logger.add("pipeline.log", rotation="500 MB", level="DEBUG")
load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@lru_cache(maxsize=1)
def get_storage_client():
    if os.environ.get('K_SERVICE'): 
        credentials, project = default()
    else:
        # We're running locally
        credentials_path = os.environ.get("GCP_CREDENTIALS")
        if not credentials_path:
            raise ValueError("GCP_CREDENTIALS environment variable is not set")
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        project = os.environ.get("GCP_PROJECT_ID")
    
    return storage.Client(credentials=credentials, project=project)

@lru_cache(maxsize=1)
def load_data():
    try:
        storage_client = get_storage_client()
        bucket = storage_client.bucket(os.getenv("GCP_BUCKET_NAME"))
        blob = bucket.blob("preprocessed_data.csv")
        
        # Télécharger le contenu du fichier en mémoire
        content = blob.download_as_text()
        
        # Utiliser StringIO pour créer un objet semblable à un fichier en mémoire
        csv_file = StringIO(content)
        
        # Lire le CSV directement à partir de l'objet en mémoire
        books_df = pd.read_csv(csv_file)
        
        logger.info("Data loaded successfully from GCS.")
        logger.info(f"DataFrame shape: {books_df.shape}")
        return books_df
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise

books_df = load_data()

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
        year_results = books_df[books_df["Year-Of-Publication"] == year_query].to_dict("records")
        results.extend(year_results)

    unique_results = list({book["ISBN"]: book for book in results}.values())

    logger.debug(f"Nombre de résultats: {len(unique_results)}")
    return jsonify(unique_results)


@lru_cache(maxsize=100)
def get_book_recommendations(query, n=5):
    query_vec = tfidf.transform([query])
    cosine_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    related_docs_indices = cosine_similarities.argsort()[:-n-1:-1]

    recommendations = books_df.iloc[related_docs_indices][
        ["ISBN", "Book-Title", "Book-Author", "Image-URL-L", "Year-Of-Publication", "Book-Rating"]
    ]
    recommendations = recommendations.drop_duplicates(subset="Book-Title").head(n)

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
        [f"• {book['Book-Title']} par {book['Book-Author']} (publié en {book['Year-Of-Publication']}) - {book['comment']}"
         for book in recommendations]
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
                {"role": "system", "content": "Vous êtes un assistant qui recommande des livres de manière personnalisée et enthousiaste."},
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

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_input = request.json.get("message", "")
    if not user_input:
        return jsonify({"response": "Je n'ai rien reçu. Pouvez-vous reformuler votre demande ?"}), 400

    logger.debug(f"Message reçu du chatbot: {user_input}")

    recommendations = get_book_recommendations(user_input)
    chatbot_response = generate_chatbot_response(user_input, recommendations)

    return jsonify({"response": chatbot_response, "books": recommendations})

@app.route("/top_rated_books")
@lru_cache(maxsize=1)
def top_rated_books():
    top_books = books_df.sort_values("Book-Rating", ascending=False).head(5)
    return jsonify(
        {
            "labels": top_books["Book-Title"].tolist(),
            "values": top_books["Book-Rating"].tolist(),
        }
    )

@app.route("/top_read_by_country")
@lru_cache(maxsize=1)
def top_read_by_country():
    try:
        countries = ["USA", "UK", "France", "Germany", "Japan"]
        reads = [1000, 800, 600, 500, 400]
        percentages = [round((x / sum(reads)) * 100, 1) for x in reads]
        
        return jsonify({
            "labels": countries,
            "values": reads,
            "percentages": percentages,
            "total": sum(reads)
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des pays lecteurs: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/popular_genres")
@lru_cache(maxsize=1)
def popular_genres():
    try:
        genres = ["Fiction", "Non-fiction", "Science-fiction", "Romance", "Thriller"]
        popularity = [40, 30, 15, 10, 5]
        total = sum(popularity)
        percentages = [round((x / total) * 100, 1) for x in popularity]
        
        return jsonify({
            "labels": genres,
            "values": popularity,
            "percentages": percentages,
            "total": total
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des genres populaires: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/reading_trends")
@lru_cache(maxsize=1)
def reading_trends():
    try:
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        books_read = [50, 60, 55, 70, 65, 80]
        
        # Calculer les tendances
        changes = []
        for i in range(1, len(books_read)):
            change = ((books_read[i] - books_read[i-1]) / books_read[i-1]) * 100
            changes.append(round(change, 1))
        changes.insert(0, 0) 
        
        return jsonify({
            "labels": months,
            "values": books_read,
            "changes": changes,
            "total": sum(books_read),
            "average": round(sum(books_read) / len(books_read), 1)
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des tendances de lecture: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6000))
    app.run(host="0.0.0.0", port=port, debug=False)