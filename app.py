import os
from flask import Flask, request, jsonify, render_template_string
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION GOOGLE ---
# On récupère la clé secrète
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

SYSTEM_PROMPT = """
Tu es le Moteur Prédictif NT-Alpha. Agis comme un expert en paris sportifs (type NerdyTips).
Tes réponses doivent être structurées, froides et basées sur des probabilités.

FORMAT OBLIGATOIRE :
# 📊 ANALYSE ALGORITHMIQUE : [Match]

## 1. SCAN DES EFFECTIFS 🚑
* **Absences Majeures :** [Liste + Impact]
* **Facteur X :** [Météo/Forme]
* **Data xG :** [Comparaison]

## 2. PRÉDICTIONS DU MOTEUR 🧠
| Type de Pari | Prédiction | Probabilité | Confiance |
| :--- | :--- | :--- | :--- |
| **Vainqueur** | **[Équipe]** | [XX %] | **[Note /10]** |
| **Buts (O/U)** | **[Over/Under]** | [XX %] | **[Note /10]** |
| **BTTS** | **[Oui/Non]** | [XX %] | **[Note /10]** |

## 3. LE BANKER 💎
* **Choix :** [Le pari le plus sûr]
* **Score Exact :** [Ex: 2-1]
"""

def get_ai_prediction(match_name):
    if not api_key:
        return "Erreur : Clé API Google manquante."
    try:
        # On utilise le modèle Flash (Rapide et Gratuit)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        full_prompt = f"{SYSTEM_PROMPT}\n\nAnalyse ce match maintenant : {match_name}"
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Erreur Google : {str(e)}"

@app.route('/')
def home():
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: sans-serif; background: #121212; color: white; padding: 20px; }
                .container { max-width: 600px; margin: 0 auto; text-align: center; }
                input { width: 80%; padding: 15px; border-radius: 8px; border:none; margin-bottom: 10px; }
                button { width: 80%; padding: 15px; background: #4285F4; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
                #result { margin-top: 20px; text-align: left; white-space: pre-wrap; background: #1e1e1e; padding: 15px; border-radius: 8px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 NT-Alpha (Google Ed.)</h1>
                <input type="text" id="matchInput" placeholder="Ex: Lakers vs Warriors">
                <button onclick="analyze()">LANCER L'ANALYSE</button>
                <div id="loading" style="display:none; margin-top:10px;">🧠 L'IA réfléchit...</div>
                <div id="result"></div>
            </div>
            <script>
                async function analyze() {
                    const match = document.getElementById('matchInput').value;
                    const resDiv = document.getElementById('result');
                    const loadDiv = document.getElementById('loading');
                    
                    if(!match) return;
                    resDiv.innerHTML = "";
                    loadDiv.style.display = "block";
                    
                    const response = await fetch('/analyze', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({match: match})
                    });
                    
                    const data = await response.json();
                    loadDiv.style.display = "none";
                    resDiv.innerText = data.analysis;
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