from flask import Flask, render_template, request, jsonify, send_from_directory
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import google.generativeai as genai
import random
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Spotify client
client_credentials_manager = SpotifyClientCredentials(client_id='6c4aa666b8944649809a36f965820b52', client_secret='e0673d60575c49a4a7ba76061b249b37')
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Initialize Gemini API
genai.configure(api_key='AIzaSyASYW9KGlynqQhmWYteTZ-5ZgB5t6L0bls')
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Initialize chat history
chat_history = []

def get_hindi_song_recommendations(mood):
    mood_queries = {
        'happy': 'happy upbeat hindi songs',
        'sad': 'sad emotional hindi songs',
        'romantic': 'romantic love hindi songs',
        'energetic': 'energetic dance hindi songs',
        'calm': 'calm soothing hindi songs',
        'angry': 'angry intense hindi songs',
        'nostalgic': 'nostalgic old hindi songs'
    }
    query = mood_queries.get(mood.lower(), 'popular hindi songs')
    
    results = sp.search(q=query, type='track', limit=50, market='IN')
    tracks = results['tracks']['items']
    
    hindi_artists = ['Arijit Singh', 'Shreya Ghoshal', 'Sonu Nigam', 'Alka Yagnik', 'Udit Narayan', 
                     'A.R. Rahman', 'Amit Trivedi', 'Vishal-Shekhar', 'Pritam', 'Lata Mangeshkar', 
                     'Kishore Kumar', 'Mohammed Rafi', 'Asha Bhosle', 'Kumar Sanu', 'Atif Aslam']
    
    hindi_tracks = [track for track in tracks if any(artist['name'] in hindi_artists for artist in track['artists'])]
    recommendations = random.sample(hindi_tracks, min(5, len(hindi_tracks)))
    
    return [(track['name'], track['artists'][0]['name'], track['external_urls']['spotify']) for track in recommendations]

def chat_with_user(user_input):
    global chat_history
    
    chat_history.append(f"Human: {user_input}")
    chat_prompt = "\n".join(chat_history[-5:])  # Only use the last 5 exchanges for context
    
    prompt = f"""
    You are a friendly, family-friendly AI assistant that chats with users about Hindi music. Engage in a polite and appropriate conversation with the user. Do not suggest songs unless explicitly asked. If the user asks for song recommendations, respond with "Sure, I can help you with Hindi song recommendations. What mood are you in?". Always keep the content suitable for all ages.

    Chat history:
    {chat_prompt}

    Please provide:
    1. A family-friendly response to the user's last message (in English)
    2. A boolean indicating if the user has explicitly asked for song recommendations

    Format your response as follows:
    Response: [Your family-friendly response to the user]
    RecommendationRequested: [true/false]
    """

    try:
        response = model.generate_content(prompt)
        logging.debug(f"API Response: {response}")
        
        # Check if the response has content
        if response:
            return response.text
        else:
            logging.error("API returned empty response")
            return "Response: I apologize, but I'm having trouble processing your request. Could you please try rephrasing your message?\nRecommendationRequested: false"
    except Exception as e:
        logging.error(f"Error generating content: {e}")
        return "Response: I apologize, but I'm unable to process that request. Let's try a different topic. How can I assist you with Hindi music?\nRecommendationRequested: false"

@app.route('/')
def home():
    return send_from_directory('', 'index.html')  # Use send_from_directory to serve the file

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json['message']
    logging.info(f"Received user input: {user_input}")
    
    # Check if the user has provided a mood
    moods = ['happy', 'sad', 'romantic', 'energetic', 'calm', 'angry', 'nostalgic']
    user_mood = next((mood for mood in moods if mood in user_input.lower()), None)
    
    if user_mood:
        # If a mood is detected, get recommendations
        recommendations = get_hindi_song_recommendations(user_mood)
        response = f"Based on your {user_mood} mood, here are some Hindi song recommendations:\n"
        for i, (song, artist, url) in enumerate(recommendations, 1):
            response += f"{i}. {song} by {artist} - [Listen on Spotify]({url})\n"
        return jsonify({'response': response, 'recommendationRequested': False})
    
    # If no mood is detected, proceed with normal chat
    analysis = chat_with_user(user_input)
    logging.info(f"Chat analysis: {analysis}")
    
    response = ''
    recommendation_requested = False
    
    if isinstance(analysis, str):
        for line in analysis.split('\n'):
            if line.startswith('Response:'):
                response = line.split(':', 1)[1].strip()
            elif line.startswith('RecommendationRequested:'):
                recommendation_requested = line.split(':', 1)[1].strip().lower() == 'true'
    else:
        response = "I'm sorry, but I couldn't understand your request. Could you please try again?"
    
    chat_history.append(f"AI: {response}")
    
    logging.info(f"Sending response: {response}, recommendation requested: {recommendation_requested}")
    return jsonify({'response': response, 'recommendationRequested': recommendation_requested})

if __name__ == '__main__':
    app.run(debug=True)