import os
from flask import Flask, request, jsonify, render_template_string
import google.generativeai as genai

app = Flask(__name__)

# Configuration API
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

SYSTEM_PROMPT = """
Tu es le Moteur Prédictif NT-Alpha. Agis comme un expert en paris sportifs.
Sois précis, direct et utilise des pourcentages.
"""

def get_ai_prediction(match_name):
    if not api_key:
        return "Erreur : Clé API manquante."
    
    try:
        # On tente le modèle Flash (le plus rapide)
        model = genai.GenerativeModel('gemini-1.5-flash')
        full_prompt = f"{SYSTEM_PROMPT}\n\nAnalyse ce match : {match_name}"
        response = model.generate_content(full_prompt)
        return response.text

    except Exception as e:
        # Si ça plante, on liste les modèles disponibles pour comprendre pourquoi
        error_msg = f"❌ Erreur technique : {str(e)}\n\n"
        try:
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            error_msg += f"✅ Modèles disponibles détectés sur ton compte : {', '.join(available_models)}"
        except:
            error_msg += "Impossible de lister les modèles."
            
        return error_msg

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
                #result { margin-top: 20px; text-align: left; white-space: pre-wrap; background: #1e1e1e; padding: 15px; border-radius: 8px; border: 1px solid #333; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 NT-Alpha (Diagnostic)</h1>
                <input type="text" id="matchInput" placeholder="Ex: PSG vs OM">
                <button onclick="analyze()">LANCER L'ANALYSE</button>
                <div id="loading" style="display:none; margin-top:10px;">🔍 Test en cours...</div>
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
