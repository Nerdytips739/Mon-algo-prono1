import os
import json
import re
import traceback
from flask import Flask, request, jsonify, render_template_string
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- PROMPT STRICT ---
SYSTEM_PROMPT = """
Tu es NT-ALGO v4. 
Tu dois analyser le match et répondre UNIQUEMENT par un JSON.
Sois critique. Si une équipe a des blessés majeurs, baisse son Trust Score.

Structure JSON OBLIGATOIRE (Respecte les clés exactes) :
{
    "match_title": "Equipe A vs Equipe B",
    "context": {
        "absences": "Lister les absents majeurs ou 'Aucun'",
        "xg_data": "Comparer les xG récents ou 'N/A'",
        "form": "Analyse forme (5 derniers matchs)"
    },
    "predictions": [
        {
            "market": "Vainqueur",
            "selection": "Nom Equipe",
            "proba": "XX%",
            "trust": 8,
            "analysis": "Pourquoi ce choix."
        },
        {
            "market": "Buts",
            "selection": "Over/Under",
            "proba": "XX%",
            "trust": 7,
            "analysis": "Pourquoi ce choix."
        },
        {
            "market": "BTTS",
            "selection": "Oui/Non",
            "proba": "XX%",
            "trust": 6,
            "analysis": "Pourquoi ce choix."
        }
    ],
    "banker": {
        "selection": "Le pari le plus sûr",
        "odds": "1.xx",
        "reason": "Argument clé."
    }
}
"""

def clean_json(text):
    """Fonction de nettoyage agressive pour trouver le JSON"""
    try:
        # On cherche le bloc entre { et }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text
    except:
        return text

def ensure_structure(data):
    """Vérifie que toutes les clés existent pour éviter le crash JS"""
    if "context" not in data:
        data["context"] = {"absences": "Non spécifié", "xg_data": "N/A", "form": "N/A"}
    if "predictions" not in data:
        data["predictions"] = []
    if "banker" not in data:
        data["banker"] = {"selection": "N/A", "odds": "-", "reason": "Données insuffisantes"}
    if "match_title" not in data:
        data["match_title"] = "Match Inconnu"
    return data

def get_ai_prediction(match_name):
    if not api_key:
        return json.dumps({"error": "Clé API manquante"})
    
    try:
        # On utilise le modèle Pro (plus stable pour le JSON que Flash)
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nANALYSE LE MATCH : {match_name}",
            generation_config={"response_mime_type": "application/json"} # Force le mode JSON natif de Google
        )
        
        raw_text = response.text
        json_text = clean_json(raw_text)
        
        # Parsing
        data = json.loads(json_text)
        
        # Sécurisation des données
        data = ensure_structure(data)
        
        return json.dumps(data)

    except Exception as e:
        print(f"ERREUR BACKEND : {traceback.format_exc()}")
        return json.dumps({"error": f"Erreur IA : {str(e)}"})

# --- INTERFACE ---
@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NT-ALGO v4</title>
    <style>
        :root { --bg: #0b1120; --card: #1e293b; --accent: #38bdf8; --text: #e2e8f0; }
        body { background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; padding: 20px; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; }
        
        /* INPUT */
        .search-box { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 15px; border-radius: 10px; border: 1px solid #334155; background: var(--card); color: white; }
        button { padding: 15px 25px; background: var(--accent); border: none; border-radius: 10px; font-weight: bold; cursor: pointer; color: #0f172a; }
        
        /* CARDS */
        .card { background: var(--card); padding: 20px; border-radius: 16px; margin-bottom: 15px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .card-header { font-size: 0.8rem; text-transform: uppercase; color: #94a3b8; margin-bottom: 8px; letter-spacing: 1px; }
        .highlight { color: var(--accent); font-weight: bold; }
        
        /* TRUST BAR */
        .trust-track { background: #334155; height: 6px; border-radius: 3px; margin-top: 8px; overflow: hidden; }
        .trust-bar { height: 100%; transition: width 0.5s ease; }
        
        /* BANKER */
        .banker-box { border: 1px solid #22c55e; background: linear-gradient(180deg, rgba(34,197,94,0.1) 0%, rgba(0,0,0,0) 100%); }
        .banker-tag { background: #22c55e; color: black; font-size: 0.7rem; padding: 3px 8px; border-radius: 4px; font-weight: bold; display: inline-block; margin-bottom: 5px; }

        #error-zone { color: #ef4444; background: rgba(239,68,68,0.1); padding: 15px; border-radius: 10px; margin-top: 20px; display: none; }
        #loader { text-align: center; display: none; margin-top: 20px; font-style: italic; color: #64748b; }
    </style>
</head>
<body>

    <div class="container">
        <h1 style="text-align:center; margin-bottom: 5px;">🧠 NT-ALGO <span style="color:var(--accent)">v4</span></h1>
        <p style="text-align:center; color:#64748b; font-size:0.9rem; margin-bottom:30px;">Algorithme Prédictif Autonome</p>

        <div class="search-box">
            <input type="text" id="matchInput" placeholder="Ex: Real Madrid vs Man City">
            <button onclick="run()">SCAN</button>
        </div>

        <div id="loader">📡 Initialisation du réseau de neurones...</div>
        <div id="error-zone"></div>

        <div id="results" style="display:none;">
            <h2 id="match-title" style="text-align:center; margin-bottom:20px;"></h2>

            <div class="card">
                <div class="card-header">🚑 EFFECTIFS & ABSENCES</div>
                <div id="ctx-absences" style="margin-bottom:10px;"></div>
                <div class="card-header">📊 DATA xG</div>
                <div id="ctx-xg"></div>
            </div>

            <div id="predictions-list"></div>

            <div class="card banker-box">
                <span class="banker-tag">💎 LE BANKER</span>
                <div id="banker-sel" style="font-size:1.3rem; font-weight:800; margin: 5px 0;"></div>
                <div style="font-size:0.9rem; color:#cbd5e1;">Cote estimée : <span id="banker-odds" class="highlight"></span></div>
                <p id="banker-reason" style="font-size:0.9rem; margin-top:10px; color:#94a3b8;"></p>
            </div>
        </div>
    </div>

    <script>
        async function run() {
            const input = document.getElementById('matchInput').value;
            if(!input) return alert("Entre un match !");

            // Reset UI
            document.getElementById('loader').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error-zone').style.display = 'none';

            try {
                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({match: input})
                });

                const jsonResponse = await res.json();

                // Gestion erreur interne Python
                if(jsonResponse.error) {
                    throw new Error(jsonResponse.error);
                }

                // Parsing des données
                let data;
                if (typeof jsonResponse.analysis === 'string') {
                    data = JSON.parse(jsonResponse.analysis);
                } else {
                    data = jsonResponse; // Cas où c'est déjà un objet
                }

                // --- REMPLISSAGE SÉCURISÉ (Le fameux correctif) ---
                // On utilise ?. (Optional Chaining) pour éviter les crashs si une donnée manque
                
                document.getElementById('match-title').innerText = data.match_title || "Match Analysé";
                
                // Contexte
                document.getElementById('ctx-absences').innerText = data.context?.absences || "Données non disponibles";
                document.getElementById('ctx-xg').innerText = data.context?.xg_data || "Données non disponibles";

                // Prédictions
                const list = document.getElementById('predictions-list');
                list.innerHTML = "";
                
                const preds = data.predictions || [];
                preds.forEach(p => {
                    // Calcul couleur
                    let color = '#ef4444'; // Rouge
                    if(p.trust >= 5) color = '#eab308'; // Jaune
                    if(p.trust >= 8) color = '#22c55e'; // Vert

                    list.innerHTML += `
                        <div class="card">
                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                <span class="card-header">${p.market}</span>
                                <span style="font-size:0.8rem; font-weight:bold; color:${color}">TRUST ${p.trust}/10</span>
                            </div>
                            <div style="font-size:1.2rem; font-weight:bold;">${p.selection}</div>
                            <div class="trust-track">
                                <div class="trust-bar" style="width:${p.trust * 10}%; background:${color};"></div>
                            </div>
                            <div style="font-size:0.9rem; color:#94a3b8; margin-top:10px;">💡 ${p.analysis}</div>
                        </div>
                    `;
                });

                // Banker
                const banker = data.banker || {};
                document.getElementById('banker-sel').innerText = banker.selection || "N/A";
                document.getElementById('banker-odds').innerText = banker.odds || "-";
                document.getElementById('banker-reason').innerText = banker.reason || "Pas d'analyse";

                // Affichage final
                document.getElementById('loader').style.display = 'none';
                document.getElementById('results').style.display = 'block';

            } catch (e) {
                document.getElementById('loader').style.display = 'none';
                const errDiv = document.getElementById('error-zone');
                errDiv.style.display = 'block';
                errDiv.innerText = "❌ ERREUR : " + e.message;
            }
        }
    </script>
</body>
</html>
    ''')

@app.route('/analyze', methods=['POST'])
def analyze_endpoint():
    data = request.json
    # On renvoie directement le JSON stringifié par la fonction get_ai_prediction
    return jsonify({"analysis": get_ai_prediction(data.get('match', ''))})

if __name__ == '__main__':
    app.run(debug=True)
