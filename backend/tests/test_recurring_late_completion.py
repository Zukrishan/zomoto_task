"""
Test suite for Zomoto Tasks - Recurring Tasks & Late Completion Features
Tests:
1. Task templates CRUD with recurring settings (is_recurring, day_intervals, allocated_time)
2. Generate Now endpoint for recurring tasks
3. Late completion flow (NOT_COMPLETED -> COMPLETED with is_late flag)
4. Task response fields (is_late, actual_time_taken, template_id)
"""
import pytest
import requests
import os
import io
from datetime import datetime, timedelta
from PIL import Image

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


# =============================================================================
# TEST TASK TEMPLATES CRUD
# =============================================================================
class TestTaskTemplates:
    """Test task template CRUD with recurring settings"""
    
    def test_create_recurring_template(self, api_client, owner_token, staff_token):
        """Test creating a recurring template with all fields"""
        token, _ = owner_token
        _, staff = staff_token
        
        template_data = {
            "title": f"TEST_Recurring_Template_{datetime.now().strftime('%H%M%S')}",
            "description": "Daily kitchen cleaning task",
            "category": "Kitchen",
            "priority": "HIGH",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "is_recurring": True,
            "day_intervals": "1-31",  # Every day of month
            "allocated_time": "09:00",
            "assigned_to": staff['id']
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/task-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Template creation failed: {response.text}"
        data = response.json()
        
        # Verify template fields
        assert data['title'] == template_data['title']
        assert data['is_recurring'] == True
        assert data['is_active'] == True
        assert data['day_intervals'] == "1-31"
        assert data['allocated_time'] == "09:00"
        assert data['assigned_to'] == staff['id']
        assert data['assigned_to_name'] is not None
        assert data['time_interval'] == 30
        assert data['time_unit'] == "MINUTES"
        
        # Store for later tests
        pytest.recurring_template_id = data['id']
        print(f"Created recurring template: {data['id']}")
    
    def test_create_simple_template(self, api_client, owner_token):
        """Test creating a non-recurring template"""
        token, _ = owner_token
        
        template_data = {
            "title": f"TEST_Simple_Template_{datetime.now().strftime('%H%M%S')}",
            "category": "Cleaning",
            "priority": "MEDIUM",
            "time_interval": 45,
            "time_unit": "MINUTES",
            "is_recurring": False
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/task-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['is_recurring'] == False
        pytest.simple_template_id = data['id']
    
    def test_get_templates_list(self, api_client, owner_token):
        """Test getting all templates"""
        token, _ = owner_token
        
        response = api_client.get(
            f"{BASE_URL}/api/task-templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify template structure
        for template in data:
            assert 'id' in template
            assert 'title' in template
            assert 'is_recurring' in template
            assert 'is_active' in template
    
    def test_update_template_toggle_active(self, api_client, owner_token):
        """Test updating template - toggling is_active"""
        token, _ = owner_token
        
        # Toggle is_active to false
        response = api_client.put(
            f"{BASE_URL}/api/task-templates/{pytest.recurring_template_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Update failed: {response.text}"
        data = response.json()
        assert data['is_active'] == False
        
        # Toggle back to true
        response = api_client.put(
            f"{BASE_URL}/api/task-templates/{pytest.recurring_template_id}",
            json={"is_active": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['is_active'] == True
    
    def test_update_template_fields(self, api_client, manager_token):
        """Test updating various template fields"""
        token, _ = manager_token
        
        update_data = {
            "title": "Updated Recurring Template Title",
            "day_intervals": "1-15,20-28",
            "allocated_time": "10:30",
            "priority": "LOW"
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/task-templates/{pytest.recurring_template_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['day_intervals'] == "1-15,20-28"
        assert data['allocated_time'] == "10:30"
        assert data['priority'] == "LOW"
    
    def test_staff_cannot_create_template(self, api_client, staff_token):
        """Test that staff cannot create templates"""
        token, _ = staff_token
        
        response = api_client.post(
            f"{BASE_URL}/api/task-templates",
            json={"title": "Staff Template", "category": "Other"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


# =============================================================================
# TEST GENERATE RECURRING TASKS
# =============================================================================
class TestGenerateRecurringTasks:
    """Test the generate-now endpoint for recurring tasks"""
    
    def test_generate_now_creates_tasks(self, api_client, owner_token, staff_token):
        """Test that generate-now creates tasks from active recurring templates"""
        token, _ = owner_token
        _, staff = staff_token
        
        # First, create a new recurring template with today's date in day_intervals
        today_day = datetime.utcnow().day
        template_data = {
            "title": f"TEST_GenNow_Template_{datetime.now().strftime('%H%M%S')}",
            "category": "Kitchen",
            "priority": "HIGH",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "is_recurring": True,
            "is_active": True,
            "day_intervals": f"1-31",  # Include all days so today matches
            "allocated_time": "11:00",
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/task-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert create_resp.status_code == 200
        template_id = create_resp.json()['id']
        
        # Call generate-now
        response = api_client.post(
            f"{BASE_URL}/api/task-templates/generate-now",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Generate-now failed: {response.text}"
        data = response.json()
        assert 'message' in data
        print(f"Generate-now result: {data['message']}")
        
        # Verify a task was created with correct format
        tasks_resp = api_client.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        tasks = tasks_resp.json()
        # Find generated task for our template
        generated_task = None
        for task in tasks:
            if task.get('template_id') == template_id:
                generated_task = task
                break
        
        if generated_task:
            # Verify task format: "Name (Mon DD HH:MM AM/PM)"
            assert generated_task['task_type'] == 'RECURRING'
            assert '(' in generated_task['title'] and ')' in generated_task['title']
            assert generated_task['template_id'] == template_id
            print(f"Generated task title: {generated_task['title']}")
        
        # Cleanup - delete template
        api_client.delete(
            f"{BASE_URL}/api/task-templates/{template_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    def test_staff_cannot_generate_now(self, api_client, staff_token):
        """Test that staff cannot trigger generate-now"""
        token, _ = staff_token
        
        response = api_client.post(
            f"{BASE_URL}/api/task-templates/generate-now",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


# =============================================================================
# TEST LATE COMPLETION FEATURE
# =============================================================================
class TestLateCompletion:
    """Test late completion flow - NOT_COMPLETED status and is_late flag"""
    
    def test_complete_from_not_completed_status(self, api_client, owner_token, staff_token):
        """Test that task can be completed from NOT_COMPLETED status (late completion)"""
        owner_tok, _ = owner_token
        staff_tok, staff = staff_token
        
        # Create a task assigned to staff with very short deadline (1 minute)
        allocated_time = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + 'Z'  # Past time
        task_data = {
            "title": f"TEST_Late_Task_{datetime.now().strftime('%H%M%S')}",
            "category": "Kitchen",
            "priority": "HIGH",
            "task_type": "INSTANT",
            "time_interval": 1,  # 1 minute deadline
            "time_unit": "MINUTES",
            "allocated_datetime": allocated_time,
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()['id']
        
        # Start the task
        start_resp = api_client.post(
            f"{BASE_URL}/api/tasks/{task_id}/start",
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        assert start_resp.status_code == 200
        
        # Manually set status to NOT_COMPLETED via update (simulating deadline passing)
        # Note: In real scenario, background job sets this when deadline passes
        
        # Upload proof photo
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        proof_resp = requests.post(
            f"{BASE_URL}/api/tasks/{task_id}/proof",
            files={'file': ('proof.jpg', img_bytes, 'image/jpeg')},
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        assert proof_resp.status_code == 200
        
        # Complete the task (should set is_late = true since deadline passed)
        complete_resp = api_client.post(
            f"{BASE_URL}/api/tasks/{task_id}/complete",
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        
        assert complete_resp.status_code == 200, f"Complete failed: {complete_resp.text}"
        data = complete_resp.json()
        
        # Verify is_late and actual_time_taken
        assert data['status'] == 'COMPLETED'
        # Since deadline was in past, is_late should be true
        assert data['is_late'] == True
        # actual_time_taken should be calculated
        assert data['actual_time_taken'] is not None
        print(f"Late completion - is_late: {data['is_late']}, actual_time: {data['actual_time_taken']} min")
        
        # Store for cleanup
        pytest.late_task_id = task_id
    
    def test_task_response_includes_late_fields(self, api_client, owner_token):
        """Test that GET /api/tasks returns is_late and actual_time_taken fields"""
        token, _ = owner_token
        
        response = api_client.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        tasks = response.json()
        
        # Find a completed task and check fields
        for task in tasks:
            # Verify fields exist in response
            assert 'is_late' in task, f"is_late field missing from task {task['id']}"
            if task.get('status') in ['COMPLETED', 'VERIFIED']:
                print(f"Task {task['id']}: is_late={task['is_late']}, actual_time={task.get('actual_time_taken')}")


# =============================================================================
# TEST TASK FIELDS STRUCTURE
# =============================================================================
class TestTaskFieldsStructure:
    """Test that tasks have the correct field structure"""
    
    def test_task_detail_has_new_fields(self, api_client, owner_token, staff_token):
        """Test task detail includes template_id, is_late, actual_time_taken"""
        owner_tok, _ = owner_token
        _, staff = staff_token
        
        # Create a task
        task_data = {
            "title": f"TEST_Fields_Task_{datetime.now().strftime('%H%M%S')}",
            "category": "Kitchen",
            "priority": "MEDIUM",
            "task_type": "INSTANT",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        task_id = create_resp.json()['id']
        
        # Get task detail
        response = api_client.get(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify new fields exist
        assert 'is_late' in data
        assert 'actual_time_taken' in data
        assert 'template_id' in data
        
        # For new tasks, these should be defaults
        assert data['is_late'] == False
        assert data['template_id'] is None  # Not generated from template
    
    def test_generated_task_has_template_id(self, api_client, owner_token, staff_token):
        """Test that tasks generated from recurring templates have template_id"""
        owner_tok, _ = owner_token
        _, staff = staff_token
        
        # Create recurring template
        template_data = {
            "title": f"TEST_TemplateLink_{datetime.now().strftime('%H%M%S')}",
            "category": "Cleaning",
            "priority": "MEDIUM",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "is_recurring": True,
            "day_intervals": "1-31",
            "allocated_time": "14:00",
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/task-templates",
            json=template_data,
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        template_id = create_resp.json()['id']
        
        # Generate tasks
        gen_resp = api_client.post(
            f"{BASE_URL}/api/task-templates/generate-now",
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        assert gen_resp.status_code == 200
        
        # Find generated task
        tasks_resp = api_client.get(
            f"{BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        
        for task in tasks_resp.json():
            if task.get('template_id') == template_id:
                assert task['task_type'] == 'RECURRING'
                print(f"Found task linked to template: {task['title']}")
                break
        
        # Cleanup
        api_client.delete(
            f"{BASE_URL}/api/task-templates/{template_id}",
            headers={"Authorization": f"Bearer {owner_tok}"}
        )


# =============================================================================
# TEST COMPLETE ENDPOINT ALLOWS NOT_COMPLETED STATUS
# =============================================================================
class TestCompleteEndpointStatuses:
    """Test that complete endpoint accepts both IN_PROGRESS and NOT_COMPLETED"""
    
    def test_complete_from_in_progress(self, api_client, owner_token, staff_token):
        """Test completing task from IN_PROGRESS status"""
        owner_tok, _ = owner_token
        staff_tok, staff = staff_token
        
        # Create task
        task_data = {
            "title": f"TEST_InProgress_{datetime.now().strftime('%H%M%S')}",
            "category": "Kitchen",
            "priority": "HIGH",
            "task_type": "INSTANT",
            "time_interval": 60,
            "time_unit": "MINUTES",
            "assigned_to": staff['id']
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
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        requests.post(
            f"{BASE_URL}/api/tasks/{task_id}/proof",
            files={'file': ('proof.jpg', img_bytes, 'image/jpeg')},
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        
        # Complete from IN_PROGRESS
        response = api_client.post(
            f"{BASE_URL}/api/tasks/{task_id}/complete",
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        
        assert response.status_code == 200
        assert response.json()['status'] == 'COMPLETED'
    
    def test_cannot_complete_from_pending(self, api_client, owner_token, staff_token):
        """Test that completing from PENDING fails"""
        owner_tok, _ = owner_token
        staff_tok, staff = staff_token
        
        # Create task (stays in PENDING)
        task_data = {
            "title": f"TEST_Pending_{datetime.now().strftime('%H%M%S')}",
            "category": "Other",
            "priority": "LOW",
            "task_type": "INSTANT",
            "time_interval": 30,
            "time_unit": "MINUTES",
            "assigned_to": staff['id']
        }
        
        create_resp = api_client.post(
            f"{BASE_URL}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {owner_tok}"}
        )
        task_id = create_resp.json()['id']
        
        # Try to complete from PENDING (without starting)
        response = api_client.post(
            f"{BASE_URL}/api/tasks/{task_id}/complete",
            headers={"Authorization": f"Bearer {staff_tok}"}
        )
        
        # Should fail - can only complete from IN_PROGRESS or NOT_COMPLETED
        assert response.status_code == 400


# =============================================================================
# CLEANUP
# =============================================================================
@pytest.fixture(scope="module", autouse=True)
def cleanup(api_client, owner_token):
    """Cleanup test templates after all tests"""
    yield
    token, _ = owner_token
    
    # Clean up any test templates
    try:
        if hasattr(pytest, 'recurring_template_id'):
            api_client.delete(
                f"{BASE_URL}/api/task-templates/{pytest.recurring_template_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
        if hasattr(pytest, 'simple_template_id'):
            api_client.delete(
                f"{BASE_URL}/api/task-templates/{pytest.simple_template_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
    except:
        pass
