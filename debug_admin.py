import requests
import json

# Simple debug test
BASE_URL = "http://localhost:8000"

def debug_admin():
    # Login
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@takedown.com", "password": "admin123"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test users endpoint with error details
    print("Testing users endpoint...")
    try:
        users_response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        if users_response.status_code == 200:
            print("✅ Users endpoint working!")
            users = users_response.json()
            print(f"Found {len(users)} users")
        else:
            print(f"❌ Users endpoint failed: {users_response.status_code}")
            print("Response text:", users_response.text)
    except Exception as e:
        print(f"❌ Exception in users: {e}")
    
    # Test cases endpoint
    print("\nTesting cases endpoint...")
    try:
        cases_response = requests.get(f"{BASE_URL}/api/admin/cases/recent", headers=headers)
        if cases_response.status_code == 200:
            print("✅ Cases endpoint working!")
            cases = cases_response.json()
            print(f"Found {len(cases)} cases")
        else:
            print(f"❌ Cases endpoint failed: {cases_response.status_code}")
            print("Response text:", cases_response.text)
    except Exception as e:
        print(f"❌ Exception in cases: {e}")

if __name__ == "__main__":
    debug_admin()
