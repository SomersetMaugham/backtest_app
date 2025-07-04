# Backend main application file
import os
import sys
from flask import Flask
from dotenv import load_dotenv

# Add the project root directory to sys.path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, project_root)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration (e.g., Secret Key, API Keys from .env)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "default-secret-key")
# Add other configurations as needed

# Import and register Blueprints using absolute imports (now possible due to sys.path modification)
from backend.api.stock_data import stock_data_bp
from backend.api.backtest_runner import backtest_bp # Import backtest blueprint
from backend.api.llm_chat import llm_chat_bp # Import LLM chat blueprint
from backend.api.strategy_manager import strategy_bp # Import strategy manager blueprint

app.register_blueprint(stock_data_bp, url_prefix="/api")
app.register_blueprint(backtest_bp, url_prefix="/api") # Register backtest blueprint
app.register_blueprint(llm_chat_bp, url_prefix="/api") # Register LLM chat blueprint
app.register_blueprint(strategy_bp, url_prefix="/api") # Register strategy manager blueprint

@app.route("/")
def index():
    return "Flask Backend is running!"

if __name__ == "__main__":
    # Note: Use `flask run` command instead of running this directly for development
    # The host and port are configured via `flask run` arguments
    app.run(host="127.0.0.1", port=5001, debug=True) # host="0.0.0.0", port=5001 are handled by flask run command
