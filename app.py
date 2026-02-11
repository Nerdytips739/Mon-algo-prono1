import os
import traceback
from flask import Flask, request, jsonify, render_template_string
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

SYSTEM_PROMPT = """
Tu es le Moteur Prédictif NT-Alpha.
Format de réponse : MARKDOWN.
Sois direct. Donne: Vainqueur, Score, Confiance.
"""

def get_ai_prediction(match_name):
    if not api_key:
        return "⚠️ Erreur : Clé API introuvable sur Render."
    
    try:
        # On utilise l'alias "latest" qui était dans ta liste (plus sûr)
        model = genai.GenerativeModel('gemini-flash-latest')
        
        response = model.generate_content(f"{SYSTEM_PROMPT}\nAnalyse : {match_name}")
        return response.text

    except Exception as e:
        # On imprime l'erreur complète pour le diagnostic
        print(f"ERREUR PYTHON : {traceback.format_exc()}")
        return f"❌ Erreur technique du moteur : {str(e)}"

# --- INTERFACE ---
@app.route('/')
def home():
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>NT-Alpha Debug</title>
            <style>
                body { background: #121212; color: white; font-family: sans-serif; padding: 20px; text-align: center; }
                input { width: 80%; padding: 15px; font-size: 16px; margin-bottom: 10px; border-radius: 5px; }
                button { width: 80%; padding: 15px; background: #007bff; color: white; font-size: 18px; border: none; border-radius: 5px; cursor: pointer; }
                #status { margin: 15px; color: yellow; font-style: italic; }
                #result { text-align: left; background: #222; padding: 15px; border-radius: 10px; margin-top: 20px; white-space: pre-wrap; display: none; border: 1px solid #444; }
            </style>
        </head>
        <body>
            <h1>🛠️ NT-Alpha Réparation</h1>
            <input type="text" id="matchInput" placeholder="Ex: Real vs City">
            <br>
            <button onclick="analyze()">LANCER L'ANALYSE</button>
            
            <div id="status">Prêt.</div>
            <div id="result"></div>

            <script>
                async function analyze() {
                    const input = document.getElementById('matchInput');
                    const status = document.getElementById('status');
                    const resDiv = document.getElementById('result');
                    
                    if(!input.value) return alert("Écris un match !");
                    
                    // Etape 1 : On prévient que ça part
                    status.innerText = "⏳ Envoi de la demande au serveur... (Attends 10-20sec)";
                    resDiv.style.display = 'none';
                    
                    try {
                        const response = await fetch('/analyze', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({match: input.value})
                        });
                        
                        // Etape 2 : Le serveur a répondu
                        if (!response.ok) {
                            throw new Error(`Erreur Serveur: ${response.status}`);
                        }

                        const data = await response.json();
                        
                        // Etape 3 : On affiche
                        status.innerText = "✅ Analyse reçue !";
                        resDiv.style.display = 'block';
                        resDiv.innerText = data.analysis;
                        
                    } catch (error) {
                        status.innerText = "❌ ERREUR : " + error.message;
                        alert("Erreur : " + error.message);
                    }
                }
            </script>
        </body>
        </html>
    ''')

@app.route('/analyze', methods=['POST'])
def analyze_endpoint():
    data = request.json
    print(f"Reçu demande pour : {data.get('match')}") # Log serveur
    return jsonify({"analysis": get_ai_prediction(data.get('match', ''))})

if __name__ == '__main__':
    app.run(debug=True)

