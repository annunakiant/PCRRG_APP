import os, zipfile, io, csv
from export_pdf import build_full_pdf
from app import STATIC_DIR

def build_zip_package(job, output_zip_path):
    pdf_path = output_zip_path.replace('.zip', '.pdf')
    build_full_pdf(job, pdf_path)
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(pdf_path, arcname=os.path.basename(pdf_path))
        for p in job.photos.all():
            img_path = os.path.join(STATIC_DIR, p.filename.lstrip("/"))
            if os.path.exists(img_path):
                zf.write(img_path, arcname=os.path.join("Photos", p.category or "General", os.path.basename(img_path)))
        csv_io = io.StringIO()
        writer = csv.writer(csv_io)
        writer.writerow(["Name","Qty","Location","Condition"])
        for i in job.packout_items.all():
            writer.writerow([i.name, i.quantity, i.location, i.condition])
        zf.writestr("packout_manifest.csv", csv_io.getvalue())
