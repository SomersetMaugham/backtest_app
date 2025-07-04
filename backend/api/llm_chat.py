# /home/ubuntu/backtest_app/backend/api/llm_chat.py

from flask import Blueprint, request, jsonify
import base64

# Use absolute import based on the project structure
from backend.core.llm_service import get_llm_response

llm_chat_bp = Blueprint("llm_chat", __name__)

@llm_chat_bp.route("/llm_chat", methods=["POST"])
def handle_chat():
    """Handles chat interactions with the LLM.
    Request Body (JSON):
        history (list): List of previous chat messages.
        message (str): The latest user message.
        image (str, optional): Base64 encoded image string.
    Returns:
        JSON: LLM response or error message.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    req_data = request.get_json()
    chat_history = req_data.get("history", [])
    user_message = req_data.get("message")
    base64_image_string = req_data.get("image") # Optional base64 image string

    if not user_message:
        return jsonify({"error": "Missing user message"}), 400
    
    # Validate history format (simple check)
    if not isinstance(chat_history, list):
        return jsonify({"error": "Invalid chat history format"}), 400

    image_data = None
    if base64_image_string:
        try:
            # Decode the base64 string to bytes
            image_data = base64.b64decode(base64_image_string)
        except Exception as e:
            return jsonify({"error": f"Invalid base64 image data: {e}"}), 400

    try:
        # Call the LLM service function
        result = get_llm_response(chat_history, user_message, image_data)

        if "error" in result:
            # Propagate specific errors if needed, otherwise return 500 for internal errors
            if "API key" in result["error"] or "authentication failed" in result["error"]:
                 return jsonify(result), 503 # Service Unavailable or similar
            elif "rate limit" in result["error"]:
                 return jsonify(result), 429 # Too Many Requests
            else:
                 return jsonify(result), 500 # Internal Server Error for other LLM issues
        
        return jsonify(result), 200

    except Exception as e:
        print(f"Error processing LLM chat request: {e}") # Log the error
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

