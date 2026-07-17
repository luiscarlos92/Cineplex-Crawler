import re

with open('cineplex_showtimes.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches_theaters = re.findall(r'"name":"([^"]+(?:Theatre|Cinemas)[^"]*)"', html, re.IGNORECASE)
print("Theaters:", sorted(list(set(matches_theaters))))
