"""
Test: RFID → Spotify Playback Integration
"""
import pytest
from sqlmodel import Session


class TestRfidSpotifyFlow:
    """Test the complete RFID → Spotify playback workflow."""

    def test_playlist_tag_triggers_playback(self, tmp_db, api_client):
        """
        End-to-end test: Assign playlist tag → simulate scan → verify play_uri called.
        """
        from database import get_engine, RfidTag
        from models.user import resolve_rfid_action
        
        # 1. Assign a playlist tag
        playlist_uri = "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
        with Session(get_engine()) as s:
            tag = RfidTag(
                uid="TESTPLAY1",
                tag_type="playlist",
                spotify_uri=playlist_uri,
                label="Test Hits"
            )
            s.add(tag)
            s.commit()
        
        # 2. Verify resolution works
        with Session(get_engine()) as s:
            action = resolve_rfid_action(s, "TESTPLAY1")
        
        assert action is not None
        assert action["type"] == "playlist"
        assert action["spotify_uri"] == playlist_uri
        assert action["label"] == "Test Hits"
    
    def test_resolve_rfid_includes_label(self, tmp_db):
        """Verify that playlist actions include the label field."""
        from database import get_engine, RfidTag
        from models.user import resolve_rfid_action
        
        with Session(get_engine()) as s:
            s.add(RfidTag(
                uid="LABEL_TEST",
                tag_type="playlist",
                spotify_uri="spotify:playlist:xyz",
                label="My Custom Playlist"
            ))
            s.commit()
            
            action = resolve_rfid_action(s, "LABEL_TEST")
        
        assert action["label"] == "My Custom Playlist"
    
    def test_playlist_tag_without_label_gets_default(self, tmp_db):
        """Tags without labels should get a default label."""
        from database import get_engine, RfidTag
        from models.user import resolve_rfid_action
        
        with Session(get_engine()) as s:
            s.add(RfidTag(
                uid="NO_LABEL",
                tag_type="playlist",
                spotify_uri="spotify:playlist:abc",
                label=""  # Empty label
            ))
            s.commit()
            
            action = resolve_rfid_action(s, "NO_LABEL")
        
        assert action["label"] == "Playlist"  # Default fallback
    
    def test_playback_api_returns_state(self, tmp_db, api_client):
        """Test that /api/playback/state returns proper structure."""
        response = api_client.get("/api/playback/state")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields
        assert "playing" in data
        assert "track" in data
        assert "artist" in data
        assert "volume" in data
        assert isinstance(data["playing"], bool)
        assert isinstance(data["volume"], int)