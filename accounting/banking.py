'''
accounting/banking.py

library for Zahlungsverkehr

'''
import fitz  # PyMuPDF
import numpy as np
import cv2
from pyzbar.pyzbar import decode


# Map common mojibake sequences to correct characters
MOJIBAKE_MAP = {
    'ﾃｼ': 'ü',  'ﾃ､': 'ä',  'ﾃｵ': 'ö',
    'ﾃｭ': 'ü',  'ﾃﾄ': 'ö',  'ﾃｬ': 'ä',
    'ﾃﾞ': 'é',  'ﾃｲ': 'è',  'ﾃﾝ': 'ê',
    'ﾃﾏ': 'à',  'ﾃｨ': 'î',  'ﾃｯ': 'ç',
    'ﾃｶ': 'ù',

    # Uppercase umlauts and accented letters
    'ﾃｼﾞ': 'Ü', 'ﾃｼﾞ': 'Ä', 'ﾃｵﾞ': 'Ö',
    'ﾃﾑ': 'É',  'ﾃﾚ': 'È',  'ﾃﾍ': 'Ê',
    'ﾃﾈ': 'À',  'ﾃｨ': 'Î',  'ﾃｯ': 'Ç',

    # Mojibake from some Unix environments
    '瓣': 'ä', '駑': 'ü', '馗': 'ö',
}


def fix_mojibake(text: str) -> str:
    for bad_seq, correct_char in MOJIBAKE_MAP.items():
        text = text.replace(bad_seq, correct_char)
    return text


def extract_qr_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=300)  # Try 300-600 for crisp render
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        # Convert RGBA or grayscale to RGB
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        elif pix.n == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        # Grayscale (recommended for pyzbar)
        img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # --- First attempt: pyzbar
        decoded = decode(img_gray)
        if decoded:            
            return fix_mojibake(decoded[0].data.decode('utf-8'))

        # --- Fallback: OpenCV's QRCodeDetector
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img_gray)
        if data:
            return fix_mojibake(data)

    return None  # No QR found


def parse_swiss_qr(qr_payload: str):
    lines = qr_payload.splitlines()

    if len(lines) != 31:
        raise ValueError(f'Expected 31 lines in QR payload but got {len(lines)}')

    try:
        amount = float(lines[18])
    except:
        raise ValueError(f'amount not valid: {lines[18]}')

    return {
        'qr_code': lines[0],
        'version': lines[1],
        'coding': lines[2], 
        'iban': lines[3],
        'creditor': {
            'address_type': lines[4],
            'name': lines[5],
            'address': lines[6],
            'nr': lines[7],
            'postal_code': lines[8],
            'city': lines[9],
            'country': lines[10]
        },
        'amount': amount,
        'currency': lines[19],
        'debtor': {
            'address_type': lines[20],
            'name': lines[21],
            'street': lines[22],
            'nr': lines[23],
            'postal_code': lines[24],
            'city': lines[25],
            'country': lines[26]
        },
        'reference': {
            'type': lines[27],
            'number': lines[28]
        },
        'additional_info': lines[29],
        'trailer': lines[30]
    }


if __name__ == '__main__':
    # Example usage    
    qr_payload = extract_qr_from_pdf('fixtures/transfer ge_soft/1_PDFsam_Rechnungen Zahlungslauf.pdf')
    print('QR Code:', qr_payload)

    if qr_payload:
        parsed = parse_swiss_qr(qr_payload)
        print(parsed)
