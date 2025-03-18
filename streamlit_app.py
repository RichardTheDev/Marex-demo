import streamlit as st
import requests
import json
import pyperclip  # Pour copier dans le presse-papiers

# ---------------------------
# Configuration
# ---------------------------

st.set_page_config(page_title="Demo - Reformatting Quotes Marex", layout="centered")
st.title("📊 Reformatting Quotes Marex")

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Airtable constants (replace or secure them in st.secrets):
AIRTABLE_URL = "https://api.airtable.com/v0/appP9tzvyjzRcLRhg/tblCCkRz7cBUClFy4"
AIRTABLE_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {st.secrets['AIRTABLE']}",
    "Cookie": "brw=brwXn8HZvgXvXmpBG; brwConsent=opt-out; AWSALBTG=YfGSFlWRkjpgu4WKCU7PykwJcL4isWnGit3xTpHsTHdtAMUbl2L8Ze0Hu94pY5jddmf1r/W/7vAATLRd1V3zGnbVDSO8HcwSVKMfaStkpSBs3D5PSs+QM5HjfqjBD0g2l7Z8Hb0qVDijKa20o2BVqE8h3/9qWW1tN0T3q5+eC0QZ2lIW74s=; AWSALBTGCORS=YfGSFlWRkjpgu4WKCU7PykwJcL4isWnGit3xTpHsTHdtAMUbl2L8Ze0Hu94pY5jddmf1r/W/7vAATLRd1V3zGnbVDSO8HcwSVKMfaStkpSBs3D5PSs+QM5HjfqjBD0g2l7Z8Hb0qVDijKa20o2BVqE8h3/9qWW1tN0T3q5+eC0QZ2lIW74s="
}


# ---------------------------
# Helper functions
# ---------------------------

def send_to_airtable(input_text: str, output_text: str, thumbs_value: str):
    """
    Create a new record in Airtable with the given fields.
    thumbs_value should be "true", "false", or "" (if empty).
    """
    data = {
        "records": [
            {
                "fields": {
                    "input": input_text,
                    "output": output_text,
                    "thumbs": thumbs_value
                }
            }
        ]
    }
    try:
        resp = requests.post(AIRTABLE_URL, headers=AIRTABLE_HEADERS, json=data)
        resp.raise_for_status()
    except Exception as e:
        st.error(f"Erreur lors de l'envoi à Airtable : {e}")


# ---------------------------
# Main app
# ---------------------------

# We use st.session_state to store the last reformatted_quote and user_input
# so we can access them again if the user clicks thumbs-up/down
if "reformatted_quote" not in st.session_state:
    st.session_state["reformatted_quote"] = ""
if "last_input" not in st.session_state:
    st.session_state["last_input"] = ""

# Form allows user to press enter/submit
with st.form("quote_form", clear_on_submit=False):
    user_input = st.text_area("✍️ Entrez la quote à reformater :", height=100)
    submitted = st.form_submit_button("🚀 Reformater")

if submitted:
    # If user tried to submit with empty
    if not user_input.strip():
        st.warning("Veuillez entrer une quote avant de soumettre.")
    else:
        # Store in session state
        st.session_state["last_input"] = user_input

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
                    "content": (
                        "You get the output show only the output\n"
                        "I need you to reformat the quotes like this :\n"
                        "Ticker / Expiry / Strike / Strategy / Ref/ Delta / Prix / Size\n"
                        "All the options Strategy: Call/Put/CS/PS/STG/STD\n"
                        "If its \"@\" = offer\n"
                        "if its \"pay\" or \"bid\" or \"bidding\" or \"for\" = \"bid\"\n"
                        "The date today is 06/02/2025 if next to the expiry there is no date put 25\n"
                        "The price must be precise to the hundredth of a unit; add zeros if necessary.\n"
                        "Some exemples :\n"
                        "1- INPUT : Vgt jan 575p tt 619.02 27x 28d @28.87\n"
                        "   OUTPUT :VGT Jan26 575 Put vs. 619.02 28d 28.87 offer 27x\n"
                        "2- INPUT : IBM Jul 25 250c--500 at 26.23 vs 262.78 on a 67\n"
                        "   OUTPUT: IBM Jul25 250 Call vs. 262.78 67d 26.23 offer 500x\n"
                        "Here are other wihtout offer \n"
                        "ABT Jan 125 Put vs. 138.05 26d @ 5.40 EXO\n"
                        "ABBV Mar26 185/240 STG vs. 210.21 9d @ 20.10 EXO\n"
                        "LLY Jul 950 Call vs. 913.27 49d @ 65.70 FUND\n"
                        "LULU Jun 400 Call vs. 342.36 32d @ 15.45 FUND\n"
                        "IBN Mar 27 Put vs. 27.75 30d @ 0.24  FLOW\n"
                        "AVGO Jan 150/255 1.5 x1 STG vs. 187.83 2d/p @ 31.15 EXO\n"
                        "COF Jun26 185 Put vs. 182.68 41d @ 25.55 EXO\n"
                        "WFC Mar26 75/80 STG Live @15.80 EXO\n"
                        "INTC Jan 18/28 1.5 x1 STG vs. 20.41 7d/p @ 5.42 EXO\n"
                        "CRWD Mar26 400/440 STG vs. 357.45 4d/p @125.60 EXO\n"
                        "MDB Mar 200 Put vs. 257.3"
                        "Other examples : "
                        "Input:"
                        """XOP 17Jan27 105 P v129.82 23d 400x
                        BMY 17Jan27 38 P v59.82 11d 700x
                        COST 18Jun26 640 P v920.35 9d 50x
                        XLF 17Jan27 39 P v49.23 15d 600x
                        DIS 17Jan27 80 P v99.89 19d 500x
                        XLI 17Jan27 95 P v133.41 8d 400x
                        XLV 17Jan27 110 P v146.88 6d 1000x"""
                        """Output:\n
                        XOP Jan27 105 Put vs.129.82 23d  400x\n
                        BMY Jan27 38 Put vs.59.82 11d 700x\n
                        COST Jun26 640 Put vs.920.35 9d 50x\n
                        XLF Jan27 39 Put vs.49.23 15d 600x\n
                        DIS Jan27 80 Put vs.99.89 19d 500x\n
                        XLI Jan27 95 Put vs.133.41 8d 400x\n
                        XLV Jan27 110 Put vs.146.88 6d 1000x"""
                    )
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

        # Call OpenAI
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response_data = response.json()

            if "choices" in response_data:
                reformatted_quote = response_data["choices"][0]["message"]["content"]
                st.session_state["reformatted_quote"] = reformatted_quote

                st.success("✅ Reformattage réussi ! Voici la quote :")
                st.code(reformatted_quote, language="markdown")

                # # Copy button
                # if st.button("📋 Copier le résultat"):
                #     pyperclip.copy(reformatted_quote)
                #     st.success("Texte copié dans le presse-papiers !")

                # 3) Always send the input with blank fields to Airtable
                send_to_airtable(user_input, "", "")

            else:
                st.error("❌ Erreur : Impossible d'obtenir une réponse de l'API.")
        except Exception as e:
            st.error(f"Erreur lors de la requête API : {e}")


# If there's a reformatted quote, show thumbs up/down
if st.session_state["reformatted_quote"]:
    # Create three columns: one for the label, then thumbs-up, then thumbs-down
    col_text, col_up, col_down = st.columns([2, 1, 1])

    with col_text:
        st.write("**Was this helpful?**")

    with col_up:
        if st.button("👍"):
            # Send thumbs-up to Airtable
            send_to_airtable(
                st.session_state["last_input"],
                st.session_state["reformatted_quote"],
                "true"
            )
            st.success("Merci pour votre feedback (👍) !")

    with col_down:
        if st.button("👎"):
            # Send thumbs-down to Airtable
            send_to_airtable(
                st.session_state["last_input"],
                st.session_state["reformatted_quote"],
                "false"
            )
            st.warning("Merci pour votre feedback (👎) !")