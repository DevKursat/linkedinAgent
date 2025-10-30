"""Test that API limitation features fail silently without logging."""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from src.worker import trigger_commenting_async, trigger_invitation_async
from src.database import SessionLocal, engine
from src.models import ActionLog, Base
import httpx


# Setup database before tests
@pytest.fixture(autouse=True, scope="session")
def setup_database():
    """Create database tables before tests."""
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup after all tests
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_commenting_no_action_log():
    """Test that commenting returns success without logging to database."""
    db = SessionLocal()
    try:
        # Get current log count
        initial_count = db.query(ActionLog).count()
        
        # Trigger commenting
        result = await trigger_commenting_async()
        
        # Should succeed (it's expected behavior)
        assert result["success"] is True
        assert "unavailable" in result["message"].lower()
        
        # Should not add any new logs
        final_count = db.query(ActionLog).count()
        assert final_count == initial_count, "Commenting should not create action logs"
        
        # Should have informational actions
        assert len(result["actions"]) > 0
        
    finally:
        db.close()


@pytest.mark.asyncio
async def test_invitation_403_no_action_log():
    """Test that invitation 403 errors don't log to database."""
    db = SessionLocal()
    try:
        # Get current log count
        initial_count = db.query(ActionLog).count()
        
        # Mock the API client to return a 403 error
        with patch('src.worker.LinkedInApiClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock get_profile to succeed
            mock_client.get_profile.return_value = {"id": "test_urn"}
            
            # Mock send_invitation to raise 403
            mock_response = AsyncMock()
            mock_response.status_code = 403
            mock_client.send_invitation.side_effect = httpx.HTTPStatusError(
                "403 Forbidden", 
                request=AsyncMock(),
                response=mock_response
            )
            
            # Trigger invitation
            result = await trigger_invitation_async()
            
            # Should fail (expected)
            assert result["success"] is False
            assert "special permissions" in result["message"]
            assert result.get("skip_log") is True
            
            # Should not add any new logs for 403 errors
            final_count = db.query(ActionLog).count()
            assert final_count == initial_count, "403 invitation errors should not create action logs"
        
    finally:
        db.close()


@pytest.mark.asyncio
async def test_invitation_success_creates_log():
    """Test that successful invitations still create logs."""
    db = SessionLocal()
    try:
        # Get current log count
        initial_count = db.query(ActionLog).count()
        
        # Mock the API client to succeed
        with patch('src.worker.LinkedInApiClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock get_profile to succeed
            mock_client.get_profile.return_value = {"id": "test_urn"}
            
            # Mock send_invitation to succeed
            mock_client.send_invitation.return_value = {"status": "success"}
            
            # Trigger invitation
            result = await trigger_invitation_async()
            
            # Should succeed
            assert result["success"] is True
            
            # Should add a log for successful invitation
            final_count = db.query(ActionLog).count()
            assert final_count == initial_count + 1, "Successful invitations should create action logs"
        
    finally:
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
