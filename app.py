import os
import json
import re
from flask import Flask, request, jsonify, render_template_string
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- PROMPT STRICT (ANTI-BLABLA) ---
SYSTEM_PROMPT = """
Tu es un Moteur API de paris sportifs.
TA SEULE ET UNIQUE TÂCHE EST DE GÉNÉRER UN JSON.
Ne dis pas "Voici le résultat". Ne mets pas de balises markdown ```json.
Commence DIRECTEMENT par {.

Données requises pour le match demandé :
1. "absences": Liste des joueurs absents et leur impact.
2. "xg": Analyse des Expected Goals récents.
3. "form": Forme des 5 derniers matchs.
4. "predictions": Liste de 3 paris (Vainqueur, Buts, BTTS) avec % et Trust Score (1-10).
5. "banker": Le pari le plus sûr avec explication détaillée.

Structure JSON EXACTE à respecter :
{
    "match_title": "Real Madrid vs Barcelona",
    "context": {
        "absences": "Alaba (Blessé - Défense affaiblie), Gavi (Out)",
        "xg_data": "Real (1.85) vs Barca (1.40)",
        "form": "Real: V-V-N-V-D | Barca: V-V-V-N-V"
    },
    "predictions": [
        {
            "market": "Vainqueur",
            "selection": "Real Madrid",
            "proba": "65%",
            "trust": 8,
            "analysis": "A domicile, le Real est imprenable..."
        },
        {
            "market": "Buts",
            "selection": "Over 2.5",
            "proba": "75%",
            "trust": 9,
            "analysis": "Les deux attaques sont en feu..."
        },
        {
            "market": "BTTS",
            "selection": "Oui",
            "proba": "60%",
            "trust": 7,
            "analysis": "Défenses friables des deux côtés..."
        }
    ],
    "banker": {
        "selection": "Real ou Nul & +1.5 Buts",
        "odds": "1.45",
        "reason": "Sécurité maximale car..."
    }
}
"""

def extract_json(text):
    """Extrait le JSON même s'il est noyé dans du texte"""
    try:
        # Regex qui cherche tout ce qui est entre { et } (multiligne)
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return match.group(0)
        return None
    except:
        return None

def get_ai_prediction(match_name):
    if not api_key:
        return json.dumps({"error": "Clé API manquante"})
    
    try:
        # On revient au modèle FLASH standard (plus obéissant)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # On envoie la requête
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nANALYSE CE MATCH: {match_name}"
        )
        
        clean_text = extract_json(response.text)
        
        if not clean_text:
            # Si l'IA n'a pas sorti de JSON, on renvoie une erreur visible
            return json.dumps({"error": "L'IA a répondu du texte au lieu du JSON. Réessaie."})
            
        return clean_text

    except Exception as e:
        return json.dumps({"error": f"Erreur Technique: {str(e)}"})

# --- FRONTEND (DESIGN PRO) ---
@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NT-PRO ULTIMATE</title>
    <style>
        :root { --bg: #0b1120; --card: #1e293b; --accent: #38bdf8; --text: #e2e8f0; }
        body { background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; padding: 20px; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; }
        
        /* INPUT */
        .search-area { background: #151e32; padding: 20px; border-radius: 16px; border: 1px solid #334155; margin-bottom: 30px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.2); }
        h1 { text-align: center; margin: 0 0 20px 0; color: white; letter-spacing: 2px; }
        .input-group { display: flex; gap: 10px; }
        input { flex: 1; padding: 15px; border-radius: 10px; border: 2px solid #334155; background: #0f172a; color: white; font-size: 16px; outline: none; }
        input:focus { border-color: var(--accent); }
        button { padding: 15px 25px; background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%); border: none; border-radius: 10px; font-weight: bold; cursor: pointer; color: white; font-size: 16px; }
        
        /* RESULTATS */
        #result-area { display: none; }
        
        .section-label { color: #94a3b8; font-size: 0.8rem; text-transform: uppercase; margin: 20px 0 10px 0; font-weight: bold; letter-spacing: 1px; }
        
        .card { background: var(--card); padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155; }
        
        /* STATS GRID */
        .stats-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .stat-item strong { color: var(--accent); display: block; font-size: 0.8rem; margin-bottom: 5px; }
        .stat-item span { font-size: 0.9rem; }

        /* PRONOS */
        .prono-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .prono-title { font-weight: bold; color: #cbd5e1; }
        .trust-badge { font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; font-weight: bold; color: #0f172a; }
        
        .progress-container { background: #334155; height: 6px; border-radius: 3px; margin: 10px 0; overflow: hidden; }
        .progress-bar { height: 100%; border-radius: 3px; }
        
        .analysis-text { font-size: 0.9rem; color: #94a3b8; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px; margin-top: 10px; border-left: 2px solid #475569; }

        /* BANKER */
        .banker-card { border: 1px solid #22c55e; background: linear-gradient(180deg, rgba(34,197,94,0.05) 0%, rgba(30,41,59,1) 100%); }
        .banker-title { color: #22c55e; font-weight: 800; font-size: 1.2rem; margin-bottom: 5px; }

        #loader { text-align: center; display: none; margin-top: 30px; font-style: italic; color: #64748b; }
        #error-msg { background: #ef4444; color: white; padding: 15px; border-radius: 10px; display: none; margin-top: 20px; text-align: center; }
    </style>
</head>
<body>

    <div class="container">
        <div class="search-area">
            <h1>NT-PRO <span style="color:var(--accent)">LIVE</span></h1>
            <div class="input-group">
                <input type="text" id="matchInput" placeholder="Ex: Lakers vs Celtics">
                <button onclick="run()">SCANNER</button>
            </div>
        </div>

        <div id="loader">🔄 Connexion aux satellites de données...</div>
        <div id="error-msg"></div>

        <div id="result-area">
            <h2 id="match-title" style="text-align:center; color:white;"></h2>

            <div class="section-label">📊 Données Contextuelles</div>
            <div class="card">
                <div style="margin-bottom: 15px;">
                    <div style="color:var(--accent); font-size:0.8rem; font-weight:bold; margin-bottom:5px;">🚑 ABSENCES & BLESSURES</div>
                    <div id="ctx-absences"></div>
                </div>
                <div class="stats-row">
                    <div class="stat-item">
                        <strong>📈 DATA xG</strong>
                        <span id="ctx-xg"></span>
                    </div>
                    <div class="stat-item">
                        <strong>🔥 FORME RÉCENTE</strong>
                        <span id="ctx-form"></span>
                    </div>
                </div>
            </div>

            <div class="section-label">🧠 Prédictions de l'Algorithme</div>
            <div id="predictions-list"></div>

            <div class="section-label">💎 Le "Banker" (Safe Bet)</div>
            <div class="card banker-card">
                <div style="font-size:0.7rem; color:#22c55e; font-weight:bold; text-transform:uppercase; margin-bottom:5px;">Confiance Maximale</div>
                <div class="banker-title" id="banker-sel"></div>
                <div style="display:flex; justify-content:space-between; font-size:0.9rem; color:#cbd5e1; margin-bottom:10px;">
                    <span>Cote estimée: <span id="banker-odds" style="color:white; font-weight:bold;"></span></span>
                </div>
                <div id="banker-reason" style="font-size:0.9rem; color:#94a3b8;"></div>
            </div>
        </div>
    </div>

    <script>
        async function run() {
            const input = document.getElementById('matchInput').value;
            if(!input) return alert("Écris un match !");

            // UI Reset
            document.getElementById('loader').style.display = 'block';
            document.getElementById('result-area').style.display = 'none';
            document.getElementById('error-msg').style.display = 'none';

            try {
                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({match: input})
                });

                const rawData = await res.json();
                
                // Si erreur backend
                if(rawData.error) throw new Error(rawData.error);

                // Parsing JSON (L'IA renvoie du texte qui est un JSON)
                let data;
                try {
                    data = JSON.parse(rawData.analysis);
                } catch(e) {
                    throw new Error("L'IA a mal formaté les données. Réessaie.");
                }

                // Remplissage UI
                document.getElementById('match-title').innerText = data.match_title || input;
                document.getElementById('ctx-absences').innerText = data.context?.absences || "Rien à signaler";
                document.getElementById('ctx-xg').innerText = data.context?.xg_data || "-";
                document.getElementById('ctx-form').innerText = data.context?.form || "-";

                // Boucle sur les pronos
                const list = document.getElementById('predictions-list');
                list.innerHTML = "";
                
                const preds = data.predictions || [];
                preds.forEach(p => {
                    let color = '#ef4444'; // Rouge
                    if(p.trust >= 5) color = '#eab308'; // Jaune
                    if(p.trust >= 8) color = '#22c55e'; // Vert

                    list.innerHTML += `
                        <div class="card">
                            <div class="prono-header">
                                <span class="prono-title">${p.market}</span>
                                <span class="trust-badge" style="background:${color}">${p.trust}/10</span>
                            </div>
                            <div style="font-size:1.2rem; font-weight:800; margin-bottom:5px;">${p.selection}</div>
                            <div class="progress-container">
                                <div class="progress-bar" style="width:${p.trust * 10}%; background:${color}"></div>
                            </div>
                            <div class="analysis-text">💡 ${p.analysis}</div>
                        </div>
                    `;
                });

                // Banker
                const banker = data.banker || {};
                document.getElementById('banker-sel').innerText = banker.selection || "N/A";
                document.getElementById('banker-odds').innerText = banker.odds || "-";
                document.getElementById('banker-reason').innerText = banker.reason || "";

                document.getElementById('loader').style.display = 'none';
                document.getElementById('result-area').style.display = 'block';

            } catch (e) {
                document.getElementById('loader').style.display = 'none';
                const errDiv = document.getElementById('error-msg');
                errDiv.style.display = 'block';
                errDiv.innerText = "⚠️ Oups : " + e.message;
            }
        }
    </script>
</body>
</html>
    ''')

@app.route('/analyze', methods=['POST'])
def analyze_endpoint():
    data
