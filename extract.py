import re

with open('cineplex_showtimes.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find all matches of "ExperienceName":"..." or something similar,
# or simply find "UltraAVX" and print surrounding 100 characters.
matches = re.finditer(r'(.{0,50}UltraAVX.{0,50})', html, re.IGNORECASE)
with open('output_avx.txt', 'w', encoding='utf-8') as out:
    for m in matches:
        out.write(m.group(1) + '\n')
