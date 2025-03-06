import streamlit as st
import requests
import json
import pyperclip  # Pour copier dans le presse-papiers

# Clé API OpenAI (à définir dans un fichier .env ou en variable d'environnement)
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Configuration de la page
st.set_page_config(page_title="Demo - Reformatting Quotes Marex", layout="centered")

st.title("📊 Reformatting Quotes Marex")

# Champ de saisie pour l'utilisateur
user_input = st.text_area("✍️ Entrez la quote à reformater :", height=100)

# Bouton d'envoi
if st.button("🚀 Reformater"):
    if not user_input.strip():
        st.warning("Veuillez entrer une quote avant de soumettre.")
    else:
        # Construction de la requête OpenAI
        api_url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": "You get the output show only the output\nI need you to reformat the quotes like this :\nTicker / Expiry / Strike / Strategy / Ref/ Delta / Prix / Size\nAll the options Strategy: Call/Put/CS/PS/STG/STD\nIf its \"@\" = offer\nif its \"pay\" or \"bid\" or \"bidding\" or \"for\" = \"bid\"\nThe date today is 06/02/2025 if next tothe expiry there is no date put 25\nSome exemples : \n1- INPUT : Vgt jan 575p tt 619.02 27x 28d @28.87\n    OUTPUT :VGT Jan26 575 Put vs. 619.02 28d 28.87 offer 27x\n2- INPUT : IBM Jul 25 250c--500 at 26.23 vs 262.78 on a 67\nOUTPUT: IBM Jul25 250 Call vs. 262.78 67d 26.23 offer 500x\nHere are other wihtout offer \nABT Jan 125 Put vs. 138.05 26d @ 5.40 EXO\n ABBV Mar26 185/240 STG vs. 210.21 9d @ 20.10 EXO\n LLY Jul 950 Call vs. 913.27 49d @ 65.70 FUND\n LULU Jun 400 Call vs. 342.36 32d @ 15.45 FUND\n IBN Mar 27 Put vs. 27.75 30d @ 0.24  FLOW\n AVGO Jan 150/255 1.5 x1 STG vs. 187.83 2d/p @ 31.15 EXO\n COF Jun26 185 Put vs. 182.68 41d @ 25.55 EXO\n WFC Mar26 75/80 STG Live @15.80 EXO\n INTC Jan 18/28 1.5 x1 STG vs. 20.41 7d/p @ 5.42 EXO\n CRWD Mar26 400/440 STG vs. 357.45 4d/p @125.60 EXO\n MDB Mar 200 Put vs. 257.3"
                },
                {
                    "role": "user",
                    "content": f"Now fix this : \nInput : {user_input}"
                }
            ],
            "response_format": {"type": "text"},
            "temperature": 1,
            "max_completion_tokens": 2048,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }

        # Envoi de la requête
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response_data = response.json()

            # Vérification de la réponse
            if "choices" in response_data:
                reformatted_quote = response_data["choices"][0]["message"]["content"]
                st.success("✅ Reformattage réussi ! Voici la quote :")
                st.code(reformatted_quote, language="markdown")

                # Bouton de copie
                if st.button("📋 Copier le résultat"):
                    pyperclip.copy(reformatted_quote)
                    st.success("Texte copié dans le presse-papiers !")

            else:
                st.error("❌ Erreur : Impossible d'obtenir une réponse de l'API.")

        except Exception as e:
            st.error(f"Erreur lors de la requête API : {e}")