# #!/bin/bash

# # Script to install dependencies and run the Flask backend and Streamlit frontend

# # Exit immediately if a command exits with a non-zero status.
set -e

# # Define project root directory
# # PROJECT_ROOT="/backtest_app"
# # Define project root directory dynamically based on script location
# # Get the absolute path of the script's directory
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# # --- Backend Setup ---
# echo "--- Setting up Backend ---"
# cd "$BACKEND_DIR"

# # Create virtual environment if it doesn\t exist
# if [ ! -d "venv" ]; then
#     echo "Creating backend virtual environment..."
#     python3 -m venv venv
# fi

# # Activate virtual environment
# source venv/bin/activate

# # Install backend dependencies
# echo "Installing backend dependencies..."
# pip install -r requirements.txt

# # Check for .env file and provide instructions if missing
# if [ ! -f ".env" ]; then
#     echo "WARNING: .env file not found in backend directory." 
#     echo "Please create a .env file based on .env.example and add your OPENAI_API_KEY."
#     # Optionally exit if key is mandatory
#     # exit 1 
# fi

# # Start Flask backend in the background
# echo "Starting Flask backend server on port 5001..."
# # Use nohup to run in background and redirect output
# # Ensure Flask listens on 0.0.0.0 to be accessible from Streamlit
# nohup flask run --host=0.0.0.0 --port=5001 > flask.log 2>&1 &
# FLASK_PID=$!
# echo "Flask backend started with PID $FLASK_PID. Logs in backend/flask.log"

# # Deactivate backend venv (optional, frontend has its own)
# deactivate

# --- Frontend Setup ---
echo "\n--- Setting up Frontend ---"
cd "$FRONTEND_DIR"

# Create virtual environment if it doesn\t exist (optional, can share backend venv if dependencies don\t clash)
# For separation, let\s create its own
if [ ! -d "venv" ]; then
    echo "Creating frontend virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install frontend dependencies
echo "Installing frontend dependencies..."
pip install -r requirements.txt

# Start Streamlit frontend
echo "Starting Streamlit frontend server on port 8501..."
# Streamlit automatically listens on 0.0.0.0 usually
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# --- Cleanup (Optional) ---
# This part will run when Streamlit is stopped (e.g., Ctrl+C)
echo "\nStreamlit stopped. Stopping Flask backend..."
kill $FLASK_PID
echo "Flask backend stopped."

# Deactivate frontend venv
deactivate

echo "\nApplication stopped."

