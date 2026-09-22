import pymupdf

def extract_text(file_path: str):
    pdf = pymupdf.open(file_path)

    text = ""

    for page in pdf:
        text += page.get_text()

    pdf.close()

    return text
