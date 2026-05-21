import requests

url = 'http://localhost:8076/rag/upload'
files = {'file': open('dummy.csv', 'rb')}
data = {'source': 'dummy.csv'}

try:
    response = requests.post(url, files=files, data=data)
    print("Status:", response.status_code)
    print("Body:", response.text)
except Exception as e:
    print("Error:", e)
