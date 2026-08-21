import pytest
from httpx import AsyncClient


@pytest.fixture
async def sample_incident(authenticated_client: AsyncClient):
    """Create and return a sample incident."""
    response = await authenticated_client.post("/api/v1/incidents/", json={
        "title": "Test Incident - Server Down",
        "description": "The production server is not responding to health checks.",
        "priority": "high",
    })
    assert response.status_code == 201
    return response.json()


@pytest.mark.incidents
class TestCreateIncident:
    """Test incident creation."""

    async def test_create_incident_success(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post("/api/v1/incidents/", json={
            "title": "Database Connection Timeout",
            "description": "The database is timing out on all connections after the latest deploy.",
            "priority": "critical",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Database Connection Timeout"
        assert data["priority"] == "critical"
        assert data["status"] == "open"
        assert data["escalation_level"] == 0
        assert data["sla_deadline"] is not None

    async def test_create_incident_default_priority(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post("/api/v1/incidents/", json={
            "title": "Minor UI Bug",
            "description": "Button color is wrong on the settings page.",
        })
        assert response.status_code == 201
        assert response.json()["priority"] == "medium"

    async def test_create_incident_unauthenticated(self, client: AsyncClient):
        response = await client.post("/api/v1/incidents/", json={
            "title": "Should Fail",
            "description": "No auth token provided for this request.",
        })
        assert response.status_code == 403

    async def test_create_incident_validation_error(self, authenticated_client: AsyncClient):
        # Title too short
        response = await authenticated_client.post("/api/v1/incidents/", json={
            "title": "AB",
            "description": "Valid description that is long enough.",
        })
        assert response.status_code == 422

        # Description too short
        response = await authenticated_client.post("/api/v1/incidents/", json={
            "title": "Valid Title",
            "description": "Short",
        })
        assert response.status_code == 422


@pytest.mark.incidents
class TestListIncidents:
    """Test incident listing and filtering."""

    async def test_list_incidents(self, authenticated_client: AsyncClient, sample_incident):
        response = await authenticated_client.get("/api/v1/incidents/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "total_pages" in data
        assert data["total"] >= 1

    async def test_list_incidents_pagination(self, authenticated_client: AsyncClient):
        # Create multiple incidents
        for i in range(5):
            await authenticated_client.post("/api/v1/incidents/", json={
                "title": f"Incident #{i+1}",
                "description": f"Description for incident number {i+1} here.",
                "priority": "low",
            })

        response = await authenticated_client.get("/api/v1/incidents/", params={"page_size": 2, "page": 1})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5
        assert data["total_pages"] >= 3

    async def test_list_incidents_search(self, authenticated_client: AsyncClient, sample_incident):
        response = await authenticated_client.get("/api/v1/incidents/", params={"search": "Server Down"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert "Server Down" in data["items"][0]["title"]

    async def test_list_incidents_filter_priority(self, authenticated_client: AsyncClient):
        await authenticated_client.post("/api/v1/incidents/", json={
            "title": "Critical System Failure",
            "description": "Everything is on fire. This is a critical incident.",
            "priority": "critical",
        })
        response = await authenticated_client.get("/api/v1/incidents/", params={"priority": "critical"})
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["priority"] == "critical"


@pytest.mark.incidents
class TestGetIncident:
    """Test getting a single incident."""

    async def test_get_incident_success(self, authenticated_client: AsyncClient, sample_incident):
        response = await authenticated_client.get(f"/api/v1/incidents/{sample_incident['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == sample_incident["id"]
        assert response.json()["title"] == sample_incident["title"]

    async def test_get_incident_not_found(self, authenticated_client: AsyncClient):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await authenticated_client.get(f"/api/v1/incidents/{fake_id}")
        assert response.status_code == 404


@pytest.mark.incidents
class TestUpdateIncident:
    """Test incident updates."""

    async def test_update_status(self, authenticated_client: AsyncClient, sample_incident):
        response = await authenticated_client.patch(
            f"/api/v1/incidents/{sample_incident['id']}",
            json={"status": "in_progress"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    async def test_resolve_incident(self, authenticated_client: AsyncClient, sample_incident):
        response = await authenticated_client.patch(
            f"/api/v1/incidents/{sample_incident['id']}",
            json={"status": "resolved"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "resolved"
        assert response.json()["resolved_at"] is not None

    async def test_update_priority(self, authenticated_client: AsyncClient, sample_incident):
        response = await authenticated_client.patch(
            f"/api/v1/incidents/{sample_incident['id']}",
            json={"priority": "critical"},
        )
        assert response.status_code == 200
        assert response.json()["priority"] == "critical"


@pytest.mark.incidents
class TestIncidentComments:
    """Test incident comments."""

    async def test_add_comment(self, authenticated_client: AsyncClient, sample_incident):
        response = await authenticated_client.post(
            f"/api/v1/incidents/{sample_incident['id']}/comments",
            json={"content": "Working on this issue now."},
        )
        assert response.status_code == 201
        assert response.json()["content"] == "Working on this issue now."
        assert response.json()["incident_id"] == sample_incident["id"]

    async def test_get_comments(self, authenticated_client: AsyncClient, sample_incident):
        # Add a comment first
        await authenticated_client.post(
            f"/api/v1/incidents/{sample_incident['id']}/comments",
            json={"content": "First comment"},
        )
        await authenticated_client.post(
            f"/api/v1/incidents/{sample_incident['id']}/comments",
            json={"content": "Second comment"},
        )

        response = await authenticated_client.get(f"/api/v1/incidents/{sample_incident['id']}/comments")
        assert response.status_code == 200
        assert len(response.json()) == 2


@pytest.mark.incidents
class TestIncidentHistory:
    """Test incident change history."""

    async def test_history_recorded_on_update(self, authenticated_client: AsyncClient, sample_incident):
        # Make an update
        await authenticated_client.patch(
            f"/api/v1/incidents/{sample_incident['id']}",
            json={"status": "in_progress"},
        )

        # Check history
        response = await authenticated_client.get(f"/api/v1/incidents/{sample_incident['id']}/history")
        assert response.status_code == 200
        history = response.json()
        assert len(history) >= 1
        assert history[0]["field_changed"] == "status"
        assert history[0]["new_value"] == "IncidentStatus.IN_PROGRESS"


@pytest.mark.incidents
class TestDeleteIncident:
    """Test incident deletion."""

    async def test_delete_own_incident(self, authenticated_client: AsyncClient, sample_incident):
        response = await authenticated_client.delete(f"/api/v1/incidents/{sample_incident['id']}")
        assert response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(f"/api/v1/incidents/{sample_incident['id']}")
        assert get_response.status_code == 404
