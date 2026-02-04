import requests
import sys
from datetime import datetime
import json

class ZomotoTasksAPITester:
    def __init__(self, base_url="https://task-tracker-735.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tasks = {}
        self.templates = {}
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.text else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        return success

    def test_seed_data(self):
        """Test seed data creation"""
        success, response = self.run_test(
            "Seed Data",
            "POST",
            "seed",
            200
        )
        return success

    def test_login(self, email, password, role):
        """Test login and store token"""
        success, response = self.run_test(
            f"Login ({role})",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'access_token' in response:
            self.tokens[role] = response['access_token']
            self.users[role] = response['user']
            return True
        return False

    def test_get_me(self, role):
        """Test get current user"""
        success, response = self.run_test(
            f"Get Me ({role})",
            "GET",
            "auth/me",
            200,
            token=self.tokens[role]
        )
        return success

    def test_dashboard_stats(self, role):
        """Test dashboard stats"""
        success, response = self.run_test(
            f"Dashboard Stats ({role})",
            "GET",
            "dashboard/stats",
            200,
            token=self.tokens[role]
        )
        return success

    def test_get_users(self, role):
        """Test get users (Owner/Manager only)"""
        expected_status = 200 if role in ['OWNER', 'MANAGER'] else 403
        success, response = self.run_test(
            f"Get Users ({role})",
            "GET",
            "users",
            expected_status,
            token=self.tokens[role]
        )
        return success

    def test_get_staff_users(self, role):
        """Test get staff users (Owner/Manager only)"""
        expected_status = 200 if role in ['OWNER', 'MANAGER'] else 403
        success, response = self.run_test(
            f"Get Staff Users ({role})",
            "GET",
            "users/staff",
            expected_status,
            token=self.tokens[role]
        )
        return success

    def test_create_user(self, role):
        """Test create user (Owner only)"""
        expected_status = 200 if role == 'OWNER' else 403
        test_user_data = {
            "name": f"Test User {datetime.now().strftime('%H%M%S')}",
            "email": f"test{datetime.now().strftime('%H%M%S')}@zomoto.lk",
            "phone": "0771234567",
            "password": "123456",
            "role": "STAFF"
        }
        success, response = self.run_test(
            f"Create User ({role})",
            "POST",
            "users",
            expected_status,
            data=test_user_data,
            token=self.tokens[role]
        )
        if success and role == 'OWNER':
            self.users['TEST_USER'] = response
        return success

    def test_get_task_templates(self, role):
        """Test get task templates"""
        success, response = self.run_test(
            f"Get Task Templates ({role})",
            "GET",
            "task-templates",
            200,
            token=self.tokens[role]
        )
        return success

    def test_create_task_template(self, role):
        """Test create task template (Owner/Manager only)"""
        expected_status = 200 if role in ['OWNER', 'MANAGER'] else 403
        template_data = {
            "name": f"Test Template {datetime.now().strftime('%H%M%S')}",
            "default_category": "Kitchen",
            "default_priority": "HIGH"
        }
        success, response = self.run_test(
            f"Create Task Template ({role})",
            "POST",
            "task-templates",
            expected_status,
            data=template_data,
            token=self.tokens[role]
        )
        if success and role in ['OWNER', 'MANAGER']:
            self.templates['TEST_TEMPLATE'] = response
        return success

    def test_get_tasks(self, role):
        """Test get tasks"""
        success, response = self.run_test(
            f"Get Tasks ({role})",
            "GET",
            "tasks",
            200,
            token=self.tokens[role]
        )
        return success

    def test_create_task(self, role):
        """Test create task (Owner/Manager only)"""
        expected_status = 200 if role in ['OWNER', 'MANAGER'] else 403
        
        # Get staff user for assignment
        staff_id = None
        if role in ['OWNER', 'MANAGER'] and 'STAFF' in self.users:
            staff_id = self.users['STAFF']['id']
        
        task_data = {
            "title": f"Test Task {datetime.now().strftime('%H%M%S')}",
            "description": "Test task description",
            "category": "Kitchen",
            "priority": "HIGH",
            "assigned_to": staff_id
        }
        success, response = self.run_test(
            f"Create Task ({role})",
            "POST",
            "tasks",
            expected_status,
            data=task_data,
            token=self.tokens[role]
        )
        if success and role in ['OWNER', 'MANAGER']:
            self.tasks['TEST_TASK'] = response
        return success

    def test_get_task_detail(self, role):
        """Test get task detail"""
        if 'TEST_TASK' not in self.tasks:
            print(f"⚠️  Skipping Get Task Detail ({role}) - No test task available")
            return True
            
        task_id = self.tasks['TEST_TASK']['id']
        success, response = self.run_test(
            f"Get Task Detail ({role})",
            "GET",
            f"tasks/{task_id}",
            200,
            token=self.tokens[role]
        )
        return success

    def test_update_task_status(self, role):
        """Test update task status"""
        if 'TEST_TASK' not in self.tasks:
            print(f"⚠️  Skipping Update Task Status ({role}) - No test task available")
            return True
            
        task_id = self.tasks['TEST_TASK']['id']
        
        # Staff can only update their own tasks
        if role == 'STAFF':
            # Check if task is assigned to this staff member
            if self.tasks['TEST_TASK'].get('assigned_to') != self.users['STAFF']['id']:
                print(f"⚠️  Skipping Update Task Status ({role}) - Task not assigned to this staff")
                return True
            status_data = {"status": "IN_PROGRESS"}
        else:
            status_data = {"status": "COMPLETED"}
            
        success, response = self.run_test(
            f"Update Task Status ({role})",
            "PUT",
            f"tasks/{task_id}",
            200,
            data=status_data,
            token=self.tokens[role]
        )
        return success

    def test_verify_task(self, role):
        """Test verify task (Owner/Manager only)"""
        if 'TEST_TASK' not in self.tasks:
            print(f"⚠️  Skipping Verify Task ({role}) - No test task available")
            return True
            
        expected_status = 200 if role in ['OWNER', 'MANAGER'] else 403
        task_id = self.tasks['TEST_TASK']['id']
        
        # First update task to completed status if we're owner/manager
        if role in ['OWNER', 'MANAGER']:
            self.run_test(
                f"Set Task to Completed ({role})",
                "PUT",
                f"tasks/{task_id}",
                200,
                data={"status": "COMPLETED"},
                token=self.tokens[role]
            )
        
        success, response = self.run_test(
            f"Verify Task ({role})",
            "POST",
            f"tasks/{task_id}/verify",
            expected_status,
            token=self.tokens[role]
        )
        return success

    def test_add_comment(self, role):
        """Test add comment to task"""
        if 'TEST_TASK' not in self.tasks:
            print(f"⚠️  Skipping Add Comment ({role}) - No test task available")
            return True
            
        task_id = self.tasks['TEST_TASK']['id']
        comment_data = {
            "content": f"Test comment from {role} at {datetime.now().strftime('%H:%M:%S')}"
        }
        success, response = self.run_test(
            f"Add Comment ({role})",
            "POST",
            f"tasks/{task_id}/comments",
            200,
            data=comment_data,
            token=self.tokens[role]
        )
        return success

    def test_get_comments(self, role):
        """Test get task comments"""
        if 'TEST_TASK' not in self.tasks:
            print(f"⚠️  Skipping Get Comments ({role}) - No test task available")
            return True
            
        task_id = self.tasks['TEST_TASK']['id']
        success, response = self.run_test(
            f"Get Comments ({role})",
            "GET",
            f"tasks/{task_id}/comments",
            200,
            token=self.tokens[role]
        )
        return success

    def test_get_activity_log(self, role):
        """Test get task activity log"""
        if 'TEST_TASK' not in self.tasks:
            print(f"⚠️  Skipping Get Activity Log ({role}) - No test task available")
            return True
            
        task_id = self.tasks['TEST_TASK']['id']
        success, response = self.run_test(
            f"Get Activity Log ({role})",
            "GET",
            f"tasks/{task_id}/activity",
            200,
            token=self.tokens[role]
        )
        return success

    # NEW FEATURES TESTING

    def test_get_categories(self, role):
        """Test get categories"""
        success, response = self.run_test(
            f"Get Categories ({role})",
            "GET",
            "categories",
            200,
            token=self.tokens[role]
        )
        return success

    def test_create_category(self, role):
        """Test create category (Owner/Manager only)"""
        expected_status = 200 if role in ['OWNER', 'MANAGER'] else 403
        category_data = {
            "name": f"Test Category {datetime.now().strftime('%H%M%S')}",
            "color": "#FF5733"
        }
        success, response = self.run_test(
            f"Create Category ({role})",
            "POST",
            "categories",
            expected_status,
            data=category_data,
            token=self.tokens[role]
        )
        if success and role in ['OWNER', 'MANAGER']:
            self.tasks['TEST_CATEGORY'] = response
        return success

    def test_update_category(self, role):
        """Test update category (Owner/Manager only)"""
        if 'TEST_CATEGORY' not in self.tasks:
            print(f"⚠️  Skipping Update Category ({role}) - No test category available")
            return True
            
        expected_status = 200 if role in ['OWNER', 'MANAGER'] else 403
        category_id = self.tasks['TEST_CATEGORY']['id']
        update_data = {
            "name": f"Updated Category {datetime.now().strftime('%H%M%S')}",
            "color": "#33FF57"
        }
        success, response = self.run_test(
            f"Update Category ({role})",
            "PUT",
            f"categories/{category_id}",
            expected_status,
            data=update_data,
            token=self.tokens[role]
        )
        return success

    def test_delete_category(self, role):
        """Test delete category (Owner/Manager only)"""
        if 'TEST_CATEGORY' not in self.tasks:
            print(f"⚠️  Skipping Delete Category ({role}) - No test category available")
            return True
            
        expected_status = 200 if role in ['OWNER', 'MANAGER'] else 403
        category_id = self.tasks['TEST_CATEGORY']['id']
        success, response = self.run_test(
            f"Delete Category ({role})",
            "DELETE",
            f"categories/{category_id}",
            expected_status,
            token=self.tokens[role]
        )
        return success

    def test_get_notifications(self, role):
        """Test get notifications"""
        success, response = self.run_test(
            f"Get Notifications ({role})",
            "GET",
            "notifications",
            200,
            token=self.tokens[role]
        )
        return success

    def test_get_unread_count(self, role):
        """Test get unread notifications count"""
        success, response = self.run_test(
            f"Get Unread Count ({role})",
            "GET",
            "notifications/unread-count",
            200,
            token=self.tokens[role]
        )
        return success

    def test_mark_notification_read(self, role):
        """Test mark notification as read"""
        # First get notifications to find one to mark as read
        success, notifications = self.run_test(
            f"Get Notifications for Read Test ({role})",
            "GET",
            "notifications",
            200,
            token=self.tokens[role]
        )
        
        if not success or not notifications:
            print(f"⚠️  Skipping Mark Notification Read ({role}) - No notifications available")
            return True
            
        # Find an unread notification
        unread_notification = None
        for notif in notifications:
            if not notif.get('is_read', True):
                unread_notification = notif
                break
                
        if not unread_notification:
            print(f"⚠️  Skipping Mark Notification Read ({role}) - No unread notifications")
            return True
            
        success, response = self.run_test(
            f"Mark Notification Read ({role})",
            "PUT",
            f"notifications/{unread_notification['id']}/read",
            200,
            token=self.tokens[role]
        )
        return success

    def test_mark_all_notifications_read(self, role):
        """Test mark all notifications as read"""
        success, response = self.run_test(
            f"Mark All Notifications Read ({role})",
            "PUT",
            "notifications/read-all",
            200,
            token=self.tokens[role]
        )
        return success

    def test_delete_task(self, role):
        """Test delete task (Owner/Manager only)"""
        if 'TEST_TASK' not in self.tasks:
            print(f"⚠️  Skipping Delete Task ({role}) - No test task available")
            return True
            
        expected_status = 200 if role in ['OWNER', 'MANAGER'] else 403
        task_id = self.tasks['TEST_TASK']['id']
        success, response = self.run_test(
            f"Delete Task ({role})",
            "DELETE",
            f"tasks/{task_id}",
            expected_status,
            token=self.tokens[role]
        )
        return success

    def test_get_attachments(self, role):
        """Test get task attachments"""
        if 'TEST_TASK' not in self.tasks:
            print(f"⚠️  Skipping Get Attachments ({role}) - No test task available")
            return True
            
        task_id = self.tasks['TEST_TASK']['id']
        success, response = self.run_test(
            f"Get Attachments ({role})",
            "GET",
            f"tasks/{task_id}/attachments",
            200,
            token=self.tokens[role]
        )
        return success

def main():
    print("🚀 Starting Zomoto Tasks API Testing...")
    tester = ZomotoTasksAPITester()
    
    # Test credentials
    credentials = {
        'OWNER': {'email': 'owner@zomoto.lk', 'password': '123456'},
        'MANAGER': {'email': 'manager@zomoto.lk', 'password': '123456'},
        'STAFF': {'email': 'staff@zomoto.lk', 'password': '123456'}
    }
    
    # Basic tests
    print("\n" + "="*50)
    print("BASIC API TESTS")
    print("="*50)
    
    if not tester.test_health_check():
        print("❌ Health check failed, stopping tests")
        return 1
    
    if not tester.test_seed_data():
        print("❌ Seed data failed, stopping tests")
        return 1
    
    # Authentication tests
    print("\n" + "="*50)
    print("AUTHENTICATION TESTS")
    print("="*50)
    
    for role, creds in credentials.items():
        if not tester.test_login(creds['email'], creds['password'], role):
            print(f"❌ {role} login failed, stopping tests")
            return 1
    
    # Test get me for all roles
    for role in credentials.keys():
        tester.test_get_me(role)
    
    # Dashboard tests
    print("\n" + "="*50)
    print("DASHBOARD TESTS")
    print("="*50)
    
    for role in credentials.keys():
        tester.test_dashboard_stats(role)
    
    # User management tests
    print("\n" + "="*50)
    print("USER MANAGEMENT TESTS")
    print("="*50)
    
    for role in credentials.keys():
        tester.test_get_users(role)
        tester.test_get_staff_users(role)
        tester.test_create_user(role)
    
    # Task library tests
    print("\n" + "="*50)
    print("TASK LIBRARY TESTS")
    print("="*50)
    
    for role in credentials.keys():
        tester.test_get_task_templates(role)
        tester.test_create_task_template(role)
    
    # Task management tests
    print("\n" + "="*50)
    print("TASK MANAGEMENT TESTS")
    print("="*50)
    
    for role in credentials.keys():
        tester.test_get_tasks(role)
        tester.test_create_task(role)
        tester.test_get_task_detail(role)
        tester.test_update_task_status(role)
        tester.test_verify_task(role)
    
    # Comments and activity tests
    print("\n" + "="*50)
    print("COMMENTS & ACTIVITY TESTS")
    print("="*50)
    
    for role in credentials.keys():
        tester.test_add_comment(role)
        tester.test_get_comments(role)
        tester.test_get_activity_log(role)
    
    # NEW FEATURES TESTING
    print("\n" + "="*50)
    print("CATEGORIES CRUD TESTS")
    print("="*50)
    
    for role in credentials.keys():
        tester.test_get_categories(role)
        tester.test_create_category(role)
        tester.test_update_category(role)
        tester.test_delete_category(role)
    
    print("\n" + "="*50)
    print("NOTIFICATIONS TESTS")
    print("="*50)
    
    for role in credentials.keys():
        tester.test_get_notifications(role)
        tester.test_get_unread_count(role)
        tester.test_mark_notification_read(role)
        tester.test_mark_all_notifications_read(role)
    
    print("\n" + "="*50)
    print("ATTACHMENTS TESTS")
    print("="*50)
    
    for role in credentials.keys():
        tester.test_get_attachments(role)
    
    print("\n" + "="*50)
    print("TASK DELETE TESTS")
    print("="*50)
    
    for role in credentials.keys():
        tester.test_delete_task(role)
    
    # Print final results
    print("\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    print(f"📈 Success rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 Backend API tests mostly successful!")
        return 0
    else:
        print("⚠️  Backend API tests have significant failures")
        return 1

if __name__ == "__main__":
    sys.exit(main())