import os
import json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24) 


api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/')
def index():
    """Render the role selection page"""
    return render_template('index.html')

@app.route('/interview')
def interview():
    """Render the interview page"""
    return render_template('interview.html')

@app.route('/results')
def results():
    """Render the results page"""
    return render_template('results.html')

@app.route('/generate_questions', methods=['POST'])
def generate_questions():
    """Generate 3 interview questions for the given role"""
    try:
        data = request.get_json()
        role = data.get('role', '').strip()
        
        if not role:
            return jsonify({'error': 'Role is required'}), 400
        
        # Construct the prompt
        prompt = f'''You are a friendly interview coach. Generate exactly three interview questions for role "{role}":
1) one aptitude/brain-teaser
2) one technical question  
3) one HR/behavioral question

Use simple, conversational language—no jargon or complex words.

Return only valid JSON in this structure:
[
    {{ "type": "Aptitude", "question": "..." }},
    {{ "type": "Technical", "question": "..." }},
    {{ "type": "HR", "question": "..." }}
]

Example for "Frontend Developer":
[
    {{ "type": "Aptitude", "question": "You have a 3-gallon jug and a 5-gallon jug… how do you measure 4 gallons?" }},
    {{ "type": "Technical", "question": "What is a React component, and why use it?" }},
    {{ "type": "HR", "question": "Tell me about a time you helped a teammate solve a problem." }}
]'''
        
        # Generate questions using Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        questions_json = response.text.strip()
        
        # Remove any markdown formatting if present
        if questions_json.startswith('```json'):
            questions_json = questions_json.replace('```json', '').replace('```', '').strip()
        elif questions_json.startswith('```'):
            questions_json = questions_json.replace('```', '').strip()
        
        questions = json.loads(questions_json)
        
        # Validate the structure
        if not isinstance(questions, list) or len(questions) != 3:
            raise ValueError("Invalid questions format")
        
        required_types = {'Aptitude', 'Technical', 'HR'}
        question_types = {q.get('type') for q in questions}
        
        if not required_types.issubset(question_types):
            raise ValueError("Missing required question types")
        
        return jsonify({'questions': questions})
        
    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to parse questions from AI response'}), 500
    except Exception as e:
        print(f"Error generating questions: {str(e)}")
        return jsonify({'error': 'Failed to generate questions. Please try again.'}), 500

@app.route('/evaluate', methods=['POST'])
def evaluate():
    """Evaluate a single answer and return feedback with score"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()
        
        if not question or not answer:
            return jsonify({'error': 'Question and answer are required'}), 400
        
        # Construct the evaluation prompt
        prompt = f'''You are an expert interviewer and coach. Evaluate this answer:

Question: "{question}"
Answer: "{answer}"

Give concise, friendly feedback on accuracy and completeness. Highlight one strength and one improvement. Assign a score from 0 to 10.

Return only valid JSON:
{{
    "feedback": "...",
    "score": <integer>
}}

Example:
{{
    "feedback": "Good start explaining that React components return UI. Add how they manage state or lifecycle to deepen your answer.",
    "score": 7
}}'''
        
        # Generate evaluation using Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        evaluation_json = response.text.strip()
        
        # Remove any markdown formatting if present
        if evaluation_json.startswith('```json'):
            evaluation_json = evaluation_json.replace('```json', '').replace('```', '').strip()
        elif evaluation_json.startswith('```'):
            evaluation_json = evaluation_json.replace('```', '').strip()
        
        evaluation = json.loads(evaluation_json)
        
        # Validate the structure
        if 'feedback' not in evaluation or 'score' not in evaluation:
            raise ValueError("Invalid evaluation format")
        
        # Ensure score is an integer between 0-10
        score = int(evaluation['score'])
        if score < 0 or score > 10:
            score = max(0, min(10, score))
        
        evaluation['score'] = score
        
        return jsonify(evaluation)
        
    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to parse evaluation from AI response'}), 500
    except Exception as e:
        print(f"Error evaluating answer: {str(e)}")
        return jsonify({'error': 'Failed to evaluate answer. Please try again.'}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)