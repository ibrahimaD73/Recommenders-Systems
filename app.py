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
import pickle
from pathlib import Path

from google import genai
from google.genai import types

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

load_dotenv()
logger.add("pipeline.log", rotation="500 MB", level="INFO")

app = Flask(__name__)

# Vérification de la clé API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning("GEMINI_API_KEY manquante ! Configure-la dans .env ou Codespaces Secrets")
    client = None
else:
    client = genai.Client(api_key=api_key)

GEMINI_MODEL = "gemini-2.0-flash"

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------
# DATA - Chargement optimisé
# ---------------------------------------------------

def load_data():
    """Charge les données avec colonnes minimales."""
    csv_path = DATA_DIR / "preprocessed_data.csv"
    
    df = pd.read_csv(csv_path)
    
    # Colonnes nécessaires
    required_cols = [
        "ISBN", "Book-Title", "Book-Author",
        "Image-URL-L", "Year-Of-Publication",
        "Book-Rating", "content"
    ]
    
    # Garder seulement les colonnes qui existent
    existing_cols = [col for col in required_cols if col in df.columns]
    df = df[existing_cols]
    
    # Pré-calcul pour recherche rapide
    df["_title_lower"] = df["Book-Title"].astype(str).str.lower()
    df["_author_lower"] = df["Book-Author"].astype(str).str.lower()
    
    logger.info(f"Data loaded: {df.shape}")
    return df


def load_or_build_tfidf(df):
    """Charge le TF-IDF depuis le cache ou le reconstruit."""
    tfidf_path = CACHE_DIR / "tfidf_matrix.pkl"
    vectorizer_path = CACHE_DIR / "tfidf_vectorizer.pkl"
    
    if tfidf_path.exists() and vectorizer_path.exists():
        logger.info("Loading TF-IDF from cache")
        with open(tfidf_path, "rb") as f:
            matrix = pickle.load(f)
        with open(vectorizer_path, "rb") as f:
            vectorizer = pickle.load(f)
        return vectorizer, matrix
    
    logger.info("Building TF-IDF matrix...")
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=10000,
        ngram_range=(1, 2)
    )
    
    content_col = df["content"].fillna("") if "content" in df.columns else pd.Series([""] * len(df))
    matrix = vectorizer.fit_transform(content_col)
    
    # Sauvegarde cache
    with open(tfidf_path, "wb") as f:
        pickle.dump(matrix, f)
    with open(vectorizer_path, "wb") as f:
        pickle.dump(vectorizer, f)
    
    return vectorizer, matrix


# Chargement au démarrage
books_df = load_data()
tfidf, tfidf_matrix = load_or_build_tfidf(books_df)

# Pré-calcul des top books
TOP_BOOKS = books_df.nlargest(5, "Book-Rating")[["Book-Title", "Book-Rating"]].copy()

# ---------------------------------------------------
# HELPERS - Optimisés
# ---------------------------------------------------

GREETINGS_PATTERN = re.compile(
    r"^(hello|hi|salut|bonjour|bonsoir|coucou|hey|yo)$",
    re.IGNORECASE
)


def is_greeting(text: str) -> bool:
    return bool(GREETINGS_PATTERN.match(text.strip()))


def safe_str(value) -> str:
    """Convertit une valeur en string, gère les NaN."""
    if pd.isna(value):
        return ""
    return str(value)


def safe_int(value, default: int = 0) -> int:
    """Convertit une valeur en int, gère les NaN."""
    try:
        if pd.isna(value):
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """Convertit une valeur en float, gère les NaN."""
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def format_book_record(row) -> dict:
    """Formate une ligne DataFrame en dictionnaire JSON-safe."""
    return {
        "ISBN": safe_str(row.get("ISBN", "")),
        "Book-Title": safe_str(row.get("Book-Title", "")),
        "Book-Author": safe_str(row.get("Book-Author", "")),
        "Image-URL-L": safe_str(row.get("Image-URL-L", "")),
        "Year-Of-Publication": safe_int(row.get("Year-Of-Publication", 0)),
        "Book-Rating": safe_float(row.get("Book-Rating", 0))
    }


def search_by_title_or_author(query: str, limit: int = 20) -> list:
    """Recherche optimisée avec colonnes pré-calculées."""
    q = query.lower()
    
    mask = (
        books_df["_title_lower"].str.contains(q, na=False, regex=False) |
        books_df["_author_lower"].str.contains(q, na=False, regex=False)
    )
    
    results = (
        books_df.loc[mask]
        .drop_duplicates(subset="Book-Title")
        .nlargest(limit, "Book-Rating")
    )
    
    return [format_book_record(row) for _, row in results.iterrows()]


# Commentaires pré-définis
RATING_COMMENTS = [
    (4.5, "Un véritable chef-d'œuvre."),
    (4.0, "Très apprécié par les lecteurs."),
    (3.5, "Une lecture agréable et intéressante."),
    (3.0, "Un livre correct qui peut surprendre."),
    (0, "Un livre au style particulier.")
]


def get_rating_comment(rating: float) -> str:
    for threshold, comment in RATING_COMMENTS:
        if rating >= threshold:
            return comment
    return RATING_COMMENTS[-1][1]


def get_book_recommendations_list(query: str, n: int = 5) -> list:
    """Retourne une liste de recommandations (pour /search)."""
    query_vec = tfidf.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    
    # Top N+5 pour avoir de la marge après déduplication
    top_count = min(n + 5, len(similarities))
    indices = np.argpartition(similarities, -top_count)[-top_count:]
    indices = indices[np.argsort(similarities[indices])[::-1]]
    
    seen_titles = set()
    results = []
    
    for idx in indices:
        if len(results) >= n:
            break
        
        row = books_df.iloc[idx]
        title = safe_str(row["Book-Title"])
        
        if title in seen_titles or not title:
            continue
        seen_titles.add(title)
        
        book = format_book_record(row)
        book["comment"] = get_rating_comment(book["Book-Rating"])
        results.append(book)
    
    return results


@lru_cache(maxsize=200)
def get_book_recommendations(query: str, n: int = 5) -> tuple:
    """Retourne un tuple (hashable pour cache) - pour /chatbot."""
    return tuple(get_book_recommendations_list(query, n))


# ---------------------------------------------------
# GEMINI - Prompt optimisé
# ---------------------------------------------------

SYSTEM_PROMPT = """Tu es un libraire passionné. Réponds de façon concise et chaleureuse.
Format: intro courte → 1 phrase par livre → question finale."""


def generate_chatbot_response(user_input: str, recommendations: tuple) -> str:
    """Génère une réponse avec prompt minimaliste."""
    
    if not client:
        return "📚 Voici mes suggestions ! (API non configurée)"
    
    books_list = " | ".join(
        f"{b['Book-Title']} ({b['Book-Author']})"
        for b in recommendations
    )
    
    prompt = f"{SYSTEM_PROMPT}\n\nClient: {user_input}\nLivres: {books_list}"
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=300,
                temperature=0.7
            )
        )
        return response.text.strip()
    
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "📚 Voici mes suggestions ! Dites-moi vos préférences pour affiner."


# ---------------------------------------------------
# ROUTES
# ---------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    """Évite les erreurs 404 pour favicon."""
    return "", 204


@app.route("/search", methods=["POST"])
def search():
    """
    Route de recherche - retourne directement un tableau
    (format attendu par le frontend: data.length > 0)
    """
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    
    logger.debug(f"Search query: {query}")
    
    if not query:
        return jsonify([])
    
    # 1. Recherche par titre/auteur
    books = search_by_title_or_author(query)
    
    # 2. Si pas de résultats, fallback vers recommandations TF-IDF
    if not books:
        logger.debug(f"No exact match, using TF-IDF recommendations for: {query}")
        books = get_book_recommendations_list(query, n=10)
    
    return jsonify(books)


@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "").strip()
    
    logger.debug(f"Chatbot message: {user_input}")
    
    if not user_input:
        return jsonify({
            "response": "Pouvez-vous préciser votre recherche ? 😊",
            "books": []
        }), 400

    # Salutation
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

    # Recherche auteur/titre
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

    # Recommandations IA
    recommendations = get_book_recommendations(user_input)
    response = generate_chatbot_response(user_input, recommendations)
    
    return jsonify({
        "response": response,
        "books": list(recommendations)
    })


# ---------------------------------------------------
# STATS
# ---------------------------------------------------

@app.route("/top_rated_books")
def top_rated_books():
    return jsonify({
        "labels": [safe_str(t) for t in TOP_BOOKS["Book-Title"].tolist()],
        "values": [safe_float(v) for v in TOP_BOOKS["Book-Rating"].tolist()]
    })


@app.route("/popular_genres")
def popular_genres():
    return jsonify({
        "labels": ["Fiction", "Non-fiction", "SF", "Romance", "Thriller"],
        "values": [40, 30, 15, 10, 5],
        "percentages": [40.0, 30.0, 15.0, 10.0, 5.0]
    })


@app.route("/reading_trends")
def reading_trends():
    values = [50, 60, 55, 70, 65, 80]
    return jsonify({
        "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "values": values,
        "average": 63.3
    })


@app.route("/top_read_by_country")
def top_read_by_country():
    """Stats fictives par pays."""
    return jsonify({
        "labels": ["France", "USA", "UK", "Germany", "Spain"],
        "values": [450, 380, 290, 220, 180]
    })


# ---------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------

@app.route("/health")
def health():
    """Endpoint de santé pour monitoring."""
    return jsonify({
        "status": "ok",
        "books_count": len(books_df),
        "gemini_configured": client is not None
    })


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6000))
    app.run(host="0.0.0.0", port=port, debug=False)