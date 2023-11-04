from flask import Flask, request, jsonify
from googletrans import Translator

app = Flask(__name__)
translator = Translator()

@app.route('/translate', methods=['POST'])
def translate_text():
    data = request.json
    text = data['text']
    
    # Translate the text to English using googletrans
    translated_text = translator.translate(text, dest='en').text

    return jsonify({'translatedText': translated_text})

@app.route('/gpt-4-prompt', methods=['POST'])
def gpt_4_prompt():
    data = request.json
    prompt = data['prompt']

    # Assuming you have some mechanism to get response from GPT-4
    gpt_4_response = "This is a dummy response for demonstration purposes. Replace with actual GPT-4 response."

    return jsonify({'gpt4Response': gpt_4_response})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
