"""
Simple test script for backend functionality.
Tests container creation and code execution.
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from services.container_manager import ContainerManager
from services.executor import Executor

async def test_backend():
    """Test backend services."""
    print("Testing Orca Backend...")
    print("=" * 50)
    
    # Test 1: Container Manager initialization
    print("\n1. Testing Container Manager...")
    try:
        container_manager = ContainerManager()
        print("   ✓ ContainerManager initialized")
    except Exception as e:
        print(f"   ✗ ContainerManager failed: {e}")
        return False
    
    # Test 2: Check Docker connection
    print("\n2. Testing Docker connection...")
    try:
        docker_client = container_manager.docker_client
        docker_client.ping()
        print("   ✓ Docker connection OK")
    except Exception as e:
        print(f"   ✗ Docker connection failed: {e}")
        print("   Make sure Docker is running!")
        return False
    
    # Test 3: Check if Docker image exists
    print("\n3. Checking Docker image...")
    try:
        image_name = container_manager.image_name
        docker_client.images.get(image_name)
        print(f"   ✓ Docker image '{image_name}' found")
    except Exception as e:
        print(f"   ✗ Docker image '{image_name}' not found")
        print(f"   Build it with: cd docker/executor && docker build -t {image_name} .")
        return False
    
    # Test 4: Create container
    print("\n4. Testing container creation...")
    test_user_id = "test_user_backend"
    try:
        container = container_manager.get_or_create_container(test_user_id)
        print(f"   ✓ Container created: {container.id[:12]}")
        print(f"   Container name: {container.name}")
        print(f"   Container status: {container.status}")
    except Exception as e:
        print(f"   ✗ Container creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Check kernel connection file
    print("\n5. Checking kernel connection file...")
    try:
        import time
        max_wait = 30
        connection_file = None
        
        for i in range(max_wait):
            connection_info = container_manager.get_container_connection_info(container)
            connection_file = connection_info['connection_file']
            
            if os.path.exists(connection_file):
                print(f"   ✓ Connection file found: {connection_file}")
                # Check if it's valid JSON
                import json
                with open(connection_file, 'r') as f:
                    conn_data = json.load(f)
                print(f"   ✓ Connection file is valid JSON")
                print(f"   Kernel ports: {conn_data.get('shell_port', 'N/A')}")
                break
            else:
                print(f"   Waiting for connection file... ({i+1}/{max_wait})")
                time.sleep(1)
        else:
            print(f"   ✗ Connection file not found after {max_wait} seconds")
            return False
    except Exception as e:
        print(f"   ✗ Connection file check failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Test executor
    print("\n6. Testing executor...")
    try:
        executor = Executor(container_manager)
        print("   ✓ Executor initialized")
    except Exception as e:
        print(f"   ✗ Executor initialization failed: {e}")
        return False
    
    # Test 7: Execute simple code
    print("\n7. Testing code execution...")
    try:
        test_code = 'print("Hello from Orca!")'
        print(f"   Executing: {test_code}")
        result = await executor.execute(
            user_id=test_user_id,
            code=test_code,
            timeout=30
        )
        
        print(f"   ✓ Code executed successfully")
        print(f"   Success: {result['success']}")
        print(f"   Stdout: {result['stdout'].strip()}")
        if result['stderr']:
            print(f"   Stderr: {result['stderr']}")
        if result['plots']:
            print(f"   Plots: {len(result['plots'])}")
        if result['results']:
            print(f"   Results: {len(result['results'])}")
            
    except Exception as e:
        print(f"   ✗ Code execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 8: Execute code with variable
    print("\n8. Testing stateful execution...")
    try:
        test_code = 'x = 42\nprint(f"x = {x}")'
        print(f"   Executing: {test_code}")
        result = await executor.execute(
            user_id=test_user_id,
            code=test_code,
            timeout=30
        )
        
        print(f"   ✓ Stateful execution successful")
        print(f"   Output: {result['stdout'].strip()}")
            
    except Exception as e:
        print(f"   ✗ Stateful execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 50)
    print("✓ All tests passed!")
    print("\nNote: Container will remain running. Clean it up with:")
    print(f"  docker stop {container.name}")
    print(f"  docker rm {container.name}")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_backend())
    sys.exit(0 if success else 1)

