import os
from datetime import datetime
from collections import defaultdict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter

def generate_pdf_report(job, JobPhoto, STATIC_DIR, ARCHIVE_FOLDER, send_from_directory_func):
    photos = job.photos.order_by(JobPhoto.uploaded_at.asc()).all()
    
    # Auto-sort photos by your exact UI categories
    categories = defaultdict(list)
    for p in photos:
        cat = p.category or "General Evidence Logs"
        categories[cat].append(p)

    export_dir = os.path.join(ARCHIVE_FOLDER, 'exports')
    os.makedirs(export_dir, exist_ok=True)
    filename = f"Job_{job.job_number}_Professional_Report.pdf"
    path = os.path.join(export_dir, filename)

    # Build landscape PDF
    pdf = canvas.Canvas(path, pagesize=landscape(letter))
    page_w, page_h = landscape(letter)

    # Professional Insurance-Ready Cover Page
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(50, page_h - 70, "Professional Cleaning Restoration & Rehab Services Group")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, page_h - 100, f"Claims Evidence Package — {job.job_number}")
    
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, page_h - 150, f"Title: {job.title}")
    pdf.drawString(50, page_h - 170, f"Client: {job.client_name or 'N/A'}")
    pdf.drawString(50, page_h - 190, f"Property Address: {job.address or 'N/A'}")
    pdf.drawString(50, page_h - 210, f"Status: {job.status.upper()}")
    pdf.drawString(50, page_h - 230, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    pdf.showPage()

    # --- PERFECT 8-GRID LAYOUT (4 Columns x 2 Rows) ---
    per_row = 4
    per_page = 8
    thumb_w = 165
    thumb_h = 165
    padding_x = 18
    padding_y = 45
    start_x = 35
    start_y = page_h - 90

    for cat, cat_photos in categories.items():
        index = 0
        while index < len(cat_photos):
            chunk = cat_photos[index:index + per_page]
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(start_x, page_h - 40, f"Evidence Group: {cat.upper()}")

            for i, p in enumerate(chunk):
                row = i // per_row
                col = i % per_row
                x = start_x + col * (thumb_w + padding_x)
                y = start_y - row * (thumb_h + padding_y) - thumb_h

                # Normalize file paths for cross-platform stability
                clean_filename = p.filename.replace("\\\\", "/").replace("\\", "/").lstrip("/")
                abs_path = os.path.join(STATIC_DIR, clean_filename)
                try:
                    pdf.drawImage(abs_path, x, y, width=thumb_w, height=thumb_h, preserveAspectRatio=True, anchor='c')
                except:
                    pdf.rect(x, y, thumb_w, thumb_h)
                    pdf.setFont("Helvetica", 9)
                    pdf.drawString(x + 15, y + thumb_h / 2, "[Image Missing]")

                meta_y = y - 12
                pdf.setFont("Helvetica", 8)
                meta = [f"ID: #{p.id}"]
                if p.uploaded_at:
                    meta.append(p.uploaded_at.strftime("%m/%d/%Y %H:%M"))
                pdf.drawString(x, meta_y, " | ".join(meta))

            pdf.showPage()
            index += per_page

    pdf.save()
    return send_from_directory_func(export_dir, filename, as_attachment=True)


def generate_zip_package(job, JobPhoto, PackoutItem, JobContract, JobTask, STATIC_DIR, ARCHIVE_FOLDER, send_from_directory_func):
    import zipfile, io, csv, json as _json
    export_dir = os.path.join(ARCHIVE_FOLDER, 'exports')
    os.makedirs(export_dir, exist_ok=True)
    filename = f"Job_{job.job_number}_Package.zip"
    path = os.path.join(export_dir, filename)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        # Segment images directly into matching category folders inside the ZIP container
        for p in job.photos.all():
            clean_filename = p.filename.replace("\\\\", "/").replace("\\", "/").lstrip("/")
            abs_img_path = os.path.join(STATIC_DIR, clean_filename)
            if os.path.exists(abs_img_path):
                folder_name = p.category or "General_Evidence"
                z.write(abs_img_path, arcname=os.path.join("Claim_Photos", folder_name, os.path.basename(abs_img_path)))

        # Append structured CSV manifests
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Item Name", "Quantity", "Location Logged", "Condition Assessment", "Notes"])
        for item in job.packout_items.all():
            writer.writerow([item.name, item.quantity, item.location or "", item.condition or "", item.notes or ""])
        z.writestr("packout_inventory_manifest.csv", csv_buffer.getvalue())

    return send_from_directory_func(export_dir, filename, as_attachment=True)
