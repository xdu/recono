from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import re
import sqlite3
import time  # Import the time module


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}
DATABASE = 'ocr_data.db'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with open('schema.sql') as f:
        conn.executescript(f.read())
    conn.close()

import os

with app.app_context():
    if not os.path.exists(DATABASE):
        init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_text(text):
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    return text.replace('- ', '')

def get_uploaded_files():
    return sorted([f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)])

@app.route('/export/<filename>', methods=['GET', 'POST'])
def export_pdf(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return "File not found", 404

    try:
        from PyPDF2 import PdfReader
        total_pages = len(PdfReader(filepath).pages)
    except Exception as e:
        print(f"Error reading PDF with PyPDF2: {e}")
        return "Error reading PDF", 500

    if request.method == 'POST':
        # Handle export
        selected_pages = request.form.getlist('pages')
        if not selected_pages:
            return "No pages selected", 400

        # Convert to integers
        selected_pages = [int(page) for page in selected_pages]

        # Generate output filename
        base_filename = os.path.splitext(filename)[0]
        output_filename = f"{base_filename}_pages_{'_'.join(map(str, selected_pages))}.txt"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        # Export the selected pages
        with open(output_path, 'w') as f:
            for page in selected_pages:
                # Get text from database or perform OCR
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT text FROM ocr_results WHERE filename = ? AND page_number = ?",
                           (filename, page))
                result = cur.fetchone()

                if result:
                    text = result['text']
                else:
                    # Perform OCR
                    image_path = f'static/page_preview_{filename}_{page}.png'
                    if not os.path.exists(image_path):
                        images = convert_from_path(filepath, first_page=page, last_page=page, dpi=200)
                        image = images[0]
                        image.save(image_path)

                    image = Image.open(image_path)
                    text = pytesseract.image_to_string(image)
                    text = clean_text(text)

                    # Save to database for future use
                    cur.execute(
                        "INSERT INTO ocr_results (filename, page_number, text) VALUES (?, ?, ?)",
                        (filename, page, text)
                    )
                    conn.commit()

                f.write(f"=== Page {page} ===\n")
                f.write(text)
                f.write("\n\n")
                conn.close()

        return redirect(url_for('static', filename=f'uploads/{output_filename}'))

    # For GET request, show the export page
    default_page = request.args.get('default_page', 1, type=int)
    return render_template('export.html',
                         filename=filename,
                         total_pages=total_pages,
                         default_page=default_page)

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

    image_path = f'static/page_preview_{filename}_{page}.png'
    if not os.path.exists(image_path):
        images = convert_from_path(filepath, first_page=page, last_page=page, dpi=200)
        image = images[0]
        image = image.convert("RGB")
        image.save(image_path, resolution=100.0)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT text FROM ocr_results WHERE filename = ? AND page_number = ?",
        (filename, page),
    )
    result = cur.fetchone()
    if result:
        text = result['text']
    else:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        text = clean_text(text)
        cur.execute(
            "INSERT INTO ocr_results (filename, page_number, text) VALUES (?, ?, ?)",
            (filename, page, text),
        )
        conn.commit()
    conn.close()

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

    texts = []
    if end is None:
        end = start
    for page_num in range(start, end + 1):
        text = extract_text(filename, page_num)
        texts.append(text.replace('\n', '<br>'))
    return render_template('text.html', filename=filename, texts=texts, start_page=start, end_page=end)
