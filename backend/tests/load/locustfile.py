"""
Load Testing with Locust
=========================
Run: locust -f tests/load/locustfile.py --host=http://localhost:8000
Open: http://localhost:8089

Recommended test scenarios:
- Light load: 50 users, spawn rate 5
- Medium load: 200 users, spawn rate 20
- Heavy load: 500 users, spawn rate 50
"""

from locust import HttpUser, task, between, tag
import random


class IncidentManagementUser(HttpUser):
    """Simulates a typical user interacting with the incident management system."""
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        """Login and get access token."""
        users = [
            {"email": "admin@test.com", "password": "Admin@123"},
            {"email": "jay.valaki.17@gmail.com", "password": "Admin@123"},
            {"email": "eng2@test.com", "password": "Admin@123"},
        ]
        creds = random.choice(users)
        response = self.client.post("/api/v1/auth/login", json=creds)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        else:
            self.token = None

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    # ─── High Frequency (read operations) ────────────────────────────────────

    @task(5)
    @tag("read")
    def list_incidents(self):
        """Most common action: viewing incident list."""
        self.client.get(
            "/api/v1/incidents/",
            headers=self.auth_headers,
            params={"page": 1, "page_size": 20},
        )

    @task(4)
    @tag("read")
    def get_dashboard(self):
        """Dashboard is loaded frequently."""
        self.client.get("/api/v1/analytics/dashboard", headers=self.auth_headers)

    @task(3)
    @tag("read")
    def get_incident_detail(self):
        """View a specific incident."""
        # First get list to pick a random incident
        response = self.client.get(
            "/api/v1/incidents/",
            headers=self.auth_headers,
            params={"page": 1, "page_size": 5},
            name="/api/v1/incidents/ [list for detail]",
        )
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                incident_id = random.choice(items)["id"]
                self.client.get(
                    f"/api/v1/incidents/{incident_id}",
                    headers=self.auth_headers,
                    name="/api/v1/incidents/[id]",
                )

    @task(2)
    @tag("read")
    def search_incidents(self):
        """Search functionality."""
        queries = ["server", "login", "timeout", "error", "database"]
        self.client.get(
            "/api/v1/incidents/",
            headers=self.auth_headers,
            params={"search": random.choice(queries), "page": 1, "page_size": 20},
            name="/api/v1/incidents/ [search]",
        )

    @task(2)
    @tag("read")
    def get_notifications(self):
        """Check notifications."""
        self.client.get("/api/v1/notifications/", headers=self.auth_headers)

    @task(1)
    @tag("read")
    def get_users(self):
        """List users (for assignment dropdown)."""
        self.client.get("/api/v1/auth/users", headers=self.auth_headers)

    # ─── Medium Frequency (write operations) ─────────────────────────────────

    @task(2)
    @tag("write")
    def create_incident(self):
        """Create a new incident."""
        priorities = ["low", "medium", "high", "critical"]
        self.client.post(
            "/api/v1/incidents/",
            headers=self.auth_headers,
            json={
                "title": f"Load test incident - {random.randint(1000, 9999)}",
                "description": "This is an automated load test incident to measure system performance under concurrent user load. " * 3,
                "priority": random.choice(priorities),
            },
        )

    @task(1)
    @tag("write")
    def add_comment(self):
        """Add a comment to an incident."""
        response = self.client.get(
            "/api/v1/incidents/",
            headers=self.auth_headers,
            params={"page": 1, "page_size": 5},
            name="/api/v1/incidents/ [list for comment]",
        )
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                incident_id = random.choice(items)["id"]
                self.client.post(
                    f"/api/v1/incidents/{incident_id}/comments",
                    headers=self.auth_headers,
                    json={"content": f"Load test comment - checking system stability #{random.randint(1, 999)}"},
                    name="/api/v1/incidents/[id]/comments",
                )

    @task(1)
    @tag("write")
    def update_incident(self):
        """Update incident priority."""
        response = self.client.get(
            "/api/v1/incidents/",
            headers=self.auth_headers,
            params={"page": 1, "page_size": 5, "status": "open"},
            name="/api/v1/incidents/ [list for update]",
        )
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                incident_id = random.choice(items)["id"]
                self.client.patch(
                    f"/api/v1/incidents/{incident_id}",
                    headers=self.auth_headers,
                    json={"priority": random.choice(["low", "medium", "high"])},
                    name="/api/v1/incidents/[id] [update]",
                )

    # ─── Low Frequency ────────────────────────────────────────────────────────

    @task(1)
    @tag("read")
    def health_check(self):
        """Basic health check."""
        self.client.get("/health")

    @task(1)
    @tag("read")
    def get_profile(self):
        """Get own profile."""
        self.client.get("/api/v1/auth/me", headers=self.auth_headers)


class CustomerUser(HttpUser):
    """Simulates a customer with limited access."""
    wait_time = between(2, 5)
    weight = 1  # Fewer customers than staff
    token = None

    def on_start(self):
        """Login as customer."""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "ca@ca.com",
            "password": "Admin@123",
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def list_my_incidents(self):
        """Customer views their own incidents."""
        self.client.get("/api/v1/incidents/", headers=self.auth_headers)

    @task(2)
    def view_dashboard(self):
        """Customer views their dashboard."""
        self.client.get("/api/v1/analytics/dashboard", headers=self.auth_headers)

    @task(1)
    def create_ticket(self):
        """Customer creates a support ticket."""
        self.client.post(
            "/api/v1/incidents/",
            headers=self.auth_headers,
            json={
                "title": f"Customer issue - {random.randint(1000, 9999)}",
                "description": "I am experiencing an issue with the system and need help resolving it. Please look into this matter.",
                "priority": "medium",
            },
        )
