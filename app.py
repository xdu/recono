from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import re
import time  # Import the time module
import requests
import json
import uuid
import threading
from dotenv import load_dotenv
from git import Repo


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}
OCR_DATA_DIR = 'ocr_data'
INDEX_FILE = os.path.join(OCR_DATA_DIR, 'index.json')

# Load environment variables from .env file
load_dotenv()

# Get OpenRouter API key from environment variable or .env file
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not found in environment variables")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OCR_DATA_DIR, exist_ok=True)

repo = Repo('.')

# Thread lock for index file access
index_lock = threading.Lock()

def load_index():
    """Load the filename to UUID mapping from index.json"""
    if not os.path.exists(INDEX_FILE):
        return {}
    try:
        with open(INDEX_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_index(index_data):
    """Save the filename to UUID mapping to index.json"""
    with index_lock:
        with open(INDEX_FILE, 'w') as f:
            json.dump(index_data, f, indent=2)

def get_or_create_uuid(filename):
    """Get existing UUID for filename or create new one"""
    index = load_index()
    if filename in index:
        return index[filename]

    # Create new UUID
    file_uuid = str(uuid.uuid4())
    index[filename] = file_uuid
    save_index(index)

    # Commit the index file
    commit_ocr_to_github(INDEX_FILE, f"Add index for filename {filename}")

    # Create UUID directory
    uuid_dir = os.path.join(OCR_DATA_DIR, file_uuid)
    os.makedirs(uuid_dir, exist_ok=True)

    return file_uuid

def get_ocr_text(filename, page_number):
    """Get OCR text for a specific page"""
    file_uuid = get_or_create_uuid(filename)
    page_file = os.path.join(OCR_DATA_DIR, file_uuid, f'{page_number}.json')

    if not os.path.exists(page_file):
        return None

    try:
        with open(page_file, 'r') as f:
            data = json.load(f)
            return data.get('text', '')
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def save_ocr_text(filename, page_number, text):
    """Save OCR text for a specific page"""
    file_uuid = get_or_create_uuid(filename)
    page_file = os.path.join(OCR_DATA_DIR, file_uuid, f'{page_number}.json')

    with open(page_file, 'w') as f:
        json.dump({'text': text}, f, indent=2)

    commit_ocr_to_github(page_file, f"Add OCR text for {filename} page {page_number}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_text(text):
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    return text.replace('- ', '')

def clean_text_with_openrouter(text):
    """
    Clean text using OpenRouter API to remove OCR artifacts.
    Returns the original text if OpenRouter is not configured.
    """
    if not OPENROUTER_API_KEY:
        print("OpenRouter API key not configured, using basic cleaning")
        return clean_text(text)
    
    prompt = f"""Clean up the following text - remove the strange OCR-like artifacts (random symbols, cut-off words, and phantom paragraphs) - do not rewrite the original text - response should contain only the cleaned text, no explanation, no further questions.

{text}"""
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-chat-v3.1",  # Using a cost-effective model
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            timeout=180  # 30 second timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            cleaned_text = result['choices'][0]['message']['content'].strip()
            return cleaned_text
        else:
            print(f"OpenRouter API error: {response.status_code} - {response.text}")
            return clean_text(text)
            
    except requests.exceptions.RequestException as e:
        print(f"OpenRouter API request failed: {e}")
        return clean_text(text)
    except (KeyError, IndexError) as e:
        print(f"OpenRouter API response parsing error: {e}")
        return clean_text(text)

def get_uploaded_files():
    return sorted([f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)])

def commit_ocr_to_github(file_path, message):
    try:
        # Add the file
        repo.index.add([file_path])
        # Check if there are staged changes
        if repo.git.diff('--cached', '--name-only'):
            # Commit
            repo.index.commit(message)
            # Push
            repo.git.push('origin', 'main')
    except Exception as e:
        print(f"Git operation failed: {e}")

@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('view_pdf', filename=filename, page=1))
    return render_template('upload.html', uploaded_files=get_uploaded_files())

@app.route('/view/<filename>/page/<int:page>', methods=['GET', 'POST'])
def view_pdf(filename, page):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return "File not found", 404

    image_path = f'static/page_preview_{filename}_{page}.png'
    if not os.path.exists(image_path):
        images = convert_from_path(filepath, first_page=page, last_page=page, dpi=200)
        image = images[0]
        image = image.convert("RGB")
        image.save(image_path, resolution=100.0)

    total_pages = 1  # Initialize total_pages
    try:
        from PyPDF2 import PdfReader
        total_pages = len(PdfReader(filepath).pages)
    except Exception as e:
        print(f"Error reading PDF with PyPDF2: {e}")
        # total_pages remains 1 if an error occurs

    return render_template(
        'view.html',
        filename=filename,
        image_url='/' + image_path,
        page=page,
        total_pages=total_pages,
    )

@app.route('/extract_text/<filename>/<int:page>', methods=['POST'])
def extract_text(filename, page):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return "File not found", 404

    text = get_ocr_text(filename, page)
    if text is None:
        # Try direct PDF text extraction first for optimization
        try:
            from PyPDF2 import PdfReader
            pdf_reader = PdfReader(filepath)
            page_obj = pdf_reader.pages[page - 1]  # page is 1-indexed
            direct_text = page_obj.extract_text()
            if direct_text.strip():
                # If direct text extraction succeeds, use it
                text = clean_text(direct_text)
                save_ocr_text(filename, page, text)
                return text
        except Exception as e:
            print(f"Direct PDF text extraction failed: {e}")

        # Otherwise, convert to image and do OCR
        image_path = f'static/page_preview_{filename}_{page}.png'
        if not os.path.exists(image_path):
            images = convert_from_path(filepath, first_page=page, last_page=page, dpi=200)
            image = images[0]
            image = image.convert("RGB")
            image.save(image_path, resolution=100.0)

        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        # Use basic cleaning for initial extraction
        text = clean_text(text)
        save_ocr_text(filename, page, text)

    return text

@app.route('/edit_text/<filename>/<int:page>', methods=['GET', 'POST'])
def edit_text(filename, page):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return "File not found", 404

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT text FROM ocr_results WHERE filename = ? AND page_number = ?",
        (filename, page),
    )
    result = cur.fetchone()
    text = result['text'] if result else ""
    conn.close()

    if request.method == 'POST':
        if request.form.get('action') == 'save':
            new_text = request.form['text']
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE ocr_results SET text = ? WHERE filename = ? AND page_number = ?",
                (new_text, filename, page),
            )
            conn.commit()
            conn.close()
        return redirect(url_for('view_pdf', filename=filename, page=page))

    return render_template('edit_text.html', filename=filename, page=page, text=text)

@app.route('/text/<filename>/<int:start>/', methods=['GET', 'POST'])
@app.route('/text/<filename>/<int:start>/<int:end>/', methods=['GET', 'POST'])
def view_text(filename, start, end=None):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return "File not found", 404

    # Get total pages
    total_pages = 1
    try:
        from PyPDF2 import PdfReader
        total_pages = len(PdfReader(filepath).pages)
    except Exception as e:
        print(f"Error reading PDF with PyPDF2: {e}")
        # total_pages remains 1 if an error occurs

    texts = []
    if end is None:
        end = start
    for page_num in range(start, end + 1):
        text = extract_text(filename, page_num)
        texts.append(text.replace('\n', '<br>'))
    return render_template('text.html', filename=filename, texts=texts, start_page=start, end_page=end, total_pages=total_pages)

@app.route('/clean_with_openrouter/<filename>/<int:page>', methods=['POST'])
def clean_with_openrouter(filename, page):
    """Clean text using OpenRouter and update the JSON storage"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return "File not found", 404

    text = get_ocr_text(filename, page)

    if text:
        original_text = text
        # Clean with OpenRouter
        cleaned_text = clean_text_with_openrouter(original_text)
        # Update the JSON storage with cleaned text
        save_ocr_text(filename, page, cleaned_text)
    else:
        # If no text exists, extract and clean
        image_path = f'static/page_preview_{filename}_{page}.png'
        if not os.path.exists(image_path):
            images = convert_from_path(filepath, first_page=page, last_page=page, dpi=200)
            image = images[0]
            image = image.convert("RGB")
            image.save(image_path, resolution=100.0)

        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        # Clean with OpenRouter
        text = clean_text_with_openrouter(text)
        # Save to JSON storage
        save_ocr_text(filename, page, text)

    # Redirect back to the text view page
    return redirect(url_for('view_text', filename=filename, start=page))

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Delete the PDF file
    if os.path.exists(filepath):
        os.remove(filepath)

    # Delete all associated page preview images
    image_pattern = f'static/page_preview_{filename}_*.png'
    import glob
    for image_file in glob.glob(image_pattern):
        try:
            os.remove(image_file)
        except OSError as e:
            print(f"Error deleting image file {image_file}: {e}")

    # Delete OCR data directory and index entry
    index = load_index()
    if filename in index:
        file_uuid = index[filename]
        uuid_dir = os.path.join(OCR_DATA_DIR, file_uuid)
        if os.path.exists(uuid_dir):
            import shutil
            shutil.rmtree(uuid_dir)
        del index[filename]
        save_index(index)

    return redirect(url_for('upload'))
