MAX_PDF_CONTENT_LENGTH = 3500
PDF_FONT_SIZE = 12
PDF_TEXT_X = 50
PDF_TEXT_Y = 770
PDF_LINE_STEP = -20


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_simple_pdf(title: str, lines: list[str]) -> bytes:
    content = "\n".join(lines)
    text = (
        f"BT /F1 {PDF_FONT_SIZE} Tf {PDF_TEXT_X} {PDF_TEXT_Y} Td "
        f"({_escape_pdf_text(title)}) Tj 0 {PDF_LINE_STEP} Td "
        f"({_escape_pdf_text(content[:MAX_PDF_CONTENT_LENGTH])}) Tj ET"
    )
    stream = text.encode("latin-1", errors="ignore")
    pdf = b"%PDF-1.4\n"
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode() + stream + b"\nendstream endobj\n",
    ]
    xref_positions = [len(pdf)]
    for obj in objects:
        pdf += obj
        xref_positions.append(len(pdf))
    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()
    offset = len(b"%PDF-1.4\n")
    for obj in objects:
        pdf += f"{offset:010d} 00000 n \n".encode()
        offset += len(obj)
    pdf += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode()
    return pdf
