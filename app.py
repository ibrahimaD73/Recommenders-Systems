from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import re
from dotenv import load_dotenv
from loguru import logger
from functools import lru_cache

from google import genai

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

load_dotenv()
logger.add("pipeline.log", rotation="500 MB", level="DEBUG")

app = Flask(__name__)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "gemini-pro-latest"

# ---------------------------------------------------
# DATA
# ---------------------------------------------------

@lru_cache(maxsize=1)
def load_data():
    csv_path = os.path.join(
        os.path.dirname(__file__),
        "data",
        "preprocessed_data.csv"
    )
    df = pd.read_csv(csv_path)
    logger.info(f"Data loaded: {df.shape}")
    return df


books_df = load_data()

# ---------------------------------------------------
# TF-IDF
# ---------------------------------------------------

tfidf = TfidfVectorizer(stop_words="english")
tfidf_matrix = tfidf.fit_transform(books_df["content"].fillna(""))

# ---------------------------------------------------
# HELPERS – INTELLIGENCE
# ---------------------------------------------------

GREETINGS = [
    "hello", "hi", "salut", "bonjour", "bonsoir",
    "coucou", "hey", "yo"
]

def is_greeting(text: str) -> bool:
    text = text.lower().strip()
    return any(re.fullmatch(g, text) for g in GREETINGS)


def search_by_title_or_author(query, limit=20):
    query = query.lower()

    mask = (
        books_df["Book-Title"].str.lower().str.contains(query, na=False) |
        books_df["Book-Author"].str.lower().str.contains(query, na=False)
    )

    results = books_df[mask].drop_duplicates(
        subset="Book-Title"
    ).sort_values("Book-Rating", ascending=False).head(limit)

    return results[[
        "ISBN",
        "Book-Title",
        "Book-Author",
        "Image-URL-L",
        "Year-Of-Publication",
        "Book-Rating"
    ]].to_dict("records")


@lru_cache(maxsize=100)
def get_book_recommendations(query, n=5):
    query_vec = tfidf.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    indices = similarities.argsort()[:-n - 1:-1]

    recommendations = books_df.iloc[indices][[
        "ISBN",
        "Book-Title",
        "Book-Author",
        "Image-URL-L",
        "Year-Of-Publication",
        "Book-Rating"
    ]]

    recommendations = recommendations.drop_duplicates(
        subset="Book-Title"
    ).head(n)

    for idx, book in recommendations.iterrows():
        rating = book["Book-Rating"]

        if rating >= 4.5:
            comment = "Un véritable chef-d'œuvre."
        elif rating >= 4.0:
            comment = "Très apprécié par les lecteurs."
        elif rating >= 3.5:
            comment = "Une lecture agréable et intéressante."
        elif rating >= 3.0:
            comment = "Un livre correct qui peut surprendre."
        else:
            comment = "Un livre au style particulier."

        recommendations.at[idx, "comment"] = comment

    return recommendations.to_dict("records")

# ---------------------------------------------------
# GEMINI RESPONSE
# ---------------------------------------------------

def generate_chatbot_response(user_input, recommendations):
    formatted_recommendations = "\n".join(
        f"• {b['Book-Title']} par {b['Book-Author']} "
        f"({b['Year-Of-Publication']}) – {b['comment']}"
        for b in recommendations
    )

    prompt = f"""
Tu es un libraire passionné, chaleureux et attentif.
Tu conseilles les lecteurs comme dans une vraie librairie.

Demande du client :
{user_input}

Livres proposés :
{formatted_recommendations}

Structure ta réponse ainsi :
1. Une introduction naturelle.
2. Une recommandation personnalisée pour chaque livre.
3. Une question ou une conclusion engageante.
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text.strip()

    except Exception as e:
        logger.exception("Gemini error")
        return (
            "📚 J’ai quelques idées de lecture pour vous, "
            "n’hésitez pas à me dire ce que vous aimez habituellement."
        )

# ---------------------------------------------------
# ROUTES
# ---------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_input = request.json.get("message", "").strip()
    logger.debug(f"User message: {user_input}")

    if not user_input:
        return jsonify({
            "response": "Pouvez-vous préciser votre recherche ? 😊",
            "books": []
        }), 400

    # 1️⃣ Salutation
    if is_greeting(user_input):
        return jsonify({
            "response": (
                "📚 Bonjour et bienvenue !\n\n"
                "Je suis votre libraire virtuel 😊\n"
                "Cherchez-vous un livre précis, un auteur, "
                "ou souhaitez-vous une recommandation ?"
            ),
            "books": []
        })

    # 2️⃣ Auteur / Saga (ex: Harry Potter)
    author_books = search_by_title_or_author(user_input)

    if len(author_books) >= 3:
        return jsonify({
            "response": (
                f"✨ Excellent choix !\n\n"
                f"Voici les livres correspondant à **{user_input}**.\n"
                f"Souhaitez-vous que je vous aide à choisir "
                f"le meilleur tome pour commencer ?"
            ),
            "books": author_books
        })

    # 3️⃣ Recommandation intelligente
    recommendations = get_book_recommendations(user_input)
    response = generate_chatbot_response(user_input, recommendations)

    return jsonify({
        "response": response,
        "books": recommendations
    })


# ---------------------------------------------------
# STATS
# ---------------------------------------------------

@app.route("/top_rated_books")
@lru_cache(maxsize=1)
def top_rated_books():
    top_books = books_df.sort_values(
        "Book-Rating", ascending=False
    ).head(5)

    return jsonify({
        "labels": top_books["Book-Title"].tolist(),
        "values": top_books["Book-Rating"].tolist()
    })


@app.route("/popular_genres")
def popular_genres():
    genres = ["Fiction", "Non-fiction", "Science-fiction", "Romance", "Thriller"]
    popularity = [40, 30, 15, 10, 5]
    total = sum(popularity)

    return jsonify({
        "labels": genres,
        "values": popularity,
        "percentages": [round(x / total * 100, 1) for x in popularity]
    })


@app.route("/reading_trends")
def reading_trends():
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    books_read = [50, 60, 55, 70, 65, 80]

    return jsonify({
        "labels": months,
        "values": books_read,
        "average": round(np.mean(books_read), 1)
    })


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6000))
    app.run(host="0.0.0.0", port=port, debug=False)
