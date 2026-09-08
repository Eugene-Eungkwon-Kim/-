#!/usr/bin/env python3
import os
import requests
from datetime import datetime
import json

os.environ.setdefault("ENVIRONMENT", "development")

def test_datagovkr_api():
    """Task 0.1: Test Data.go.kr API credentials"""
    # 원래 이 테스트에 박혀 있던 값은 짧은 형식(DATAGOVKR_API_KEY)이 아니라
    # data.go.kr 의 긴 base64 "일반 인증키(Decoding)" 형식이었다. 두 키가
    # 실제로 같은 계정인지 확인되지 않아 별도 이름으로 구분해 둔다.
    api_key = os.environ.get("DATAGOVKR_DECODING_KEY", "")

    url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSAptTradeDev"
    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 10,
        "DEAL_YMD": "202406",
        "type": "json"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        status = response.status_code

        if status == 200:
            data = response.json()
            print(f"✅ API Test Success (HTTP {status})")
            print(f"   Response keys: {list(data.keys())}")
            return {"status": "ok", "http_code": status, "timestamp": datetime.now().isoformat()}
        else:
            print(f"⚠️ API Test Warning (HTTP {status})")
            print(f"   Response: {response.text[:200]}")
            return {"status": "warning", "http_code": status, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        print(f"❌ API Test Failed: {str(e)}")
        return {"status": "error", "error": str(e), "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    result = test_datagovkr_api()
    print(json.dumps(result, indent=2, ensure_ascii=False))
