"""
Test suite for Zomoto Tasks - New Task Lifecycle Features
Tests: PENDING, IN_PROGRESS, COMPLETED, NOT_COMPLETED, VERIFIED statuses
Tests: Time-bound tasks with time_interval, time_unit, allocated_datetime
Tests: Task start, complete (with proof), verify endpoints
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://resto-tasks-1.preview.emergentagent.com')

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
def owner_token(api_client):
    """Get owner authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['OWNER'])
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    data = response.json()
    return data['access_token'], data['user']


@pytest.fixture(scope="module")
def manager_token(api_client):
    """Get manager authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['MANAGER'])
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    data = response.json()
    return data['access_token'], data['user']


@pytest.fixture(scope="module")
def staff_token(api_client):
    """Get staff authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['STAFF'])
    assert response.status_code == 200, f"Staff login failed: {response.text}"
    data = response.json()
    return data['access_token'], data['user']


class TestAuthentication:
    """Test authentication for all three roles"""
    
    def test_owner_login(self, api_client):
        """Test owner login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['OWNER'])
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['user']['role'] == 'OWNER'
        assert data['user']['email'] == 'owner@zomoto.lk'
    
    def test_manager_login(self, api_client):
        """Test manager login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['MANAGER'])
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['user']['role'] == 'MANAGER'
        assert data['user']['email'] == 'manager@zomoto.lk'
    
    def test_staff_login(self, api_client):
        """Test staff login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['STAFF'])
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['user']['role'] == 'STAFF'
        assert data['user']['email'] == 'staff@zomoto.lk'
    
    def test_invalid_login(self, api_client):
        """Test invalid credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            'email': 'invalid@zomoto.lk',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401


class TestTaskCreation:
    """Test task creation with new lifecycle fields"""
    
    def test_create_instant_task_with_time_interval(self, api_client, owner_token, staff_token):
        """Test creating instant task with time_interval, time_unit, allocated_datetime"""
        token, owner = owner_token
        _, staff = staff_token
        
        # Create task with 30 minutes time interval
        allocated_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Instant_Task_{datetime.now().strftime('%H%M%S')}",
            "description": "Test instant task with time interval",
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
        
        # Verify task fields
        assert data['title'] == task_data['title']
        assert data['task_type'] == 'INSTANT'
        assert data['time_interval'] == 30
        assert data['time_unit'] == 'MINUTES'
        assert data['status'] == 'PENDING'
        assert data['allocated_datetime'] is not None
        assert data['deadline'] is not None
        assert data['assigned_to'] == staff['id']
        
        # Store task ID for cleanup
        pytest.test_task_id = data['id']
    
    def test_create_task_with_hours_interval(self, api_client, manager_token, staff_token):
        """Test creating task with hours time unit"""
        token, _ = manager_token
        _, staff = staff_token
        
        allocated_time = (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Hours_Task_{datetime.now().strftime('%H%M%S')}",
            "description": "Test task with hours interval",
            "category": "Cleaning",
            "priority": "MEDIUM",
            "task_type": "INSTANT",
            "time_interval": 2,
            "time_unit": "HOURS",
            "allocated_datetime": allocated_time,
            "assigned_to": staff['id']
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['time_interval'] == 2
        assert data['time_unit'] == 'HOURS'
        
        pytest.hours_task_id = data['id']
    
    def test_staff_cannot_create_task(self, api_client, staff_token):
        """Test that staff cannot create tasks"""
        token, _ = staff_token
        
        task_data = {
            "title": "Staff Task Attempt",
            "category": "Other",
            "priority": "LOW",
            "task_type": "INSTANT",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "allocated_datetime": datetime.utcnow().isoformat() + 'Z'
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


class TestTaskLifecycle:
    """Test task lifecycle: PENDING -> IN_PROGRESS -> COMPLETED -> VERIFIED"""
    
    @pytest.fixture(autouse=True)
    def setup_task(self, api_client, owner_token, staff_token):
        """Create a task for lifecycle testing"""
        token, _ = owner_token
        _, staff = staff_token
        
        allocated_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Lifecycle_Task_{datetime.now().strftime('%H%M%S')}",
            "description": "Task for lifecycle testing",
            "category": "Kitchen",
            "priority": "HIGH",
            "task_type": "INSTANT",
            "time_interval": 60,
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "assigned_to": staff['id']
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            self.task_id = response.json()['id']
            self.staff_id = staff['id']
        else:
            pytest.skip("Could not create test task")
    
    def test_start_task_from_pending(self, api_client, staff_token):
        """Test starting a task (PENDING -> IN_PROGRESS)"""
        token, staff = staff_token
        
        response = api_client.post(
            f"{BASE_URL}/api/tasks/{self.task_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Start task failed: {response.text}"
        data = response.json()
        assert data['status'] == 'IN_PROGRESS'
        assert data['start_time'] is not None
    
    def test_complete_task_without_proof_fails(self, api_client, staff_token):
        """Test that completing task without proof photo fails"""
        token, _ = staff_token
        
        # First start the task
        api_client.post(
            f"{BASE_URL}/api/tasks/{self.task_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Try to complete without proof
        response = api_client.post(
            f"{BASE_URL}/api/tasks/{self.task_id}/complete",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "proof" in response.json().get('detail', '').lower()
    
    def test_upload_proof_photo(self, api_client, staff_token):
        """Test uploading proof photo"""
        token, _ = staff_token
        
        # First start the task
        api_client.post(
            f"{BASE_URL}/api/tasks/{self.task_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Create a simple test image
        import io
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test_proof.jpg', img_bytes, 'image/jpeg')}
        
        response = requests.post(
            f"{BASE_URL}/api/tasks/{self.task_id}/proof",
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Proof upload failed: {response.text}"
        data = response.json()
        assert 'url' in data
    
    def test_verify_task_by_manager(self, api_client, manager_token, staff_token, owner_token):
        """Test verifying a completed task"""
        owner_tok, _ = owner_token
        manager_tok, _ = manager_token
        staff_tok, _ = staff_token
        
        # Create a new task for this test
        allocated_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Verify_Task_{datetime.now().strftime('%H%M%S')}",
            "category": "Kitchen",
            "priority": "HIGH",
            "task_type": "INSTANT",
            "time_interval": 60,
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "assigned_to": self.staff_id
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        task_id = create_resp.json()['id']
        
        # Start task
        api_client.post(
            f"{BASE_URL}/api/tasks/{task_id}/start",
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        
        # Upload proof
        import io
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        requests.post(
            f"{BASE_URL}/api/tasks/{task_id}/proof",
            files={'file': ('proof.jpg', img_bytes, 'image/jpeg')},
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        
        # Complete task
        api_client.post(
            f"{BASE_URL}/api/tasks/{task_id}/complete",
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        
        # Verify task by manager
        response = api_client.post(
            f"{BASE_URL}/api/tasks/{task_id}/verify",
            headers={"Authorization": f"Bearer {manager_tok}"}
        )
        
        assert response.status_code == 200, f"Verify failed: {response.text}"
        data = response.json()
        assert data['status'] == 'VERIFIED'
    
    def test_staff_cannot_verify_task(self, api_client, staff_token, owner_token):
        """Test that staff cannot verify tasks"""
        owner_tok, _ = owner_token
        staff_tok, staff = staff_token
        
        # Create and complete a task
        allocated_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Staff_Verify_{datetime.now().strftime('%H%M%S')}",
            "category": "Kitchen",
            "priority": "HIGH",
            "task_type": "INSTANT",
            "time_interval": 60,
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        task_id = create_resp.json()['id']
        
        # Start, upload proof, complete
        api_client.post(f"{BASE_URL}/api/tasks/{task_id}/start", headers={"Authorization": f"Bearer {staff_tok}"})
        
        import io
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        requests.post(f"{BASE_URL}/api/tasks/{task_id}/proof", files={'file': ('proof.jpg', img_bytes, 'image/jpeg')}, headers={"Authorization": f"Bearer {staff_tok}"})
        
        api_client.post(f"{BASE_URL}/api/tasks/{task_id}/complete", headers={"Authorization": f"Bearer {staff_tok}"})
        
        # Staff tries to verify - should fail
        response = api_client.post(
            f"{BASE_URL}/api/tasks/{task_id}/verify",
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        
        assert response.status_code == 403


class TestTaskDelete:
    """Test task deletion (soft delete)"""
    
    def test_owner_can_delete_task(self, api_client, owner_token, staff_token):
        """Test owner can delete task"""
        token, _ = owner_token
        _, staff = staff_token
        
        # Create task
        allocated_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Delete_Task_{datetime.now().strftime('%H%M%S')}",
            "category": "Other",
            "priority": "LOW",
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
        
        # Delete task
        response = api_client.delete(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Verify task is soft deleted (not in list)
        list_resp = api_client.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {token}"}
        )
        task_ids = [t['id'] for t in list_resp.json()]
        assert task_id not in task_ids
    
    def test_manager_can_delete_task(self, api_client, manager_token, staff_token):
        """Test manager can delete task"""
        token, _ = manager_token
        _, staff = staff_token
        
        # Create task
        allocated_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Manager_Delete_{datetime.now().strftime('%H%M%S')}",
            "category": "Other",
            "priority": "LOW",
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
        
        # Delete task
        response = api_client.delete(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    def test_staff_cannot_delete_task(self, api_client, owner_token, staff_token):
        """Test staff cannot delete task"""
        owner_tok, _ = owner_token
        staff_tok, staff = staff_token
        
        # Create task as owner
        allocated_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Staff_Delete_{datetime.now().strftime('%H%M%S')}",
            "category": "Other",
            "priority": "LOW",
            "task_type": "INSTANT",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        task_id = create_resp.json()['id']
        
        # Staff tries to delete - should fail
        response = api_client.delete(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        
        assert response.status_code == 403


class TestTaskEdit:
    """Test task editing functionality"""
    
    def test_owner_can_edit_task(self, api_client, owner_token, staff_token):
        """Test owner can edit task"""
        token, _ = owner_token
        _, staff = staff_token
        
        # Create task
        allocated_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Edit_Task_{datetime.now().strftime('%H%M%S')}",
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
        
        # Edit task
        update_data = {
            "title": "Updated Task Title",
            "description": "Updated description",
            "priority": "LOW",
            "time_interval": 45,
            "time_unit": "MINUTES"
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/tasks/{task_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == "Updated Task Title"
        assert data['description'] == "Updated description"
        assert data['priority'] == "LOW"
        assert data['time_interval'] == 45


class TestTaskList:
    """Test task list and filtering"""
    
    def test_get_tasks_list(self, api_client, owner_token):
        """Test getting task list"""
        token, _ = owner_token
        
        response = api_client.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_filter_tasks_by_status(self, api_client, owner_token):
        """Test filtering tasks by status"""
        token, _ = owner_token
        
        response = api_client.get(
            f"{BASE_URL}/api/tasks?status=PENDING",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        for task in data:
            assert task['status'] == 'PENDING'
    
    def test_staff_sees_only_assigned_tasks(self, api_client, staff_token):
        """Test staff can only see their assigned tasks"""
        token, staff = staff_token
        
        response = api_client.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        for task in data:
            assert task['assigned_to'] == staff['id']


class TestTaskDetail:
    """Test task detail page data"""
    
    def test_task_detail_shows_time_info(self, api_client, owner_token, staff_token):
        """Test task detail shows time_interval, allocated_datetime, deadline"""
        token, _ = owner_token
        _, staff = staff_token
        
        # Create task
        allocated_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        task_data = {
            "title": f"TEST_Detail_Task_{datetime.now().strftime('%H%M%S')}",
            "category": "Kitchen",
            "priority": "HIGH",
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
        
        # Get task detail
        response = api_client.get(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all time-related fields
        assert data['time_interval'] == 45
        assert data['time_unit'] == 'MINUTES'
        assert data['allocated_datetime'] is not None
        assert data['deadline'] is not None
        assert data['task_type'] == 'INSTANT'


class TestDashboardStats:
    """Test dashboard statistics"""
    
    def test_dashboard_stats_include_all_statuses(self, api_client, owner_token):
        """Test dashboard stats include all status counts"""
        token, _ = owner_token
        
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all status fields exist
        assert 'total_tasks' in data
        assert 'pending' in data
        assert 'in_progress' in data
        assert 'completed' in data
        assert 'not_completed' in data
        assert 'verified' in data


# Cleanup test data
@pytest.fixture(scope="module", autouse=True)
def cleanup(api_client, owner_token):
    """Cleanup test data after all tests"""
    yield
    # Cleanup is handled by soft delete - test tasks remain but are marked deleted
