import httpx
import json

def test_timing():
    url = "http://localhost:8077/api/chat/stream"
    payload = {
        "message": "大学の歴史について教えてください",
        "filler_mode": "dynamic"
    }
    
    with httpx.stream("POST", url, json=payload, timeout=30.0) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if data.get("type") == "timing":
                    print("--- TIMING PAYLOAD ---")
                    for k, v in data.items():
                        print(f"{k}: {v}")

if __name__ == "__main__":
    test_timing()
