import requests
import json

# Test Admin Functionality
BASE_URL = "http://localhost:8000"

def test_admin_functionality():
    print("🧪 Testing Admin Functionality")
    
    # 1. Login as admin
    print("\n1. 🔐 Login as admin...")
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@takedown.com", "password": "admin123"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Admin login successful")
    
    # 2. Test admin stats
    print("\n2. 📊 Testing admin stats...")
    stats_response = requests.get(f"{BASE_URL}/api/admin/stats", headers=headers)
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print("✅ Admin stats endpoint working!")
        print(f"   - Total users: {stats['users']['total']}")
        print(f"   - Total cases: {stats['cases']['total']}")
        print(f"   - Overdue cases: {stats['cases']['overdue']}")
    else:
        print(f"❌ Stats failed: {stats_response.status_code}")
        print(stats_response.text)
    
    # 3. Test user management
    print("\n3. 👥 Testing user management...")
    users_response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    
    if users_response.status_code == 200:
        users = users_response.json()
        print(f"✅ User management endpoint working! Found {len(users)} users")
        for user in users[:3]:  # Show first 3 users
            print(f"   - {user['email']} ({user['role']})")
    else:
        print(f"❌ User management failed: {users_response.status_code}")
        print(users_response.text)
    
    # 4. Test recent cases
    print("\n4. 📋 Testing recent cases...")
    cases_response = requests.get(f"{BASE_URL}/api/admin/cases/recent", headers=headers)
    
    if cases_response.status_code == 200:
        cases = cases_response.json()
        print(f"✅ Recent cases endpoint working! Found {len(cases)} cases")
    else:
        print(f"❌ Recent cases failed: {cases_response.status_code}")
        print(cases_response.text)
    
    print("\n🎉 Admin functionality test completed!")

if __name__ == "__main__":
    test_admin_functionality()
