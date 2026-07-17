import urllib.request
import json
import base64

url = "https://api.github.com/repos/sinfran/cineplex-scraper/contents/"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        for file in data:
            if file['name'].endswith('.py'):
                file_req = urllib.request.Request(file['download_url'], headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(file_req) as file_resp:
                    content = file_resp.read().decode()
                    if 'cineplex.com' in content:
                        print("Found in", file['name'])
                        lines = content.split('\n')
                        for line in lines:
                            if 'http' in line:
                                print(line.strip())
except Exception as e:
    print("Error:", e)
