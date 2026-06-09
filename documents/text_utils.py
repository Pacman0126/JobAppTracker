def extract_document_text(document):
    """
    Best-effort text extraction from a vault document.

    Works directly for .txt files.
    Tries optional PDF/DOCX libraries if installed.
    Falls back to document title if text cannot be extracted yet.
    """
    if not document or not document.file:
        return ""

    filename = document.file.name.lower()

    try:
        if filename.endswith(".txt"):
            with document.file.open("rb") as file_obj:
                return file_obj.read().decode("utf-8", errors="ignore")

        if filename.endswith(".pdf"):
            try:
                from pypdf import PdfReader
            except ImportError:
                try:
                    from PyPDF2 import PdfReader
                except ImportError:
                    return document.title

            with document.file.open("rb") as file_obj:
                reader = PdfReader(file_obj)
                pages = []
                for page in reader.pages:
                    pages.append(page.extract_text() or "")
                return "\n".join(pages).strip() or document.title

        if filename.endswith(".docx"):
            try:
                from docx import Document
            except ImportError:
                return document.title

            with document.file.open("rb") as file_obj:
                doc = Document(file_obj)
                return "\n".join(
                    paragraph.text for paragraph in doc.paragraphs
                ).strip() or document.title

    except Exception:
        return document.title

    return document.title
