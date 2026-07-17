import re

with open('cineplex_theatres.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Look for Scotiabank Theatre
print("Scotiabank found" if "Scotiabank" in html else "Scotiabank not found")

# Look for all Cineplex theatres
matches = re.findall(r'"name":"([^"]+)"', html)
cinemas = [m for m in matches if 'Cineplex' in m or 'Theatre' in m or 'Cinema' in m]
print(sorted(list(set(cinemas))))
