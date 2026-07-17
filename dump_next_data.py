import re
import json

with open('cineplex_showtimes.html', 'r', encoding='utf-8') as f:
    html = f.read()

match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
if match:
    data = json.loads(match.group(1))
    with open('next_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print("Saved to next_data.json")
