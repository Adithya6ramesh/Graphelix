#!/usr/bin/env python3
"""
Direct test of admin functionality
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, init_db
from app.models import User, UserRole
from app.routers.admin import get_all_users, get_system_stats, get_recent_cases
from sqlalchemy import select

async def test_admin_direct():
    """Test admin functions directly without HTTP"""
    print("🧪 Testing Admin Functions Directly")
    
    # Initialize database
    await init_db()
    
    # Get database session
    async for db in get_db():
        # Get a test admin user
        admin_query = select(User).where(User.email == "admin@takedown.com")
        admin_result = await db.execute(admin_query)
        admin_user = admin_result.scalar_one_or_none()
        
        if not admin_user:
            print("❌ Admin user not found")
            return
        
        print(f"✅ Found admin user: {admin_user.email}")
        
        # Test get_all_users
        print("\n1. Testing get_all_users...")
        try:
            users = await get_all_users(current_user=admin_user, db=db)
            print(f"✅ Found {len(users)} users")
            for user in users[:3]:
                print(f"   - {user.email} ({user.role})")
        except Exception as e:
            print(f"❌ get_all_users failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test get_system_stats
        print("\n2. Testing get_system_stats...")
        try:
            stats = await get_system_stats(current_user=admin_user, db=db)
            print(f"✅ Stats generated successfully")
            print(f"   - Total users: {stats['users']['total']}")
            print(f"   - Total cases: {stats['cases']['total']}")
        except Exception as e:
            print(f"❌ get_system_stats failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test get_recent_cases
        print("\n3. Testing get_recent_cases...")
        try:
            cases = await get_recent_cases(current_user=admin_user, db=db)
            print(f"✅ Found {len(cases)} recent cases")
        except Exception as e:
            print(f"❌ get_recent_cases failed: {e}")
            import traceback
            traceback.print_exc()
        
        break

if __name__ == "__main__":
    asyncio.run(test_admin_direct())
