
import time
import requests
import sys

BASE_URL = "http://127.0.0.1:8000/items"
KEY = "test_verification_key"
VALUE = "verification_value_123"

def verify_cache():
    print(f"--- Starting Cache Verification for key: {KEY} ---")

    # 1. Test Cache Miss
    print("\n1. Testing Cache Miss...")
    try:
        response = requests.get(f"{BASE_URL}/cache/{KEY}")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "MISS":
                print("✅ Success: Cache MISS as expected.")
            else:
                print(f"❌ Failure: Expected MISS, got {data}")
        else:
            print(f"❌ Failure: Status code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return

    # 2. Trigger Compute
    print("\n2. Triggering Computation...")
    try:
        response = requests.post(f"{BASE_URL}/cache/compute/{KEY}", data={"value": VALUE})
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            if task_id:
                print(f"✅ Success: Computation triggered. Task ID: {task_id}")
            else:
                print(f"❌ Failure: No task ID returned. {data}")
        else:
            print(f"❌ Failure: Status code {response.status_code}")
            print(response.text)
            return
    except Exception as e:
        print(f"❌ Error triggering computation: {e}")
        return

    # 3. Wait for Celery Task
    print("\n3. Waiting for 7 seconds (processing simulation)...")
    time.sleep(7)

    # 4. Test Cache Hit
    print("\n4. Testing Cache Hit...")
    try:
        response = requests.get(f"{BASE_URL}/cache/{KEY}")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "HIT" and data.get("value") == VALUE:
                print(f"✅ Success: Cache HIT with correct value: {data.get('value')}")
            else:
                print(f"❌ Failure: Expected HIT with '{VALUE}', got {data}")
        else:
            print(f"❌ Failure: Status code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")

if __name__ == "__main__":
    verify_cache()
