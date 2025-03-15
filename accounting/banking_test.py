'''
accounting/banking_test.py

'''
from pathlib import Path
from banking import extract_qr_from_pdf

# Example usage
if True:
    pdf_path = "fixtures/transfer ge_soft/1_PDFsam_Rechnungen Zahlungslauf.pdf"
    pdf_file = Path(pdf_path)  # Change this to your actual file path
    qr_data = extract_qr_from_pdf(pdf_file)
    print("qr_data", qr_data)
    
    