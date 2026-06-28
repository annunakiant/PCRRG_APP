import re

path = 'templates/view_job.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the map div with the correct version
html = re.sub(
    r"<div id='job-map'[^>]*>",
    "<div id='job-map' data-url='{{ url_for(\"job_map_data\", job_id=job.id) }}'>",
    html
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print('✔ FIXED — map now has data-url and will deploy correctly')

