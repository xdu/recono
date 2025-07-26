DROP TABLE IF EXISTS ocr_results;

CREATE TABLE ocr_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    text TEXT
);
