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

# --- PROMPT STRICT (JSON ONLY) ---
SYSTEM_PROMPT = """
Tu es un API de prédiction sportive. 
Ton rôle est de convertir une demande de match en un objet JSON strict.
Ne mets JAMAIS de Markdown (pas de ```json).
Ne mets JAMAIS de phrase d'intro.
Renvoie JUSTE l'objet JSON brut.

Structure OBLIGATOIRE :
{
    "match_info": "Equipe A vs Equipe B",
    "stats_context": {
        "absences": "Liste courte des absents majeurs",
        "xg_analysis": "Analyse rapide des xG récents",
        "form": "Comparaison de forme (ex: A est invaincu...)"
    },
    "predictions": [
        {
            "type": "Vainqueur",
            "selection": "Nom Equipe",
            "probability": "XX%",
            "trust_score": 8,
            "reasoning": "Explication courte."
        },
        {
            "type": "Buts",
            "selection": "Over/Under",
            "probability": "XX%",
            "trust_score": 7,
            "reasoning": "Explication courte."
        },
        {
            "type": "BTTS",
            "selection": "Oui/Non",
            "probability": "XX%",
            "trust_score": 6,
            "reasoning": "Explication courte."
        }
    ],
    "banker": {
        "selection": "Le pari le plus sûr",
        "odds": "1.50",
        "analysis": "Pourquoi c'est sûr."
    }
}
"""

def get_ai_prediction(match_name):
    if not api_key:
        return json.dumps({"error": "Clé API manquante"})
    
    try:
        # On utilise Flash Latest (Rapide)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nMATCH: {match_name}"
        )
        
        # --- FILTRE DE NETTOYAGE (LE CORRECTIF) ---
        # On cherche le premier '{' et le dernier '}' pour isoler le JSON
        text = response.text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if match:
            json_str = match.group(0)
            # On vérifie si c'est du JSON valide
            json.loads(json_str) 
            return json_str
        else:
            # Si l'IA n'a pas renvoyé de JSON, on force une structure d'erreur
            return json.dumps({
                "match_info": "Erreur IA",
                "stats_context": {"absences": "N/A", "xg_analysis": "N/A", "form": "N/A"},
                "predictions": [],
                "banker": {"selection": "Erreur", "odds": "0", "analysis": "L'IA a mal répondu."}
            })

    except Exception as e:
        return json.dumps({"error": f"Erreur technique : {str(e)}"})

# --- INTERFACE ---
@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NT-PRO FIXED</title>
    <style>
        body { font-family: sans-serif; background: #0f172a; color: white; padding: 20px; margin: 0; }
        .container { max-width: 600px; margin: 0 auto; }
        input { width: 100%; padding: 15px; background: #1e293b; border: 1px solid #334155; color: white; border-radius: 8px; margin-bottom: 10px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #38bdf8; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        
        .card { background: #1e293b; padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155; }
        .tag { color: #94a3b8; font-size: 0.8rem; text-transform: uppercase; display: block; margin-bottom: 5px; }
        .value { font-size: 1rem; color: #e2e8f0; }
        
        .bar-bg { background: #334155; height: 6px; border-radius: 3px; margin-top: 5px; }
        .bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
        
        #error-msg { color: #ef4444; background: rgba(239,68,68,0.1); padding: 10px; border-radius: 8px; display: none; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 style="text-align:center; color:#38bdf8;">NT-PRO v3</h1>
        <input type="text" id="matchInput" placeholder="Ex: Real vs Barca">
        <button onclick="run()">ANALYSER</button>
        
        <div id="loading" style="display:none; text-align:center; margin-top:20px;">🔄 Analyse des données en cours...</div>
        <div id="error-msg"></div>

        <div id="result" style="display:none; margin-top:20px;">
            <h2 id="match-title" style="text-align:center;"></h2>
            
            <div class="card">
                <span class="tag">🚑 Absences</span>
                <div class="value" id="absences"></div>
                <hr style="border-color:#334155; opacity:0.3; margin:10px 0;">
                <span class="tag">📊 xG & Forme</span>
                <div class="value" id="form"></div>
            </div>

            <div id="pronos-list"></div>

            <div class="card" style="border: 1px solid #22c55e;">
                <span class="tag" style="color:#22c55e;">💎 LE BANKER</span>
                <div class="value" style="font-size:1.2rem; font-weight:bold;" id="banker-sel"></div>
                <div class="tag" style="margin-top:5px;">Analyse : <span id="banker-ana" style="color:#ccc; text-transform:none;"></span></div>
            </div>
        </div>
    </div>

    <script>
        async function run() {
            const input = document.getElementById('matchInput').value;
            if(!input) return;

            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            document.getElementById('error-msg').style.display = 'none';

            try {
                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({match: input})
                });
                
                const rawData = await res.json();
                
                // Si le serveur renvoie une erreur directe
                if(rawData.error) throw new Error(rawData.error);

                // Parsing du JSON nettoyé par Python
                let data = JSON.parse(rawData.analysis);

                // Remplissage
                document.getElementById('match-title').innerText = data.match_info;
                document.getElementById('absences').innerText = data.stats_context.absences;
                document.getElementById('form').innerText = data.stats_context.xg_analysis + " " + data.stats_context.form;

                // Liste des pronos
                const list = document.getElementById('pronos-list');
                list.innerHTML = "";
                data.predictions.forEach(p => {
                    let color = p.trust_score > 7 ? '#22c55e' : (p.trust_score > 4 ? '#eab308' : '#ef4444');
                    list.innerHTML += `
                        <div class="card">
                            <div style="display:flex; justify-content:space-between;">
                                <span class="tag">${p.type}</span>
                                <span class="tag">Trust: ${p.trust_score}/10</span>
                            </div>
                            <div style="font-size:1.1rem; font-weight:bold;">${p.selection}</div>
                            <div class="bar-bg"><div class="bar-fill" style="width:${p.trust_score*10}%; background:${color};"></div></div>
                            <div style="font-size:0.9rem; color:#ccc; margin-top:8px;">💡 ${p.reasoning}</div>
                        </div>
                    `;
                });

                // Banker
                document.getElementById('banker-sel').innerText = data.banker.selection;
                document.getElementById('banker-ana').innerText = data.banker.analysis;

                document.getElementById('loading').style.display = 'none';
                document.getElementById('result').style.display = 'block';

            } catch (e) {
                document.getElementById('loading').style.display = 'none';
                const errDiv = document.getElementById('error-msg');
                errDiv.style.display = 'block';
                errDiv.innerText = "Erreur : " + e.message + " (Réessaie, l'IA a bégayé)";
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
