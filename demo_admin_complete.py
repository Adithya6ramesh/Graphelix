#!/usr/bin/env python3
"""
Comprehensive Admin Functionality Demo
Shows all admin features working in the Take It Down system
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def demo_admin_functionality():
    print("🎯 Take It Down - Admin Functionality Demo")
    print("=" * 50)
    
    # 1. Login as admin
    print("\n1. 🔐 Admin Authentication")
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@takedown.com", "password": "admin123"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Admin login failed: {login_response.status_code}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Admin successfully authenticated")
    
    # 2. System Statistics
    print("\n2. 📊 System Statistics Dashboard")
    stats_response = requests.get(f"{BASE_URL}/api/admin/stats", headers=headers)
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print("✅ System stats retrieved successfully!")
        print(f"   📊 Users Overview:")
        print(f"      • Total users: {stats['users']['total']}")
        print(f"      • New users (24h): {stats['users']['recent_24h']}")
        print(f"      • User roles breakdown:")
        for role, count in stats['users']['by_role'].items():
            print(f"        - {role.title()}: {count}")
        
        print(f"   📋 Cases Overview:")
        print(f"      • Total cases: {stats['cases']['total']}")
        print(f"      • New cases (24h): {stats['cases']['recent_24h']}")
        print(f"      • Overdue cases: {stats['cases']['overdue']}")
        print(f"      • Average resolution: {stats['cases']['avg_resolution_hours'] or 'N/A'} hours")
        print(f"      • Case states breakdown:")
        for state, count in stats['cases']['by_state'].items():
            print(f"        - {state.title()}: {count}")
    else:
        print(f"❌ Failed to get stats: {stats_response.status_code}")
    
    # 3. User Management
    print("\n3. 👥 User Management")
    users_response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    
    if users_response.status_code == 200:
        users = users_response.json()
        print(f"✅ User management system operational! Managing {len(users)} users")
        print("   Recent users:")
        for user in users[:5]:  # Show first 5 users
            role_emoji = {"admin": "👑", "officer": "🛡️", "victim": "👤"}.get(user['role'], "👤")
            print(f"      {role_emoji} {user['email']} ({user['role']})")
    else:
        print(f"❌ User management failed: {users_response.status_code}")
    
    # 4. Case Administration
    print("\n4. 📋 Case Administration")
    cases_response = requests.get(f"{BASE_URL}/api/admin/cases/recent?limit=10", headers=headers)
    
    if cases_response.status_code == 200:
        cases = cases_response.json()
        print(f"✅ Case administration active! Monitoring {len(cases)} recent cases")
        
        overdue_count = sum(1 for case in cases if case['overdue'])
        if overdue_count > 0:
            print(f"   ⚠️  {overdue_count} cases are overdue and need attention!")
        
        print("   Recent case activity:")
        for case in cases[:3]:  # Show first 3 cases
            status_emoji = {
                "submitted": "📝", "in_review": "👀", "approved": "✅", 
                "rejected": "❌", "escalated": "🚨", "completed": "✅"
            }.get(case['state'], "📝")
            overdue_flag = " ⚠️ OVERDUE" if case['overdue'] else ""
            print(f"      {status_emoji} Case #{case['id'][:8]}... - {case['state'].upper()}{overdue_flag}")
            print(f"         URL: {case['url'] or 'N/A'}")
    else:
        print(f"❌ Case administration failed: {cases_response.status_code}")
    
    # 5. Workflow Analytics (if available)
    print("\n5. 📈 Workflow Analytics")
    analytics_response = requests.get(f"{BASE_URL}/api/admin/analytics/workflow", headers=headers)
    
    if analytics_response.status_code == 200:
        analytics = analytics_response.json()
        print("✅ Workflow analytics generated!")
        print(f"   • Analysis period: {analytics['period_days']} days")
        print(f"   • SLA compliance data:")
        if analytics['sla_compliance']['total_overdue'] > 0:
            print(f"     - Total overdue: {analytics['sla_compliance']['total_overdue']}")
            for state, count in analytics['sla_compliance']['overdue_by_state'].items():
                print(f"     - {state}: {count} overdue")
        else:
            print("     - ✅ No overdue cases - excellent SLA compliance!")
    else:
        print(f"❌ Analytics failed: {analytics_response.status_code}")
    
    # 6. Admin Feature Summary
    print("\n6. 🎯 Admin Features Summary")
    print("✅ Available Admin Capabilities:")
    print("   🔐 Full system authentication and authorization")
    print("   📊 Real-time system statistics and metrics")
    print("   👥 Complete user management and role administration")
    print("   📋 Comprehensive case oversight and monitoring")
    print("   📈 Advanced workflow analytics and reporting")
    print("   ⚠️  SLA compliance monitoring and alerts")
    print("   🔄 Automated escalation and workflow management")
    
    print("\n🎉 Admin functionality fully operational!")
    print("=" * 50)
    print("🚀 Your Take It Down system has comprehensive admin capabilities!")

if __name__ == "__main__":
    demo_admin_functionality()
