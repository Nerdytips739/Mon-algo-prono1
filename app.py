import os
import json
import re
from flask import Flask, request, jsonify, render_template_string
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION API ---
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- LE CERVEAU CONNECTÉ (SOURCES PROS) ---
SYSTEM_PROMPT = """
Tu es le moteur NT-LIVE (NerdyTips Clone).
Ta mission : Scanne le web en TEMPS RÉEL pour remplir les données.
NE RÉPONDS JAMAIS "Rien à signaler" ou "N/A". Si une info manque, cherche plus loin ou fais une estimation basée sur la moyenne de la saison.

SOURCES OBLIGATOIRES À CONSULTER (Virtuellement) :
1. **Stats Avancées (xG) :** Understat.com, FBref.com (Data Opta).
2. **Blessures & News (Minute par minute) :** Transfermarkt, Rotowire, Comptes Twitter/X officiels des clubs, PremierInjuries.
3. **Compos Probables :** Whoscored, SofaScore.
4. **Cotes & Value :** OddsPortal, Pinnacle.

FORMAT DE SORTIE (JSON STRICT) :
{
    "meta": {
        "match_name": "Equipe A vs Equipe B",
        "league": "Competition",
        "time": "Heure"
    },
    "live_news": {
        "headline": "Dernière minute (ex: Mbappé incertain à l'échauffement)",
        "source_used": "Source (ex: L'Equipe / Twitter)"
    },
    "main_prediction": {
        "selection": "Pari Principal",
        "trust_score": 8.5,
        "odds_approx": "1.50"
    },
    "tabs": {
        "analysis": {
            "summary": "Analyse technique détaillée utilisant le jargon pro (bloc bas, transition rapide...).",
            "key_factors": [
                "Facteur 1 (ex: xG contre très élevé à l'extérieur)",
                "Facteur 2 (ex: Retour de blessure du capitaine)",
                "Facteur 3 (ex: Météo ou Contexte Derby)"
            ]
        },
        "stats": {
            "xg_comparison": "EqA (1.45/m) vs EqB (0.80/m)",
            "possession_style": "EqA: Possession (60%) | EqB: Contre-attaque",
            "defense_strength": "EqA: 3 Clean Sheets en 5 matchs"
        },
        "h2h": {
            "last_meetings": "Résultats des 3 derniers matchs (ex: 2-1, 0-0, 1-3)",
            "trend": "Tendance (ex: Toujours BTTS entre eux)"
        }
    },
    "side_bets": [
        {"market": "Total Buts", "selection": "Over/Under", "trust": 7},
        {"market": "BTTS", "selection": "Oui/Non", "trust": 6}
    ]
}
"""

def extract_json(text):
    try:
        match = re.search(r'\{[\s\S]*\}', text)
        if match: return match.group(0)
        return None
    except: return None

def get_nerdytips_analysis(match_name):
    if not api_key: return json.dumps({"error": "Clé API manquante"})
    try:
        # ACTIVATION DE L'OUTIL DE RECHERCHE (GROUNDING)
        # On utilise le modèle qui supporte le mieux la recherche
        tools = {"google_search_retrieval": {}} 
        model = genai.GenerativeModel('gemini-1.5-flash', tools='google_search_retrieval') 
        
        # On force l'IA à chercher avec un prompt directif
        full_prompt = f"{SYSTEM_PROMPT}\n\nACTION: Effectue une recherche Google sur '{match_name} preview stats injuries xG' et remplis le JSON."
        
        response = model.generate_content(full_prompt)
        
        json_data = extract_json(response.text)
        if not json_data: 
            # Fallback : Si l'IA échoue, on renvoie une erreur explicite
            return json.dumps({"error": "L'IA n'a pas trouvé de données. Réessaie."})
            
        return json_data

    except Exception as e:
        # Si le compte gratuit ne supporte pas 'google_search_retrieval', on tente sans outil
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"{SYSTEM_PROMPT}\n\nMATCH: {match_name}")
            return extract_json(response.text)
        except:
            return json.dumps({"error": str(e)})

# --- SITE WEB (INTERFACE) ---
@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NT-LIVE PRO</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0b0e14; --card: #151a23; --accent: #00ff88; --text: #ffffff; --border: #2d3748; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        
        /* SEARCH */
        .search-box { display: flex; gap: 10px; margin-bottom: 30px; }
        input { flex: 1; padding: 15px; border-radius: 12px; border: 1px solid var(--border); background: #1f2937; color: white; outline: none; }
        button { padding: 15px 30px; background: var(--accent); border: none; border-radius: 12px; font-weight: bold; cursor: pointer; color: #0b0e14; }

        /* LIVE NEWS TICKER */
        .news-ticker { background: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; color: #60a5fa; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.9rem; display: flex; align-items: center; gap: 10px; display: none; }
        .live-dot { height: 8px; width: 8px; background: #ef4444; border-radius: 50%; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }

        /* MATCH HEADER */
        .header-card { background: var(--card); padding: 25px; border-radius: 16px; text-align: center; border: 1px solid var(--border); margin-bottom: 20px; display: none; }
        .teams { font-size: 1.8rem; font-weight: 800; margin: 10px 0; }
        .trust-badge { display: inline-block; background: var(--accent); color: #000; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 0.9rem; margin-top: 10px; }

        /* TABS */
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; overflow-x: auto; display: none; }
        .tab-btn { background: var(--card); border: 1px solid var(--border); color: #9ca3af; padding: 10px 20px; border-radius: 30px; cursor: pointer; white-space: nowrap; }
        .tab-btn.active { background: white; color: black; border-color: white; }
        .tab-content { display: none; background: var(--card); padding: 20px; border-radius: 16px; border: 1px solid var(--border); }
        .tab-content.active { display: block; }

        /* CONTENT */
        .info-row { display: flex; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        .label { color: #9ca3af; }
        .val { font-weight: bold; text-align: right; }
        
        #loader { text-align: center; display: none; margin-top: 40px; color: #9ca3af; }
    </style>
</head>
<body>

    <div class="container">
        <h1 style="text-align:center; letter-spacing:-1px;">NT-LIVE <span style="color:var(--accent)">PRO</span></h1>
        
        <div class="search-box">
            <input type="text" id="matchInput" placeholder="Ex: Real Madrid vs Man City">
            <button onclick="run()">SCANNER LE WEB</button>
        </div>

        <div id="loader">🌍 Recherche des données Opta/Understat en cours...</div>
        <div id="error-msg" style="display:none; color:#ef4444; text-align:center;"></div>

        <div id="result-area" style="display:none;">
            
            <div id="news-ticker" class="news-ticker">
                <div class="live-dot"></div>
                <span id="news-text"></span>
            </div>

            <div class="header-card" style="display:block;">
                <div style="font-size:0.8rem; color:#9ca3af; text-transform:uppercase;" id="league"></div>
                <div class="teams" id="teams"></div>
                <div class="trust-badge">CONFIANCE IA: <span id="trust"></span>/10</div>
                <div style="margin-top:15px; font-size:1.2rem; font-weight:bold; color:var(--accent);" id="main-pred"></div>
            </div>

            <div class="tabs" style="display:flex;">
                <button class="tab-btn active" onclick="openTab('analysis')">Analyse Pro</button>
                <button class="tab-btn" onclick="openTab('stats')">Data xG</button>
                <button class="tab-btn" onclick="openTab('h2h')">H2H</button>
            </div>

            <div id="analysis" class="tab-content active">
                <p id="analysis-text" style="line-height:1.6; color:#d1d5db;"></p>
                <ul id="key-factors" style="color:#d1d5db; padding-left:20px;"></ul>
            </div>

            <div id="stats" class="tab-content">
                <div class="info-row">
                    <span class="label">Comparaison xG</span>
                    <span class="val" id="xg-val"></span>
                </div>
                <div class="info-row">
                    <span class="label">Style de Jeu</span>
                    <span class="val" id="style-val"></span>
                </div>
                <div class="info-row">
                    <span class="label">Défense</span>
                    <span class="val" id="def-val"></span>
                </div>
            </div>

            <div id="h2h" class="tab-content">
                <div class="info-row">
                    <span class="label">Derniers Matchs</span>
                    <span class="val" id="h2h-last"></span>
                </div>
                <div class="info-row">
                    <span class="label">Tendance</span>
                    <span class="val" id="h2h-trend"></span>
                </div>
            </div>

            <div style="margin-top:20px; background:var(--card); padding:20px; border-radius:16px; border:1px solid var(--border);">
                <div style="font-size:0.9rem; color:#9ca3af; margin-bottom:10px;">AUTRES OPPORTUNITÉS</div>
                <div id="side-bets"></div>
            </div>

        </div>
    </div>

    <script>
        function openTab(name) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(name).classList.add('active');
            event.target.classList.add('active');
        }

        async function run() {
            const input = document.getElementById('matchInput').value;
            if(!input) return alert("Entre un match !");

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
                
                if(rawData.error) throw new Error(rawData.error);
                const data = JSON.parse(rawData.analysis);

                // Remplissage
                document.getElementById('league').innerText = data.meta.league;
                document.getElementById('teams').innerText = data.meta.match_name;
                document.getElementById('trust').innerText = data.main_prediction.trust_score;
                document.getElementById('main-pred').innerText = data.main_prediction.selection;

                // Live News
                if(data.live_news && data.live_news.headline) {
                    document.getElementById('news-ticker').style.display = 'flex';
                    document.getElementById('news-text').innerText = data.live_news.headline + " (Source: " + data.live_news.source_used + ")";
                }

                // Onglets
                document.getElementById('analysis-text').innerText = data.tabs.analysis.summary;
                const ul = document.getElementById('key-factors');
                ul.innerHTML = "";
                data.tabs.analysis.key_factors.forEach(f => ul.innerHTML += `<li>${f}</li>`);

                document.getElementById('xg-val').innerText = data.tabs.stats.xg_comparison;
                document.getElementById('style-val').innerText = data.tabs.stats.possession_style;
                document.getElementById('def-val').innerText = data.tabs.stats.defense_strength;

                document.getElementById('h2h-last').innerText = data.tabs.h2h.last_meetings;
                document.getElementById('h2h-trend').innerText = data.tabs.h2h.trend;

                // Side bets
                const sbDiv = document.getElementById('side-bets');
                sbDiv.innerHTML = "";
                data.side_bets.forEach(b => {
                    sbDiv.innerHTML += `
                        <div style="display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #2d3748;">
                            <span>${b.market}</span>
                            <span style="font-weight:bold; color:white;">${b.selection}</span>
                        </div>
                    `;
                });

                document.getElementById('loader').style.display = 'none';
                document.getElementById('result-area').style.display = 'block';

            } catch (e) {
                document.getElementById('loader').style.display = 'none';
                document.getElementById('error-msg').style.display = 'block';
                document.getElementById('error-msg').innerText = "Erreur : " + e.message;
            }
        }
    </script>
</body>
</html>
    ''')

@app.route('/analyze', methods=['POST'])
def analyze_endpoint():
    data = request.json
    return jsonify({"analysis": get_nerdytips_analysis(data.get('match', ''))})

if __name__ == '__main__':
    app.run(debug=True)
