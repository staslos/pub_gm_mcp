from __future__ import annotations
from pathlib import Path
from pub_gm_mcp.models.campaign import Campaign
from pub_gm_mcp.models.campaign_session import CampaignSession


class CampaignStore:
    def __init__(self, campaigns_dir: Path, sessions_dir: Path) -> None:
        self.campaigns_dir = campaigns_dir
        self.sessions_dir = sessions_dir
        self.campaigns_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    # -- Campaigns --

    def load_campaign(self, campaign_id: str) -> Campaign:
        path = self._campaign_path(campaign_id)
        if not path.exists():
            raise FileNotFoundError(f"Campaign '{campaign_id}' not found")
        return Campaign.model_validate_json(path.read_text())

    def save_campaign(self, campaign: Campaign) -> None:
        self._campaign_path(campaign.id).write_text(campaign.model_dump_json(indent=2))

    def list_campaigns(self) -> list[str]:
        return [p.stem for p in self.campaigns_dir.glob("*.json")]

    def delete_campaign(self, campaign_id: str) -> None:
        path = self._campaign_path(campaign_id)
        if not path.exists():
            raise FileNotFoundError(f"Campaign '{campaign_id}' not found")
        path.unlink()

    # -- Campaign sessions --

    def load_session(self, session_id: str) -> CampaignSession:
        path = self._session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Campaign session '{session_id}' not found")
        return CampaignSession.model_validate_json(path.read_text())

    def save_session(self, session: CampaignSession) -> None:
        session.touch()
        self._session_path(session.id).write_text(session.model_dump_json(indent=2))

    def list_sessions(self) -> list[str]:
        return [p.stem for p in self.sessions_dir.glob("*.json")]

    def _campaign_path(self, campaign_id: str) -> Path:
        return self.campaigns_dir / f"{campaign_id}.json"

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"
