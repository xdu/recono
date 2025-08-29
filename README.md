# Recono - PDF Text Extraction Tool

A Flask application for extracting text from PDF files using OCR (Tesseract) with optional AI-powered text cleaning via OpenRouter.

## Features

- Upload PDF files
- View PDF pages as images
- Extract text using Tesseract OCR
- Clean extracted text using OpenRouter AI to remove OCR artifacts
- Edit and save extracted text
- Export text from selected pages

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Tesseract OCR:
   - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - macOS: `brew install tesseract`
   - Linux: `sudo apt-get install tesseract-ocr`

3. Install Poppler for PDF to image conversion:
   - Windows: Download from [poppler-windows](http://blog.alivate.com.au/poppler-windows/)
   - macOS: `brew install poppler`
   - Linux: `sudo apt-get install poppler-utils`

## OpenRouter Integration

The application includes optional AI-powered text cleaning using OpenRouter. The workflow is:

1. **Initial extraction**: Text is extracted using Tesseract OCR with basic cleaning
2. **Manual AI cleaning**: Users can click the "Clean with AI" button on the text view page to clean specific pages with OpenRouter

### Setup

1. Get an OpenRouter API key from https://openrouter.ai/keys
2. Create a `.env` file in the project root:
```bash
OPENROUTER_API_KEY=your_actual_api_key_here
```
3. Or set it as an environment variable:
```bash
export OPENROUTER_API_KEY=your_actual_api_key_here
```

### OpenRouter Prompt

The system uses the following prompt for text cleaning:
```
Clean up the following text - remove the strange OCR-like artifacts (random symbols, cut-off words, and phantom paragraphs) - do not rewrite the original text - response should contain only the cleaned text, no explanation, no further questions.
```

If no OpenRouter API key is configured, the application will fall back to basic text cleaning.

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser to `http://localhost:5000`

3. Upload a PDF file and navigate through pages to extract and clean text

## File Structure

- `app.py` - Main Flask application
- `requirements.txt` - Python dependencies
- `schema.sql` - Database schema
- `templates/` - HTML templates
- `static/` - Static files and uploads
- `.env.example` - Example environment configuration

## License

MIT License
