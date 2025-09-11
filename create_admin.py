#!/usr/bin/env python3
"""
Create initial admin user for the Take It Down system.
Run this script to create the first admin account.
"""
import asyncio
import sys
from app.database import get_db_session, init_db
from app.models.user import User, UserRole
from app.auth import get_password_hash
from sqlalchemy import select

async def create_admin_user():
    """Create an admin user"""
    print("🔧 Take It Down - Admin User Creation")
    print("=" * 50)
    
    # Initialize database
    await init_db()
    
    # Get user input
    email = input("Enter admin email: ").strip()
    if not email:
        print("❌ Email is required")
        return
    
    password = input("Enter admin password: ").strip()
    if not password:
        print("❌ Password is required")
        return
    
    # Check if user already exists
    async with get_db_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"❌ User with email {email} already exists")
            return
        
        # Create admin user
        hashed_password = get_password_hash(password)
        admin_user = User(
            email=email,
            hashed_password=hashed_password,
            role=UserRole.ADMIN
        )
        
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)
        
        print(f"✅ Admin user created successfully!")
        print(f"📧 Email: {admin_user.email}")
        print(f"👑 Role: {admin_user.role}")
        print(f"🆔 ID: {admin_user.id}")
        print("\nYou can now login with these credentials.")

if __name__ == "__main__":
    try:
        asyncio.run(create_admin_user())
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
