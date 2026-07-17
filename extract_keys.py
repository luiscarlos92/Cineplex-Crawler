import re
import json

with open('cineplex_showtimes.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Look for any JSON-like structures that might contain theaters
keys = set(re.findall(r'"([a-zA-Z]*[tT]heatre[a-zA-Z]*)":', html))
print("Keys with 'theatre':", keys)

# Let's just find anything matching "name":"..." and see if any look like theaters
names = re.findall(r'"name":"([^"]+)"', html)
theaters = [n for n in names if 'Cinemas' in n or 'Theatre' in n or 'Cineplex' in n]
print("Found theaters via 'name':", set(theaters))

# Alternatively, search for the global __NEXT_DATA__
match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
if match:
    try:
        data = json.loads(match.group(1))
        print("NEXT_DATA found! Keys at root:", data.keys())
    except Exception as e:
        print("JSON parse error:", e)
else:
    print("No NEXT_DATA script found.")
