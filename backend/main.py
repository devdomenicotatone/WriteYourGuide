import os
import requests
import logging
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from utils import perform_search, scrape_article
import openai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY non impostata.")
    raise RuntimeError("OPENAI_API_KEY non impostata.")

if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    logger.error("GOOGLE_API_KEY o GOOGLE_CSE_ID non impostate.")
    raise RuntimeError("GOOGLE_API_KEY o GOOGLE_CSE_ID non impostate.")

openai.api_key = OPENAI_API_KEY

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateArticleRequest(BaseModel):
    query: str

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello World from FastAPI!"}

@app.get("/search")
def search_endpoint(query: str):
    if not query.strip():
        logger.warning("Empty query received in /search endpoint")
        raise HTTPException(status_code=400, detail="La query di ricerca non può essere vuota.")

    logger.info(f"Search endpoint called with query: {query}")
    try:
        # Modifichiamo la query includendo il sito di GetYourGuide
        site_query = f"site:https://www.getyourguide.it/ {query}"
        data = perform_search(site_query)
        return data
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Errore durante la ricerca")

@app.post("/generate_article")
def generate_article(payload: GenerateArticleRequest):
    original_query = payload.query.strip()
    if not original_query:
        logger.warning("Empty query received")
        raise HTTPException(status_code=400, detail="La query di ricerca non può essere vuota.")

    logger.info(f"generate_article endpoint called with query: {original_query}")

    # Trasformiamo la query per cercare su GetYourGuide
    query = f"site:https://www.getyourguide.it/ {original_query}"

    try:
        search_results = perform_search(query=query)
    except Exception as e:
        logger.error(f"Error during search: {e}")
        raise HTTPException(status_code=500, detail="Errore durante la ricerca")

    items = search_results.get("items", [])
    if not items:
        logger.warning("No results found for the query")
        raise HTTPException(status_code=404, detail="Nessun risultato trovato per la query.")

    # Consideriamo i primi 10 risultati
    top_items = items[:10]
    logger.info(f"Processing top {len(top_items)} results")

    risultati = []
    immagini_globali = []

    for index, item in enumerate(top_items, start=1):
        link = item.get("link")
        if not link:
            logger.warning(f"Result {index} has no valid link, skipping")
            continue
        logger.info(f"Scraping result {index}: {link}")
        article_text, immagini = scrape_article(link)

        # Aggiungiamo le immagini trovate alla lista globale
        immagini_globali.extend(immagini)

        if article_text:
            # Prompt per OpenAI: rielaborare il contenuto come un copywriter professionale
            prompt_message = (
                "Sei un esperto copywriter. Di seguito troverai il contenuto di una guida estratta dal sito GetYourGuide. "
                "Usa parole differenti ma mantieni le informazioni veritiere. Crea un contenuto composto da un titolo (h2) "
                "e da un paragrafo che descriva accuratamente le informazioni, senza citare fonti, URL o nomi di marchi. "
                "Non menzionare 'GetYourGuide'. Il risultato deve essere autonomamente comprensibile e professionale.\n\n"
                f"Testo originale:\n{article_text}\n\n"
                "Ora genera il tuo risultato con un h2 e un paragrafo:"
            )

            try:
                logger.info(f"Sending text to OpenAI for re-elaboration (result {index})")
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Sei un assistente che crea contenuti di copywriting professionali."},
                        {"role": "user", "content": prompt_message}
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                )
                generated_text = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Error generating rewritten text for article {index}: {e}")
                continue

            # Cerchiamo di separare l'H2 dal paragrafo. L'utente potrebbe aver generato un testo con un h2 e poi un paragrafo.
            # Supponiamo che l'H2 sia la prima linea o il primo titolo.
            # In caso il modello non segua esattamente le istruzioni, tentiamo alcune euristiche.
            lines = generated_text.split("\n")
            titolo = ""
            contenuto = ""
            # Cerchiamo la prima riga che potrebbe essere un h2
            # Esempio: se il modello ha generato: "## Titolo\nParagrafo...", lo convertiamo in <h2>
            # Se non c'è markup, prendiamo la prima riga come titolo e il resto come paragrafo.
            if lines:
                # Trova la prima linea non vuota per titolo
                for i, l in enumerate(lines):
                    clean_line = l.strip()
                    if clean_line:
                        titolo = clean_line
                        # Rimuovi eventuali markdown di h2
                        if titolo.startswith("##"):
                            titolo = titolo.replace("##", "").strip()
                        elif titolo.startswith("#"):
                            titolo = titolo.replace("#", "").strip()
                        # Il resto delle linee costituisce il paragrafo
                        contenuto = "\n".join(lines[i+1:]).strip()
                        break

            # Se non è riuscito a estrarre, assegniamo comunque qualcosa
            if not titolo:
                titolo = "Informazioni sulla Guida"
            if not contenuto:
                contenuto = generated_text

            risultati.append({
                "titolo": titolo,
                "contenuto": contenuto
            })
        else:
            logger.warning(f"No relevant text extracted from article {index}")

    if not risultati:
        logger.error("No results could be processed successfully")
        raise HTTPException(status_code=500, detail="Non è stato possibile estrarre contenuti rilevanti.")

    # Rimuoviamo eventuali duplicati dalle immagini
    immagini_globali = list(set(immagini_globali))

    return {
        "risultati": risultati,
        "immagini": immagini_globali
    }
