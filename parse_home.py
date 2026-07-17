import re

with open('cineplex_home.html', 'r', encoding='utf-8') as f:
    html = f.read()

links = set(re.findall(r'href=[\'"]([^\'"]+)[\'"]', html))
theatre_links = [l for l in links if 'theatre' in l.lower()]
print("Found theatre links:")
for l in theatre_links:
    print(l)
