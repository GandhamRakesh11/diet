from flask import Flask, render_template, request
import google.generativeai as genai
import re
import webbrowser
import threading
import requests

# 🔑 Configure Gemini API Key
genai.configure(api_key="AIzaSyA59YEAQ0nvfBgDgrz-HFhA4bWWYl0GysM")

app = Flask(__name__)

# Function to fetch dish images using an image search API
def fetch_dish_image(dish_name):
    try:
        search_url = f"https://www.googleapis.com/customsearch/v1?q={dish_name}+food&searchType=image&key=YOUR_GOOGLE_API_KEY&cx=YOUR_CX_ID"
        response = requests.get(search_url).json()
        if "items" in response:
            return response["items"][0]["link"]  # Return first image result
        return "https://via.placeholder.com/150"  # Placeholder if no image found
    except Exception as e:
        print(f"Error fetching image for {dish_name}: {e}")
        return "https://via.placeholder.com/150"  # Return placeholder if error

@app.route('/')
def index():
    return render_template('index.html')

# 📝 Generate AI prompt
def generate_prompt(user_data):
    return (f"Based on the following user details, provide structured dietary recommendations:\n"
            f"- Age: {user_data['age']}\n- Gender: {user_data['gender']}\n- Weight: {user_data['weight']}kg\n"
            f"- Height: {user_data['height']}cm\n- Dietary Preference: {user_data['veg_or_nonveg']}\n"
            f"- Medical Conditions: {user_data['medical_conditions']}\n"
            f"- Region: {user_data['region']}\n- Allergies: {user_data['allergics']}\n"
            f"- Preferred Food Type: {user_data['foodtype']}\n"
            f"\n### Required Recommendations:\n"
            f"1️⃣ **<b>Breakfast Options</b>:** (List 5 healthy breakfast options)\n"
            f"2️⃣ **Lunch Options:** (List 5 Lunch options)\n"
            f"3️⃣ **Workout Suggestions:** (Provide a simple workout plan)\n"
            f"4 **Dinner Options:** (List 5 dinner options)\n"
            f"5 **Medical Advice:** (Provide health tips based on conditions)\n"
            f"\nFormat response with clear section headers.\n")

# ✅ Extract structured recommendations
def extract_recommendations(results):
    def extract_section(pattern, text):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            extracted_data = [item.strip("- ").strip() for item in match.group(1).strip().split("\n") if item.strip()]
            return extracted_data if extracted_data else ["No data available"]
        return ["No data available"]

    recommendations = {
        "breakfast_names": extract_section(r"Breakfast Options:\s*\n([\s\S]*?)(?:\n\n|$)", results),
        "Lunch_names": extract_section(r"Lunch Options:\s*\n([\s\S]*?)(?:\n\n|$)", results),
        "workout_names": extract_section(r"Workout Suggestions:\s*\n([\s\S]*?)(?:\n\n|$)", results),
        "dinner_names": extract_section(r"Dinner Options:\s*\n([\s\S]*?)(?:\n\n|$)", results),
        "medical_advice": extract_section(r"Medical Advice:\s*\n([\s\S]*?)(?:\n\n|$)", results),
    }

    # Fetch images for dishes
    recommendations["breakfast_images"] = [fetch_dish_image(dish) for dish in recommendations["breakfast_names"]]
    recommendations["dinner_images"] = [fetch_dish_image(dish) for dish in recommendations["dinner_names"]]
    
    # Fetch images for workout suggestions and medical advice
    recommendations["workout_images"] = [fetch_dish_image(workout) for workout in recommendations["workout_names"]]
    recommendations["medical_images"] = [fetch_dish_image(advice) for advice in recommendations["medical_advice"]]

    return recommendations

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        user_data = {field: request.form.get(field) for field in [
            'age', 'gender', 'weight', 'height', 'veg_or_nonveg', 'disease', 'region', 'allergics', 'foodtype', 'medical_conditions']}

        if not all(user_data.values()):
            return render_template('index.html', error="⚠️ All fields are required.")

        # Generate AI prompt
        prompt = generate_prompt(user_data)

        # 🌍 Call Gemini API
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        if not response.text:
            return render_template('index.html', error="⚠️ No response from Gemini API.")

        # Extract recommendations
        recommendations = extract_recommendations(response.text)

        return render_template('result.html', raw_ai_response=response.text, **recommendations)

    except Exception as e:
        return render_template('index.html', error=f"⚠️ An error occurred: {str(e)}")

# 🚀 Open browser
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == '__main__':
    threading.Timer(1.25, open_browser).start()
    app.run(debug=True, host='127.0.0.1', port=5000)
