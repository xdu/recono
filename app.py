from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
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

@app.route('/')
def home():
    return redirect(url_for('upload_file'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
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

    try:
        from PyPDF2 import PdfReader
        total_pages = len(PdfReader(filepath).pages)
    except Exception as e:
        print(f"Error reading PDF with PyPDF2: {e}")
        pass

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

@app.route('/export_text/<filename>', methods=['POST'])
def export_text(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "File not found"}), 404

    try:
        from PyPDF2 import PdfReader
        total_pages = len(PdfReader(filepath).pages)
    except Exception as e:
        print(f"Error reading PDF with PyPDF2: {e}")
        return jsonify({"status": "error", "message": "Could not read PDF"}), 500

    selected_pages = request.get_json().get('pages', [])
    output_filename = f"{filename.split('.')[0]}.txt"
    output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

    with open(output_filepath, "w") as outfile:
        if not selected_pages:
            # If no pages are selected, export all pages
            for page_number in range(1, total_pages + 1):
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT text FROM ocr_results WHERE filename = ? AND page_number = ?",
                    (filename, page_number),
                )
                result = cur.fetchone()
                if result:
                    text = result['text']
                else:
                    image_path = f'static/page_preview_{filename}_{page_number}.png'
                    if not os.path.exists(image_path):
                        try:
                            images = convert_from_path(filepath, first_page=page_number, last_page=page_number, dpi=200)
                            image = images[0]
                            image = image.convert("RGB")
                            image.save(image_path, resolution=100.0)
                        except Exception as e:
                            print(f"Error converting page {page_number} to image: {e}")
                            text = "Error extracting text from this page."
                            outfile.write(f"Page {page_number}:\n{text}\n\n")
                            conn.close()
                            continue

                    try:
                        image = Image.open(image_path)
                        text = pytesseract.image_to_string(image)
                        text = clean_text(text)
                        cur.execute(
                            "INSERT INTO ocr_results (filename, page_number, text) VALUES (?, ?, ?)",
                            (filename, page_number, text),
                        )
                        conn.commit()
                    except Exception as e:
                        print(f"Error performing OCR on page {page_number}: {e}")
                        text = "Error extracting text from this page."
                        outfile.write(f"Page {page_number}:\n{text}\n\n")
                        conn.close()
                        continue

                outfile.write(f"Page {page_number}:\n{text}\n\n")
                conn.close()
                # Simulate some processing time for the progress bar
                time.sleep(0.1)  # Adjust the sleep duration as needed
        else:
            # Export only selected pages
            for page_number in selected_pages:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT text FROM ocr_results WHERE filename = ? AND page_number = ?",
                    (filename, page_number),
                )
                result = cur.fetchone()
                if result:
                    text = result['text']
                else:
                    image_path = f'static/page_preview_{filename}_{page_number}.png'
                    if not os.path.exists(image_path):
                        try:
                            images = convert_from_path(filepath, first_page=page_number, last_page=page_number, dpi=200)
                            image = images[0]
                            image = image.convert("RGB")
                            image.save(image_path, resolution=100.0)
                        except Exception as e:
                            print(f"Error converting page {page_number} to image: {e}")
                            text = "Error extracting text from this page."
                            outfile.write(f"Page {page_number}:\n{text}\n\n")
                            conn.close()
                            continue

                    try:
                        image = Image.open(image_path)
                        text = pytesseract.image_to_string(image)
                        text = clean_text(text)
                        cur.execute(
                            "INSERT INTO ocr_results (filename, page_number, text) VALUES (?, ?, ?)",
                            (filename, page_number, text),
                        )
                        conn.commit()
                    except Exception as e:
                        print(f"Error performing OCR on page {page_number}: {e}")
                        text = "Error extracting text from this page."
                        outfile.write(f"Page {page_number}:\n{text}\n\n")
                        conn.close()
                        continue

                outfile.write(f"Page {page_number}:\n{text}\n\n")
                conn.close()
                # Simulate some processing time for the progress bar
                time.sleep(0.1)  # Adjust the sleep duration as needed

    return jsonify({"status": "completed", "filepath": url_for('static', filename=f'uploads/{output_filename}')})
