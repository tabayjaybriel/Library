from waitress import serve
from app import create_app # Import the function instead
import webbrowser
import sys
import os
from threading import Timer

def open_browser():
    webbrowser.open_new('http://localhost:5500')

if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    Timer(2, open_browser).start()

app = create_app() # Initialize the app

if __name__ == '__main__':
    print(f"--- Environment Debug ---")
    print(f"Python Executable: {sys.executable}")
    print(f"Project Root: {os.path.abspath(os.getcwd())}")
    print("Starting the CMU Library Server at http://localhost:5500")
    serve(app, host='0.0.0.0', port=5500, threads=6)