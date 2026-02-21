"""
Comprehensive test suite for Zomoto Tasks - Restaurant Task Management System
Tests all CRUD operations, task lifecycle, templates, categories, and users
Migrated from MongoDB to MySQL - verifying datetime handling fixes
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://zomoto-tasks.preview.emergentagent.com')

# Test credentials
CREDENTIALS = {
    'OWNER': {'email': 'owner@zomoto.lk', 'password': '123456'},
    'MANAGER': {'email': 'manager@zomoto.lk', 'password': '123456'},
    'STAFF': {'email': 'staff@zomoto.lk', 'password': '123456'}
}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def owner_auth(api_client):
    """Get owner authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['OWNER'])
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    data = response.json()
    return data['access_token'], data['user']


@pytest.fixture(scope="module")
def manager_auth(api_client):
    """Get manager authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['MANAGER'])
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    data = response.json()
    return data['access_token'], data['user']


@pytest.fixture(scope="module")
def staff_auth(api_client):
    """Get staff authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['STAFF'])
    assert response.status_code == 200, f"Staff login failed: {response.text}"
    data = response.json()
    return data['access_token'], data['user']


# ===================== AUTHENTICATION TESTS =====================
class TestAuthentication:
    """Test login for all three roles"""
    
    def test_owner_login_success(self, api_client):
        """Owner login with owner@zomoto.lk / 123456 should succeed"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['OWNER'])
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['user']['role'] == 'OWNER'
        assert data['user']['email'] == 'owner@zomoto.lk'
        print(f"✓ Owner login successful: {data['user']['name']}")
    
    def test_manager_login_success(self, api_client):
        """Manager login with manager@zomoto.lk / 123456 should succeed"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['MANAGER'])
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['user']['role'] == 'MANAGER'
        assert data['user']['email'] == 'manager@zomoto.lk'
        print(f"✓ Manager login successful: {data['user']['name']}")
    
    def test_staff_login_success(self, api_client):
        """Staff login with staff@zomoto.lk / 123456 should succeed"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['STAFF'])
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['user']['role'] == 'STAFF'
        assert data['user']['email'] == 'staff@zomoto.lk'
        print(f"✓ Staff login successful: {data['user']['name']}")
    
    def test_invalid_credentials_rejected(self, api_client):
        """Invalid credentials should return 401"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            'email': 'invalid@zomoto.lk',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401


# ===================== TASK TESTS =====================
class TestTaskOperations:
    """Test all task CRUD operations - previously caused TypeError with datetime"""
    
    def test_get_tasks_list_no_error(self, api_client, owner_auth):
        """GET /api/tasks should return tasks list without errors"""
        token, _ = owner_auth
        response = api_client.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /api/tasks failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/tasks returned {len(data)} tasks")
    
    def test_create_instant_task_success(self, api_client, owner_auth, staff_auth):
        """POST /api/tasks should create an instant task successfully"""
        token, _ = owner_auth
        _, staff = staff_auth
        
        allocated_time = datetime.utcnow().isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Instant_Task_{datetime.now().strftime('%H%M%S')}",
            "description": "Test instant task creation",
            "category": "Kitchen",
            "priority": "HIGH",
            "task_type": "INSTANT",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "assigned_to": staff['id']
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Task creation failed: {response.text}"
        data = response.json()
        
        # Verify response data
        assert data['title'] == task_data['title']
        assert data['task_type'] == 'INSTANT'
        assert data['time_interval'] == 30
        assert data['time_unit'] == 'MINUTES'
        assert data['status'] == 'PENDING'
        assert data['allocated_datetime'] is not None
        assert data['deadline'] is not None
        assert data['id'] is not None
        
        print(f"✓ Created instant task: {data['id']}")
        return data['id']
    
    def test_create_recurring_task_success(self, api_client, owner_auth, staff_auth):
        """POST /api/tasks should create a recurring task successfully"""
        token, _ = owner_auth
        _, staff = staff_auth
        
        allocated_time = datetime.utcnow().isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Recurring_Task_{datetime.now().strftime('%H%M%S')}",
            "description": "Test recurring task creation",
            "category": "Cleaning",
            "priority": "MEDIUM",
            "task_type": "RECURRING",
            "time_interval": 60,
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "recurrence_pattern": "MONTHLY",
            "recurrence_intervals": [1, 5, 10, 15, 20, 25],
            "assigned_to": staff['id']
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Recurring task creation failed: {response.text}"
        data = response.json()
        
        assert data['task_type'] == 'RECURRING'
        assert data['recurrence_intervals'] == [1, 5, 10, 15, 20, 25]
        print(f"✓ Created recurring task: {data['id']}")
        return data['id']
    
    def test_get_task_details_success(self, api_client, owner_auth, staff_auth):
        """GET /api/tasks/{task_id} should return task details"""
        token, _ = owner_auth
        _, staff = staff_auth
        
        # First create a task
        allocated_time = datetime.utcnow().isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Detail_Task_{datetime.now().strftime('%H%M%S')}",
            "category": "Maintenance",
            "priority": "LOW",
            "task_type": "INSTANT",
            "time_interval": 45,
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        task_id = create_resp.json()['id']
        
        # Get task details
        response = api_client.get(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"GET task detail failed: {response.text}"
        data = response.json()
        
        assert data['id'] == task_id
        assert data['title'] == task_data['title']
        assert data['time_interval'] == 45
        assert data['time_unit'] == 'MINUTES'
        assert data['allocated_datetime'] is not None
        assert data['deadline'] is not None
        print(f"✓ GET /api/tasks/{task_id} returned task details")
    
    def test_update_task_success(self, api_client, owner_auth, staff_auth):
        """PUT /api/tasks/{task_id} should update a task successfully"""
        token, _ = owner_auth
        _, staff = staff_auth
        
        # Create a task
        allocated_time = datetime.utcnow().isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Update_Task_{datetime.now().strftime('%H%M%S')}",
            "category": "Kitchen",
            "priority": "HIGH",
            "task_type": "INSTANT",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        task_id = create_resp.json()['id']
        
        # Update task
        update_data = {
            "title": "Updated Task Title",
            "description": "Updated description",
            "priority": "LOW",
            "time_interval": 60,
            "time_unit": "MINUTES"
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/tasks/{task_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Task update failed: {response.text}"
        data = response.json()
        
        assert data['title'] == "Updated Task Title"
        assert data['description'] == "Updated description"
        assert data['priority'] == "LOW"
        assert data['time_interval'] == 60
        print(f"✓ PUT /api/tasks/{task_id} updated successfully")
    
    def test_start_task_success(self, api_client, owner_auth, staff_auth):
        """POST /api/tasks/{task_id}/start should start a task"""
        owner_token, _ = owner_auth
        staff_token, staff = staff_auth
        
        # Create task assigned to staff
        allocated_time = datetime.utcnow().isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Start_Task_{datetime.now().strftime('%H%M%S')}",
            "category": "Kitchen",
            "priority": "HIGH",
            "task_type": "INSTANT",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        task_id = create_resp.json()['id']
        
        # Start task as staff
        response = api_client.post(
            f"{BASE_URL}/api/tasks/{task_id}/start",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        
        assert response.status_code == 200, f"Start task failed: {response.text}"
        data = response.json()
        
        assert data['status'] == 'IN_PROGRESS'
        assert data['started_at'] is not None
        print(f"✓ POST /api/tasks/{task_id}/start succeeded - status: IN_PROGRESS")


# ===================== TASK TEMPLATE TESTS =====================
class TestTaskTemplates:
    """Test task template operations"""
    
    def test_create_template_success(self, api_client, owner_auth):
        """POST /api/task-templates should create a template successfully"""
        token, _ = owner_auth
        
        template_data = {
            "title": f"TEST_Template_{datetime.now().strftime('%H%M%S')}",
            "description": "Test template",
            "category": "Kitchen",
            "priority": "HIGH",
            "time_interval": 30,
            "time_unit": "MINUTES"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/task-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Template creation failed: {response.text}"
        data = response.json()
        
        assert data['title'] == template_data['title']
        assert data['category'] == 'Kitchen'
        assert data['priority'] == 'HIGH'
        print(f"✓ POST /api/task-templates created: {data['id']}")
    
    def test_get_templates_list(self, api_client, owner_auth):
        """GET /api/task-templates should list templates"""
        token, _ = owner_auth
        
        response = api_client.get(
            f"{BASE_URL}/api/task-templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/task-templates returned {len(data)} templates")


# ===================== CATEGORY TESTS =====================
class TestCategories:
    """Test category operations"""
    
    def test_get_categories_returns_seeded(self, api_client, owner_auth):
        """GET /api/categories should return seeded categories"""
        token, _ = owner_auth
        
        response = api_client.get(
            f"{BASE_URL}/api/categories",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"GET categories failed: {response.text}"
        data = response.json()
        
        # Verify seeded categories exist
        category_names = [c['name'] for c in data]
        expected_categories = ['Kitchen', 'Cleaning', 'Maintenance', 'Other']
        
        for expected in expected_categories:
            assert expected in category_names, f"Category '{expected}' not found"
        
        print(f"✓ GET /api/categories returned seeded categories: {category_names}")


# ===================== USER TESTS =====================
class TestUsers:
    """Test user operations"""
    
    def test_get_users_returns_seeded(self, api_client, owner_auth):
        """GET /api/users should return seeded users"""
        token, _ = owner_auth
        
        response = api_client.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"GET users failed: {response.text}"
        data = response.json()
        
        # Verify seeded users exist
        user_emails = [u['email'] for u in data]
        expected_users = ['owner@zomoto.lk', 'manager@zomoto.lk', 'staff@zomoto.lk']
        
        for expected in expected_users:
            assert expected in user_emails, f"User '{expected}' not found"
        
        print(f"✓ GET /api/users returned seeded users: {user_emails}")


# ===================== DASHBOARD TESTS =====================
class TestDashboard:
    """Test dashboard stats"""
    
    def test_dashboard_stats_returns_counts(self, api_client, owner_auth):
        """GET /api/dashboard/stats should return task stats"""
        token, _ = owner_auth
        
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"GET dashboard stats failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        required_fields = ['total_tasks', 'in_progress', 'completed', 'verified', 'tasks_to_assign', 'tasks_to_verify', 'staff_count']
        for field in required_fields:
            assert field in data, f"Field '{field}' missing from dashboard stats"
        
        print(f"✓ Dashboard stats: total={data['total_tasks']}, in_progress={data['in_progress']}, completed={data['completed']}")


# ===================== CLEANUP =====================
@pytest.fixture(scope="module", autouse=True)
def cleanup(api_client, owner_auth):
    """Cleanup test data after tests"""
    yield
    # Test tasks with TEST_ prefix will be cleaned up or ignored
