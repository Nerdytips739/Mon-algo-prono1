import os
import json
import re
from flask import Flask, request, jsonify, render_template_string
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION API GOOGLE ---
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- LE CERVEAU ANALYTIQUE (MODE JSON) ---
SYSTEM_PROMPT = """
Tu es NT-PRO 3.0, un algorithme de prédiction sportive d'élite (Style NerdyTips/VisiFoot).
Ta mission : Analyser un match et retourner UNIQUEMENT un objet JSON structuré.

RÈGLES D'ANALYSE :
1. Cherche les données réelles (Forme, H2H, xG, Blessures).
2. Fournis 3 types de paris distincts (Vainqueur, Buts, BTTS).
3. Calcule un "Trust Score" (Confiance) de 0 à 10 pour chaque pari.
4. Explique chaque choix avec des arguments techniques (pas de blabla générique).

FORMAT DE SORTIE ATTENDU (JSON STRICT) :
{
    "match_info": "Equipe A vs Equipe B (Date)",
    "stats_context": {
        "xg_analysis": "Analyse courte des Expected Goals (ex: Eq A sous-performe son xG...)",
        "absences": "Liste des joueurs clés absents et impact",
        "form_comparison": "Comparaison de la forme récente (5 derniers matchs)"
    },
    "predictions": [
        {
            "type": "Vainqueur (1X2)",
            "selection": "Nom de l'équipe ou Nul",
            "probability": "XX%",
            "trust_score": 8.5,
            "reasoning": "Explication basée sur la domination à domicile et l'absence du défenseur adverse..."
        },
        {
            "type": "Total Buts (Over/Under)",
            "selection": "Plus de 2.5 Buts",
            "probability": "XX%",
            "trust_score": 7.0,
            "reasoning": "Les deux équipes ont une moyenne de 3.2 buts/match ce mois-ci..."
        },
        {
            "type": "Les deux marquent (BTTS)",
            "selection": "Oui",
            "probability": "XX%",
            "trust_score": 6.5,
            "reasoning": "Attaques performantes mais défenses friables..."
        }
    ],
    "banker_bet": {
        "selection": "Le pari le plus sûr de tous",
        "odds_estimated": "Cote estimée (ex: 1.45)",
        "analysis": "Pourquoi c'est la valeur sûre (Safe Bet)."
    }
}
"""

def get_ai_prediction(match_name):
    if not api_key:
        return json.dumps({"error": "Clé API manquante"})
    
    try:
        # On utilise le modèle Flash Latest pour la vitesse
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # On force la réponse en JSON
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nANALYSE LE MATCH : {match_name}\nRéponds uniquement en JSON valide."
        )
        
        # Nettoyage du JSON (parfois l'IA met des ```json ... ``` autour)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return clean_text

    except Exception as e:
        return json.dumps({"error": f"Erreur technique : {str(e)}"})

# --- INTERFACE FRONTEND (DESIGN PRO) ---
@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NT-PRO ANALYTICS</title>
    <style>
        :root {
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --accent: #38bdf8;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
        }
        body { font-family: 'Segoe UI', Roboto, sans-serif; background: var(--bg-dark); color: var(--text-main); margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; }
        
        /* HEADER */
        header { text-align: center; margin-bottom: 40px; }
        h1 { margin: 0; font-size: 2.5rem; letter-spacing: -1px; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p.subtitle { color: var(--text-muted); font-size: 0.9rem; text-transform: uppercase; letter-spacing: 2px; }

        /* SEARCH BAR */
        .search-box { display: flex; gap: 10px; margin-bottom: 30px; }
        input { flex: 1; padding: 15px; border-radius: 12px; border: 2px solid #334155; background: var(--card-bg); color: white; font-size: 16px; outline: none; transition: 0.3s; }
        input:focus { border-color: var(--accent); }
        button { padding: 15px 30px; border-radius: 12px; border: none; background: var(--accent); color: #0f172a; font-weight: bold; cursor: pointer; font-size: 16px; transition: transform 0.2s; }
        button:active { transform: scale(0.95); }

        /* LOADING */
        .loader { display: none; text-align: center; color: var(--text-muted); font-style: italic; }
        .spinner { width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.1); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* RESULTS AREA */
        #result-area { display: none; animation: fadeIn 0.5s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        /* SECTIONS */
        .section-title { font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px; border-left: 3px solid var(--accent); padding-left: 10px; letter-spacing: 1px; }
        
        /* CARDS */
        .card { background: var(--card-bg); border-radius: 16px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        
        /* CONTEXT STATS GRID */
        .stats-grid { display: grid; grid-template-columns: 1fr; gap: 15px; }
        @media (min-width: 600px) { .stats-grid { grid-template-columns: repeat(3, 1fr); } }
        .stat-box { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; font-size: 0.9rem; }
        .stat-box strong { display: block; color: var(--accent); margin-bottom: 5px; font-size: 0.8rem; text-transform: uppercase; }

        /* PREDICTION ITEMS */
        .pred-item { border-bottom: 1px solid #334155; padding-bottom: 20px; margin-bottom: 20px; }
        .pred-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
        
        .pred-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .pred-type { font-weight: bold; color: var(--text-muted); font-size: 0.9rem; }
        .pred-selection { font-size: 1.2rem; font-weight: 800; color: white; }
        
        /* TRUST BAR */
        .trust-container { margin: 10px 0; }
        .trust-labels { display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 5px; }
        .progress-bg { height: 8px; background: #334155; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; border-radius: 4px; transition: width 1s ease; }
        
        .reasoning { font-size: 0.95rem; color: #cbd5e1; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px; margin-top: 10px; border-left: 2px solid var(--text-muted); }

        /* BANKER CARD */
        .banker-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid var(--success); position: relative; overflow: hidden; }
        .banker-card::before { content: "TOP PICK"; position: absolute; top: 0; right: 0; background: var(--success); color: #000; font-size: 0.7rem; font-weight: bold; padding: 5px 10px; border-bottom-left-radius: 8px; }
        .banker-selection { color: var(--success); font-size: 1.5rem; font-weight: bold; margin: 10px 0; }

    </style>
</head>
<body>

    <div class="container">
        <header>
            <h1>NT-PRO</h1>
            <p class="subtitle">Analyse Sportive Algorithmique</p>
        </header>

        <div class="search-box">
            <input type="text" id="matchInput" placeholder="Ex: Liverpool vs Manchester City...">
            <button onclick="runAnalysis()">ANALYSER</button>
        </div>

        <div id="loader" class="loader">
            <div class="spinner"></div>
            <p>Extraction des données (xG, H2H, Forme)...</p>
            <p style="font-size:0.8rem">Interrogation du modèle Gemini Pro...</p>
        </div>

        <div id="result-area">
            <h2 id="match-title" style="text-align:center; margin-bottom:20px;"></h2>

            <div class="section-title">Analyse du Contexte</div>
            <div class="card">
                <div class="stats-grid">
                    <div class="stat-box">
                        <strong>🚑 Effectif & Absences</strong>
                        <span id="stat-absences"></span>
                    </div>
                    <div class="stat-box">
                        <strong>📊 Analyse xG</strong>
                        <span id="stat-xg"></span>
                    </div>
                    <div class="stat-box">
                        <strong>🔥 Forme & H2H</strong>
                        <span id="stat-form"></span>
                    </div>
                </div>
            </div>

            <div class="section-title">Prédictions Détaillées</div>
            <div class="card" id="predictions-container">
                </div>

            <div class="section-title">Le "Banker" (Sûreté Maximale)</div>
            <div class="card banker-card">
                <div class="banker-selection" id="banker-selection"></div>
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="color:#aaa;">Cote Estimée : <span id="banker-odds" style="color:white;"></span></span>
                </div>
                <p id="banker-analysis" style="font-size:0.95rem; color:#ddd;"></p>
            </div>
        </div>
    </div>

    <script>
        async function runAnalysis() {
            const input = document.getElementById('matchInput');
            const loader = document.getElementById('loader');
            const resultArea = document.getElementById('result-area');
            
            if(!input.value) return alert("Entre un match !");

            // Reset UI
            resultArea.style.display = 'none';
            loader.style.display = 'block';

            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({match: input.value})
                });

                const rawData = await response.json();
                
                // Si l'IA renvoie une erreur ou du texte brut au lieu de JSON
                let data;
                try {
                    data = JSON.parse(rawData.analysis);
                } catch(e) {
                    console.error("Erreur parsing JSON", rawData.analysis);
                    alert("Erreur de formatage de l'IA. Réessaie.");
                    loader.style.display = 'none';
                    return;
                }

                // --- 1. Remplissage des Infos Match ---
                document.getElementById('match-title').innerText = data.match_info;
                document.getElementById('stat-absences').innerText = data.stats_context.absences;
                document.getElementById('stat-xg').innerText = data.stats_context.xg_analysis;
                document.getElementById('stat-form').innerText = data.stats_context.form_comparison;

                // --- 2. Remplissage des Prédictions ---
                const predsContainer = document.getElementById('predictions-container');
                predsContainer.innerHTML = ''; // Clean

                data.predictions.forEach(pred => {
                    // Calcul couleur barre (Rouge < 5, Jaune < 8, Vert > 8)
                    let barColor = '#ef4444';
                    if(pred.trust_score >= 5) barColor = '#eab308';
                    if(pred.trust_score >= 8) barColor = '#22c55e';

                    const html = `
                        <div class="pred-item">
                            <div class="pred-header">
                                <span class="pred-type">${pred.type}</span>
                                <span class="pred-selection">${pred.selection}</span>
                            </div>
                            <div class="trust-container">
                                <div class="trust-labels">
                                    <span>Probabilité: ${pred.probability}</span>
                                    <span>Trust: ${pred.trust_score}/10</span>
                                </div>
                                <div class="progress-bg">
                                    <div class="progress-fill" style="width: ${pred.trust_score * 10}%; background-color: ${barColor};"></div>
                                </div>
                            </div>
                            <div class="reasoning">💡 ${pred.reasoning}</div>
                        </div>
                    `;
                    predsContainer.innerHTML += html;
                });

                // --- 3. Remplissage du Banker ---
                document.getElementById('banker-selection').innerText = data.banker_bet.selection;
                document.getElementById('banker-odds').innerText = data.banker_bet.odds_estimated;
                document.getElementById('banker-analysis').innerText = data.banker_bet.analysis;

                // Affichage final
                loader.style.display = 'none';
                resultArea.style.display = 'block';

            } catch (error) {
                console.error(error);
                alert("Erreur technique : " + error.message);
                loader.style.display = 'none';
            }
        }
    </script>
</body>
</html>
    ''')

@app.route('/analyze', methods=['POST'])
def analyze_endpoint():
    data = request.json
    return jsonify({"analysis": get_ai_prediction(data.get('match', ''))})

if __name__ == '__main__':
    app.run(debug=True)
