#!/bin/bash

# Test API Keys Configuration
# Checks that all required API keys are configured and working

echo "Testing API Keys Configuration..."
echo "=================================="

cd "$(dirname "$0")/backend" || exit

# Activate virtual environment
source venv/bin/activate

# Create test script
cat > test_keys.py << 'EOF'
"""Test API keys configuration"""
import sys
from config import settings

print("\n🔑 Checking API Keys Configuration...\n")

errors = []
warnings = []

# Check Anthropic API key
try:
    if settings.anthropic_api_key and settings.anthropic_api_key.startswith("sk-ant-"):
        print("✅ Anthropic API key: Configured")

        # Test connection
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=50,
                messages=[{"role": "user", "content": "Say 'ok'"}]
            )
            print("   ✓ Connection test: PASSED")
        except Exception as e:
            errors.append(f"Anthropic API connection failed: {e}")
            print(f"   ✗ Connection test: FAILED - {e}")
    else:
        errors.append("Anthropic API key not configured or invalid format")
        print("❌ Anthropic API key: NOT CONFIGURED")
except Exception as e:
    errors.append(f"Anthropic config error: {e}")
    print(f"❌ Anthropic API key: ERROR - {e}")

# Check Tavily API key
try:
    if settings.tavily_api_key and len(settings.tavily_api_key) > 10:
        print("✅ Tavily API key: Configured")

        # Test connection
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.tavily_api_key)
            result = client.search(query="test", max_results=1)
            print("   ✓ Connection test: PASSED")
        except Exception as e:
            warnings.append(f"Tavily API connection warning: {e}")
            print(f"   ⚠ Connection test: WARNING - {e}")
    else:
        warnings.append("Tavily API key not configured (optional for MVP)")
        print("⚠️  Tavily API key: NOT CONFIGURED (optional)")
except Exception as e:
    warnings.append(f"Tavily config warning: {e}")
    print(f"⚠️  Tavily API key: WARNING - {e}")

# Check Reddit credentials
try:
    if (settings.reddit_client_id and settings.reddit_client_secret
        and len(settings.reddit_client_id) > 5):
        print("✅ Reddit API credentials: Configured")

        # Test connection
        try:
            import praw
            reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent
            )
            # Test by checking if we can access read-only endpoint
            subreddit = reddit.subreddit("test")
            _ = subreddit.display_name
            print("   ✓ Connection test: PASSED")
        except Exception as e:
            errors.append(f"Reddit API connection failed: {e}")
            print(f"   ✗ Connection test: FAILED - {e}")
    else:
        errors.append("Reddit API credentials not configured")
        print("❌ Reddit API credentials: NOT CONFIGURED")
except Exception as e:
    errors.append(f"Reddit config error: {e}")
    print(f"❌ Reddit API credentials: ERROR - {e}")

# Summary
print("\n" + "="*50)
print("SUMMARY")
print("="*50)

if errors:
    print(f"\n❌ {len(errors)} ERROR(S):")
    for error in errors:
        print(f"   - {error}")

if warnings:
    print(f"\n⚠️  {len(warnings)} WARNING(S):")
    for warning in warnings:
        print(f"   - {warning}")

if not errors:
    print("\n✅ All required API keys are configured!")
    print("\nYou can now:")
    print("  1. Start backend: ./start-backend.sh")
    print("  2. Test scraping: visit http://localhost:8000/docs")
    sys.exit(0)
else:
    print("\n❌ Please configure missing API keys in .env file")
    print("\nSee README.md for instructions on obtaining API keys")
    sys.exit(1)
EOF

# Run test
PYTHONPATH=. python test_keys.py

# Cleanup
rm test_keys.py
