'''
accounting/banking.py
'''
from pdf2image import convert_from_path
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from pathlib import Path

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
        "Creditor": {
            "IBAN": qr_data[3],
            "Name": qr_data[5],
            "Address": f"{qr_data[6]}, {qr_data[8]} {qr_data[9]}",
            "Postal Code": qr_data[8],
            "City": qr_data[9],
            "Country": qr_data[10]
        },
        "Debtor": {
            "Name": qr_data[21],
            "Address": f"{qr_data[22]}, {qr_data[23]} {qr_data[24]}",
            "Postal Code": qr_data[24],
            "City": qr_data[25],
            "Country": qr_data[26]
        },
        "Amount": f"{qr_data[18]} {qr_data[19]}",
        "QR Reference": qr_data[27],
        "Type": qr_data[2],
        "Payment Type": qr_data[30]
    }
    return formatted_data


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
                formatted_qr_data = format_qr_data(lines)
                
                # Print the formatted QR code data
                for key, value in formatted_qr_data.items():
                    print(f"{key}: {value}")
                
                # Return the QR code data (first found)
                return qr_data

    # If no QR code is found in any of the pages
    print("No QR code found in the document.")
    return None


# Example usage
pdf_path = "fixtures/transfer ge_soft/invoice_example.pdf"
pdf_file = Path(pdf_path)  # Change this to your actual file path
qr_data = extract_qr_from_pdf(pdf_file)
