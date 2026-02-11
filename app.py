import os
from flask import Flask, request, jsonify, render_template_string
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION GOOGLE ---
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- LE CERVEAU (NERDYTIPS 2.0 SYSTEM) ---
SYSTEM_PROMPT = """
Tu es le Moteur Prédictif NT-Alpha (Version 2.0).
Ta mission : Analyser un match de sport (Foot ou Basket) avec une précision chirurgicale.

RÈGLES D'OR :
1. Recherche les stats en TEMPS RÉEL (Blessures confirmées, xG récents, Forme).
2. Ignore le "bruit" médiatique, concentre-toi sur la DATA.
3. Utilise le format Markdown ci-dessous.

FORMAT DE SORTIE :
# 📊 ANALYSE NT-ALPHA : [Match]

## 1. SCAN DES DONNÉES 🚑
* **Absences Majeures :** [Joueur + Impact réel sur le jeu]
* **Facteur Clé :** [Météo / Motivation / Série en cours]
* **Stats Avancées :** [xG / Pace / Efficacité]

## 2. PRÉDICTIONS DU MOTEUR 🧠
| Type de Pari | Prédiction | Probabilité | Confiance |
| :--- | :--- | :--- | :--- |
| **Vainqueur** | **[Équipe]** | [XX %] | **[Note /10]** |
| **Total (O/U)** | **[Over/Under]** | [XX %] | **[Note /10]** |
| **Sécurité** | **[Double Chance / H +X]** | [XX %] | **[Note /10]** |

## 3. LE BANKER (CHOIX FINAL) 💎
* **La Sélection :** [Le pari le plus fiable]
* **Score Exact Probable :** [Ex: 2-1]
* **Analyse :** [Pourquoi les maths valident ce choix]
"""

def get_ai_prediction(match_name):
    if not api_key:
        return "Erreur : Clé API Google manquante dans les réglages Render."
    
    try:
        # --- MISE À JOUR : UTILISATION DU DERNIER MODÈLE 2.0 ---
        # Ce modèle est beaucoup plus puissant pour le raisonnement complexe
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        full_prompt = f"{SYSTEM_PROMPT}\n\nANALYSE CE MATCH MAINTENANT : {match_name}"
        
        response = model.generate_content(full_prompt)
        return response.text

    except Exception as e:
        return f"❌ Erreur technique : {str(e)}"

# --- INTERFACE WEB (DESIGN PRO DARK MODE) ---
@app.route('/')
def home():
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>NT-Alpha 2.0</title>
            <style>
                body { font-family: -apple-system, system-ui, sans-serif; background: #0b1120; color: #e2e8f0; padding: 20px; margin: 0; }
                .container { max-width: 600px; margin: 0 auto; }
                h1 { color: #38bdf8; text-align: center; font-size: 26px; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 30px; font-weight: 800; }
                
                .search-box { background: #1e293b; padding: 20px; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); border: 1px solid #334155; }
                input { width: 100%; padding: 18px; background: #0f172a; border: 2px solid #334155; border-radius: 10px; color: white; font-size: 16px; box-sizing: border-box; margin-bottom: 15px; outline: none; transition: 0.3s; }
                input:focus { border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2); }
                
                button { width: 100%; padding: 18px; background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); color: white; border: none; border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; transition: transform 0.1s; box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.3); }
                button:active { transform: scale(0.98); }
                
                #loading { display: none; text-align: center; margin-top: 25px; color: #94a3b8; font-style: italic; animation: pulse 1.5s infinite; }
                @keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }
                
                #result { display: none; margin-top: 30px; white-space: pre-wrap; background: #1e293b; padding: 25px; border-radius: 16px; border: 1px solid #334155; line-height: 1.7; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2); }
                
                /* Design des tableaux générés par l'IA */
                h1, h2, h3 { color: #38bdf8; margin-top: 20px; }
                table { width: 100%; border-collapse: separate; border-spacing: 0; margin: 20px 0; border-radius: 8px; overflow: hidden; }
                th { background-color: #0f172a; padding: 12px; text-align: left; color: #38bdf8; border-bottom: 2px solid #334155; }
                td { padding: 12px; border-bottom: 1px solid #334155; background: #1e293b; }
                tr:last-child td { border-bottom: none; }
                strong { color: #fff; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚡ NT-Alpha 2.0</h1>
                <div class="search-box">
                    <input type="text" id="matchInput" placeholder="Ex: Lakers vs Celtics ou PSG vs OM...">
                    <button onclick="analyze()">LANCER L'ALGORITHME</button>
                </div>
                
                <div id="loading">📡 Initialisation du moteur Gemini 2.0...<br>Scan des bases de données...</div>
                <div id="result"></div>
            </div>

            <script>
                // Utilisation d'une fonction simple pour transformer le Markdown basique en HTML (Gras et Tableaux)
                function simpleMarkdown(text) {
                    let html = text
                        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
                        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
                        .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
                        .replace(/\n/gim, '<br>');
                    return html;
                }

                async function analyze() {
                    const match = document.getElementById('matchInput').value;
                    const resDiv = document.getElementById('result');
                    const loadDiv = document.getElementById('loading');
                    
                    if(!match) return alert("Entre un match !");
                    
                    resDiv.innerHTML = "";
                    resDiv.style.display = "none";
                    loadDiv.style.display = "block";
                    
                    try {
                        const response = await fetch('/analyze', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({match: match})
                        });
                        
                        const data = await response.json();
                        loadDiv.style.display = "none";
                        resDiv.style.display = "block";
                        // On affiche le résultat brut (l'IA formate déjà bien le texte)
                        resDiv.innerText = data.analysis;
                    } catch (error) {
                        loadDiv.style.display = "none";
                        alert("Erreur de connexion. Vérifie ta connexion internet.");
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
