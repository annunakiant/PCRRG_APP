with open("app.py", "a", encoding="utf-8") as f:
    f.write("""

# ---------------------------------------------------------
# FIX: Missing delete_photo route (causing BuildError)
# ---------------------------------------------------------
@app.route('/jobs/<int:job_id>/photo/<int:photo_id>/delete', methods=['POST'])
@login_required
def delete_photo(job_id, photo_id):
    photo = JobPhoto.query.get_or_404(photo_id)
    db.session.delete(photo)
    db.session.commit()
    flash('Photo deleted.')
    return redirect(url_for('view_job', job_id=job_id))
""")

print("✔ Added delete_photo route — BuildError fixed.")
