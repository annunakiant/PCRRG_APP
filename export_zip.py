import os
import zipfile
import io
import csv
from export_pdf import build_full_pdf
from app import STATIC_DIR

def build_zip_package(job, output_zip_path):
    pdf_path = output_zip_path.replace('.zip', '.pdf')
    build_full_pdf(job, pdf_path)
    
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(pdf_path):
            zf.write(pdf_path, arcname=os.path.basename(pdf_path))
            
        for p in job.photos.all():
            clean_filename = p.filename.replace("\\\\", "/").replace("\\", "/").lstrip("/")
            img_path = os.path.join(STATIC_DIR, clean_filename)
            if os.path.exists(img_path):
                zf.write(img_path, arcname=f"photos/{os.path.basename(img_path)}")
                
        csv_io = io.StringIO()
        writer = csv.writer(csv_io)
        writer.writerow(["Name", "Quantity", "Location", "Condition", "Notes"])
        for item in job.packout_items.all():
            writer.writerow([item.name, item.quantity, item.location or "", item.condition or "", item.notes or ""])
        zf.writestr("packout_manifest.csv", csv_io.getvalue())
