'''
accounting/banking.py

'''
from pdf2image import convert_from_path
import cv2
import numpy as np
from pyzbar.pyzbar import decode

try:
    from .banking_swiss_dir import SWISS_BANKS
except:
    from banking_swiss_dir import SWISS_BANKS

# Set Poppler path for Windows (change this if needed)
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"


UMLAUTE = [
    ('ﾃｼ', 'ü'),
    ('ﾃ､', 'ä'),
]


def clean(text):
    for source, destination in UMLAUTE:
        text = text.replace(source, destination)
    return text


def format_qr_data(qr_data):
    formatted_data = {
        "creditor": {
            "iban": qr_data[3],
            "name": qr_data[5],
            "address": f"{qr_data[6]}, {qr_data[8]} {qr_data[9]}",
            "zip": qr_data[8],
            "city": qr_data[9],
            "country": qr_data[10]
        },
        "debtor": {
            "name": qr_data[21],
            "address": f"{qr_data[22]}, {qr_data[23]} {qr_data[24]}",
            "zip": qr_data[24],
            "city": qr_data[25],
            "country": qr_data[26]
        },
        "amount": f"{qr_data[18]} {qr_data[19]}",
        "reference": qr_data[27],
        "type": qr_data[2],
        "payment Type": qr_data[30]
    }
    return formatted_data
    

def get_bic(iban):
    clearing = iban[4:9]
    for x in SWISS_BANKS:
        if x['clearing'] == clearing:
            return x['bic']
            
    return None


def extract_qr_from_pdf(pdf_path):
    # Convert PDF to images (all pages)
    images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)

    if len(images) == 0:
        print("No pages found in the PDF.")
        return None

    # Loop through all pages to find the first QR code
    for page_num, image in enumerate(images):
        print(f"Processing page {page_num + 1}")
        
        # Convert PIL image to OpenCV format
        open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Detect and decode QR codes
        decoded_objects = decode(open_cv_image)

        # If QR code found, process it and return
        if decoded_objects:
            for obj in decoded_objects:
                qr_data = clean(obj.data.decode("utf-8", errors="replace"))
                lines = [x.strip() for x in qr_data.split('\n')]
                data = format_qr_data(lines)
                
                # bic
                iban = data['creditor']['iban']
                data['bic'] = get_bic(iban)
                
                # Return the QR code data (first found)
                return data

    return None
    