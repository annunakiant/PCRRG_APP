
import os, json, zipfile
from export_pdf import build_full_pdf

def build_zip_package(job, zip_path):
    temp_dir = os.path.dirname(zip_path)
    pdf_path = os.path.join(temp_dir, f"job_{job.id}_full_report.pdf")

    # Build PDF first
    build_full_pdf(job, pdf_path)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:

        # Add PDF
        if os.path.exists(pdf_path):
            z.write(pdf_path, arcname='job_report.pdf')

        # Metadata
        metadata = {
            'job_number': job.job_number,
            'title': job.title,
            'client_name': job.client_name,
            'address': job.address,
            'status': job.status,
            'created_at': str(job.created_at),
            'closed_at': str(job.closed_at)
        }
        z.writestr('metadata.json', json.dumps(metadata, indent=2))

        # Tasks
        tasks = [
            {
                'label': t.label,
                'completed': t.completed,
                'completed_at': str(t.completed_at),
                'template': t.template.name if t.template else None
            }
            for t in job.tasks
        ]
        z.writestr('tasks.json', json.dumps(tasks, indent=2))

        # Packout items
        packout = [
            {
                'name': i.name,
                'quantity': i.quantity,
                'location': i.location,
                'condition': i.condition,
                'notes': i.notes
            }
            for i in job.packout_items
        ]
        z.writestr('packout.json', json.dumps(packout, indent=2))

        # Photos
        for p in job.photos:
            img_path = os.path.join('static', p.filename)
            if os.path.exists(img_path):
                z.write(img_path, arcname=f"photos/{os.path.basename(img_path)}")

        # Packout photos
        for item in job.packout_items:
            for ph in item.photos:
                img_path = os.path.join('static', ph.filename)
                if os.path.exists(img_path):
                    z.write(img_path, arcname=f"packout_photos/{os.path.basename(img_path)}")

        # Contracts
        for c in job.contracts:
            if c.template and c.template.filename:
                c_path = os.path.join('static', 'uploads', 'contracts', c.template.filename)
                if os.path.exists(c_path):
                    z.write(c_path, arcname=f"contracts/{c.template.filename}")
