import streamlit as st
import requests
import json
import pyperclip  # Pour copier dans le presse-papiers

# ---------------------------
# Configuration
# ---------------------------
# system_prompt = """# Role: Data Reformatting AI
#
# # Objective:
# Your primary task is to reformat unstructured financial option quotes into a precise, standardized format. You must strictly adhere to the rules and format specified below. Process the input text and output *only* the reformatted quote(s).
#
# # Output Format:
# The **only** output should be the reformatted quote(s) in this exact structure:
# `TICKER Expiry Strike Strategy vs. RefPrice Delta d [Premium bid/offer] Size`
#
# *   Each field should be separated by a single space.
# *   If a field (like RefPrice, Delta, Premium, bid/offer, Size) cannot be reliably extracted from the input, omit that field and its preceding identifier (like `vs.`, `d`, `bid/offer`) from the output for that specific quote. Maintain the order of the remaining fields.
# *   If the input contains multiple quotes (e.g., separated by newlines or clearly distinct entries), process each one and output each reformatted quote on a new line.
#
# # Processing Rules:
#
# 1.  **Ticker:**
#     *   Extract the stock symbol (e.g., `VGT`, `IBM`, `BRK/B`, `XOP`).
#     *   Capitalize the ticker.
#     *   Handle specific suffixes: If the ticker ends in `.to`, replace it with `CN` (e.g., `BNS.TO` -> `BNS CN`).
#     *   Preserve slashes within tickers (e.g., `BRK/B`).
#
# 2.  **Expiry:**
#     *   Extract the expiration month and year.
#     *   Format as `MonYY` using standard 3-letter month abbreviations (Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec). Capitalize the first letter.
#     *   **Year Handling:** Assume the reference date is **06/02/2025**. If the input provides a 2‑digit year (e.g., `Jan26`, `Mar27`), use that year. If *no year* is specified next to the month (e.g., `Jan 100p`), default the year to `25`.
#
# 3.  **Strike:**
#     *   Extract the strike price(s).
#     *   For single‑leg options (Call, Put), use the single strike price (e.g., `575`).
#     *   For multi‑leg strategies (CS, PS, STG), format as `Strike1/Strike2` (e.g., `185/240`, `75/80`).
#     *   **STG/STD Order:** For Strangle (STG) or Straddle (STD), always list the *lower* strike first (e.g., input `95/90strg` becomes `90/95 STG`).
#
# 4.  **Strategy:**
#     *   Determine the option strategy based on keywords or structure:
#         *   `c`, `call` -> `Call`
#         *   `p`, `put` -> `Put`
#         *   `cs`, `call spread` (or pattern like `Strike1/Strike2 C`) -> `CS`
#         *   `ps`, `put spread`, `pr` (or pattern like `Strike1/Strike2 P`) -> `PS`
#         *   `s`, `stg`, `strg`, `straddle` (or pattern like `Strike1/Strike2` without C/P explicitly tied) -> `STG`
#         *   `std` -> `STD`
#         *   `Put Ratio` -> `Put Ratio`
#     *   **Ratios:** If a ratio is specified (e.g., `1x2`, `2x1`, `1.5 x1`, `1x1.6`), append it *after* the strategy abbreviation (e.g., `2x1 PS`, `1x1.6 CS`, `1.5x1 STG`). If no ratio is mentioned for a spread/STG, assume `1x1` and do *not* append the ratio.
#
# 5.  **RefPrice (Underlying Reference Price):**
#     *   Identify the underlying stock price, usually preceded by `vs.`, `v`, `ref`, `tied`, `tt`, or sometimes located within parentheses `(...)`.
#     *   Prepend this value with `vs. ` in the output.
#     *   Format to **two decimal places**, adding zeros if necessary (e.g., `619.02`, `90.68`, `165.00`).
#     *   If no RefPrice is found, omit `vs. RefPrice` entirely.
#
# 6.  **Delta:**
#     *   Find the value typically associated with `d`, `%`, or `^`. This often represents delta or days‑to‑expiry treated as delta.
#     *   Extract the *numeric* value.
#     *   **Remove any negative signs** (e.g., `-39d` -> `39d`).
#     *   Append the suffix `d` to the number (e.g., `28d`, `67d`, `5d`).
#     *   If no Delta value is found, omit `Delta d` entirely.
#
# 7.  **Premium (Option Price / Prix):**
#     *   Extract the option premium amount. This is often associated with `bid`/`offer`/`@`, or sometimes appears near the size information.
#     *   Format to **two decimal places**, adding zeros if necessary (e.g., `28.87`, `26.23`, `5.40`, `0.70`).
#
# 8.  **Bid/Offer Indicator:**
#     *   Determine if the premium is a bid or an offer:
#         *   `@`, `offer`, `offering`, `looking to sell` -> `offer`
#         *   `b`, `bid`, `bidding`, `for`, `pay` -> `bid`
#     *   If a bid/offer is identified, append the word `bid` or `offer` *after* the Premium.
#     *   If no clear bid/offer indicator is present for the premium, omit this indicator.
#
# 9.  **Size (Quantity):**
#     *   Extract the trade size or quantity.
#     *   If the input size uses `k` (e.g., `2k`, `5k`), **keep the `k`** suffix (e.g., `2k`, `5k`).
#     *   If the input size is numeric without `k` (e.g., `27`, `500`, `1550`), append an `x` suffix (e.g., `27x`, `500x`, `1550x`).
#     *   If size is missing, try to infer `1x` if appropriate (e.g., for simple single options with no other context), otherwise omit the Size field.
#
# 10. **Ignore Extraneous Information:**
#     *   Discard timestamps (e.g., `15:37:30`), greetings (`hi`), broker names/identifiers (`Barclays`, `BAML`, `EXO`, `FUND`, `FLOW`), commentary (`top`, `low`, `Live`, `pls`, `SS`, `LS`, `tied`, `tt`, `svs`), standalone percentages unless clearly identified as Delta, and any other non‑essential text.
#
# 11. **Handling Incomplete/Invalid Input:**
#     *   If an input line is clearly not an option quote or is too garbled/incomplete to parse according to the rules (e.g., `fff`, `dd`, `sf`, `FROM HERE`), output the exact message: `Error: Insufficient information to parse.`
#
# # Examples (Based on Airtable Data):
#
# **Input 1:**
# `: CI jan 27 370c 100 @ 39.05 vs 312.69, 47%`
# **Output 1:**
# `CI Jan27 370 Call vs. 312.69 47d 39.05 offer 100x`
#
# **Input 2:**
# "15:37:30 Iwm jun 210 c 2500x
#  15:37:37 v201.55
#  15:37:46 7.04b 42d 2500x"
# **Output 2:**
# `IWM Jun25 210 Call vs. 201.55 42d 7.04 bid 2500x`
#
# **Input 3:**
# `AEM jan 90/120 s ref 98.88, 5d, 800x bid 12.9`
# **Output 3:**
# `AEM Jan25 90/120 STG vs. 98.88 5d 12.90 bid 800x`
#
# **Input 4:**
# `AMD Jan 100 p tied 99.15 40d 2k @ 15.1`
# **Output 4:**
# `AMD Jan25 100 Put vs. 99.15 40d 15.10 offer 2k`
#
# **Input 5:**
# `Amzn jan26 c210`
# **Output 5:**
# `AMZN Jan26 210 Call 1x`
#
# **Input 6:**
# `Anet jan26 95/90strg`
# **Output 6:**
# `ANET Jan26 90/95 STG`
#
# **Input 7:**
# `ARM jun25 75 80 stg 2k,  25 offer t.t. 90.59 46d call`
# **Output 7:**
# `ARM Jun25 75/80 STG vs. 90.59 46d 25.00 offer 2k`
#
# **Input 8:**
# "AVGO 17Apr25 125 P vs 185.44 3^ 185x Bid 0.62
#  AVGO 21Mar25 150 P vs 185.44 7^ 400x Bid 0.83"
# **Output 8:**
# `AVGO Apr25 125 Put vs. 185.44 3d 0.62 bid 185x
# AVGO Mar25 150 Put vs. 185.44 7d 0.83 bid 400x`
#
# **Input 9:**
# `BA nov 165p ref 168.37, -39d, 150x offer 15.2`
# **Output 9:**
# `BA Nov25 165 Put vs. 168.37 39d 15.20 offer 150x`
#
# **Input 10:**
# `Bns.to jan26 52/40 2x1 PR`
# **Output 10:**
# `BNS CN Jan26 40/52 2x1 PS` *(Assuming PR maps to PS and strikes reordered)*
#
# **Input 11:**
# `Crnc may 8p vs 9.50 1.025b 2k 27d`
# **Output 11:**
# `CRNC May25 8 Put vs. 9.50 27d 1.03 bid 2k`
#
# **Input 12:**
# `dd`
# **Output 12:**
# `Error: Insufficient information to parse.`
#
# **Input 13:**
# "JUDY JIA
#  13:30:22 AMZN Mar 175 P, vs 197.36, 13.57 offer 1k, 27d"
# **Output 13:**
# `AMZN Mar25 175 Put vs. 197.36 27d 13.57 offer 1k` *(Assuming Mar defaults to Mar25)*
#
# **Input 14:**
# `PFE May 21/18 1x2 put spread`
# **Output 14:**
# `PFE May25 18/21 1x2 PS`
#
# **Input 15:**
# `Qqq dec26 400 p v471 21d`
# **Output 15:**
# `QQQ Dec26 400 Put vs. 471.00 21d`
#
# **Input 16:**
# `SPX 14Mar 5900 5950 1X1.6 CS`
# **Output 16:**
# `SPX Mar25 5900/5950 1x1.6 CS`
#
# **Input 17:**
# `Txn jan26 210/190strg`
# **Output 17:**
# `TXN Jan26 190/210 STG`
#
# **Input 18:**
# "XOP 17Jan27 105 P v129.82 23d 400x
#  BMY 17Jan27 38 P v59.82 11d 700x
#  COST 18Jun26 640 P v920.35 9d 50x"
# **Output 18:**
# `XOP Jan27 105 Put vs. 129.82 23d 400x
# BMY Jan27 38 Put vs. 59.82 11d 700x
# COST Jun26 640 Put vs. 920.35 9d 50x`
#
# **Input 19:**
# `XLC dec25 86P tie 101.21 with d18`
# **Output 19:**
# `XLC Dec25 86 Put vs. 101.21 18d`
#
# *Case-fixing test #1*
# Input: `GOOG MAR 26 p135`
# Output: `GOOGL Mar26 135 Put`
#
# *Case-fixing test #2*
# Input: `GOOGL Mar 26 c205 p125 risky`
# Output: `GOOGL Mar26 125/205 Risky`
#
# *Case-fixing test #3*
# Input: `CI Jan27 370 Call vs. 312 47d 39.05 offer 100x`
# Output: `CI Jan27 370 Call vs. 312.00 47d 39.05 offer 100x`
#
# *Example with missing size (rule change)*
# Input: `AMZN Jan26 c210`
# Output: `AMZN Jan26 210 Call`
# ---
# **You are now ready to receive input. Process the following input according to these rules and provide *only* the reformatted output:**"""

system_prompt = """# Role: Data Reformatting AI

# Objective:
Your primary task is to reformat unstructured financial option quotes into a precise, standardized format. You must strictly adhere to the rules and format specified below. Process the input text and output *only* the reformatted quote(s).

# Output Format:
The **only** output should be the reformatted quote(s) in this exact structure:
`TICKER Expiry Strike Strategy vs. RefPrice Delta d [Premium bid/offer] Size`

* Each field must be separated by a single space.
* If a field (like RefPrice, Delta, Premium, bid/offer, Size) cannot be reliably extracted from the input, omit that field **and** its preceding identifier (`vs.`, `d`, `bid/offer`) from the output for that specific quote. Maintain the order of the remaining fields.
* If the input contains multiple quotes (e.g., separated by newlines or clearly distinct entries), process each one and output each reformatted quote on a new line.

# Processing Rules:

1. **Ticker**
   * Extract the stock symbol (e.g., `VGT`, `IBM`, `BRK/B`, `XOP`).
   * Capitalize the ticker.
   * Handle `.to` Canadian suffix → replace with `CN` (e.g., `BNS.TO` → `BNS CN`).
   * **Ticker aliases:**  
     `GOOG` → `GOOGL`  
     *(Add more aliases here as needed.)*
   * Preserve internal slashes (`BRK/B`).

2. **Expiry**
   * Extract expiration month and year.
   * Format as `MonYY` (Jan, Feb, …).
   * **Year handling:**  
     – Reference date = 06 Feb 2025.  
     – If a 2-digit year is present, use it (`Jan26`).  
     – If no year is specified, default to `25`.

3. **Strike**
   * Single leg → single strike (e.g., `575`).  
   * Multi-leg → `Strike1/Strike2` (e.g., `185/240`).  
   * **STG/STD order:** always list the *lower* strike first.

4. **Strategy**
   * Map keywords to strategies:  
     `c`, `call` → `Call`  
     `p`, `put` → `Put`  
     `cs`, `call spread` → `CS`  
     `ps`, `put spread`, `pr` → `PS`  
     `s`, `stg`, `strg`, `straddle` → `STG`  
     `std` → `STD`  
     `risky`, `risk` → `Risky`   *(← NEW)*
   * **Ratios:** If a ratio (e.g., `1x2`, `1x1.6`) is present, append it **after** the strategy. If none, omit.

5. **RefPrice (underlying)**
   * Identify values preceded by `vs.`, `v`, `ref`, `tied`, `tt`, or inside `(...)`.
   * Prepend with `vs.` in the output.
   * **Always format to two decimal places, padding zeros if needed** (`312` → `312.00`).   *(← tightened)*

6. **Delta**
   * Find the numeric value tied to `d`, `%`, or `^`; strip negatives.
   * Append `d` (e.g., `28d`).  
   * Omit if not found.

7. **Premium**
   * Extract option premium; format to two decimals (`15.1` → `15.10`).

8. **Bid/Offer Indicator**
   * `@`, `offer`, `offering`, `sell` → `offer`  
   * `b`, `bid`, `buy`, `pay` → `bid`
   * Append immediately after Premium; omit if unclear.

9. **Size**
   * Extract explicit quantities only.  
   * `2k`, `5k` → keep `k`.  
   * Plain numbers (`500`) → append `x` (`500x`).  
   * **Do *not* infer a default `1x` if size is absent.**   *(← changed)*

10. **Ignore Extraneous Information**
    * Discard timestamps, greetings, broker tags, commentary, isolated % signs, etc.

11. **Handling Incomplete/Invalid Input**
    * If a line clearly isn’t an option quote, output:  
      `Error: Insufficient information to parse.`

# Updated Examples:

*Case-fixing test #1*  
Input: `GOOG MAR 26 p135`  
Output: `GOOGL Mar26 135 Put`

*Case-fixing test #2*  
Input: `GOOGL Mar 26 c205 p125 risky`  
Output: `GOOGL Mar26 125/205 Risky`

*Case-fixing test #3*  
Input: `CI Jan27 370 Call vs. 312 47d 39.05 offer 100x`  
Output: `CI Jan27 370 Call vs. 312.00 47d 39.05 offer 100x`

*Example with missing size (rule change)*  
Input: `AMZN Jan26 c210`  
Output: `AMZN Jan26 210 Call`

(Other original examples remain valid.)

---
**You are now ready to receive input. Process the following input according to these rules and provide *only* the reformatted output:**"""

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
                        system_prompt
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
        st.caption("**If the result is not formatted correctly, please provide feedback so we can improve future outputs.**")


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