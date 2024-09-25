import json
from flask import Flask, Blueprint, render_template, request, jsonify
import google.generativeai as genai
import os
from fuzzywuzzy import fuzz
import re

# Create a Flask app
app = Flask(__name__)

# Create a blueprint
cybersentry_ai = Blueprint('cybersentry_ai', __name__, template_folder='.')

# Load responses from JSON file
def load_responses():
    try:
        with open('responses.json', 'r') as file:
            data = json.load(file)
        print(f"Loaded {len(data)} responses from JSON.")
        return data
    except Exception as e:
        print(f"Error loading responses: {e}")
        return []

responses = load_responses()

# Configure Gemini API
api_key = os.environ.get('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def preprocess_text(text):
    # Convert to lowercase and remove punctuation
    text = re.sub(r'[^\w\s]', '', text.lower())
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

def advanced_match(query, responses, threshold=80):
    query = preprocess_text(query)
    best_match = None
    best_score = 0

    for response in responses:
        if 'question' in response:
            processed_question = preprocess_text(response['question'])
            
            # Calculate various similarity scores
            ratio = fuzz.ratio(query, processed_question)
            partial_ratio = fuzz.partial_ratio(query, processed_question)
            token_sort_ratio = fuzz.token_sort_ratio(query, processed_question)
            token_set_ratio = fuzz.token_set_ratio(query, processed_question)
            
            # Use a weighted average of these scores
            weighted_score = (ratio * 0.3 + partial_ratio * 0.3 + 
                              token_sort_ratio * 0.2 + token_set_ratio * 0.2)

            if weighted_score > best_score:
                best_score = weighted_score
                best_match = response

    if best_score >= threshold:
        return best_match.get('answer')
    return None

def get_gemini_response(query):
    try:
        response = model.generate_content(query)
        return response.text
    except Exception as e:
        print(f"Error fetching response from Gemini API: {e}")
        return None

# Blueprint routes
@cybersentry_ai.route('/')
def index():
    return render_template('cybersentry_AI.html')

@cybersentry_ai.route('/ask', methods=['POST'])
def ask():
    print("Ask function called")  # Debug line
    try:
        question = request.json.get('question')
        if not question:
            return jsonify({'error': 'No question provided'}), 400

        print(f"Received question: {question}")
        answer = advanced_match(question, responses)
        print(f"JSON answer: {answer}")

        if answer:
            return jsonify({'answer': answer, 'source': 'JSON'})
        else:
            print("No match found in JSON, trying Gemini API")
            gemini_answer = get_gemini_response(question)
            if gemini_answer:
                return jsonify({'answer': gemini_answer, 'source': 'Gemini'})
            else:
                return jsonify({'answer': "I'm sorry, I don't have an answer for that question.", 'source': 'Default'})
    except Exception as e:
        print(f"Error in /ask route: {e}")
        return jsonify({'error': str(e)}), 500

# Register blueprint
app.register_blueprint(cybersentry_ai)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)