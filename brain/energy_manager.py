"""
Energy Manager — Resource-aware agent behavior.

Tracks Claude API costs per run/day. Agent adjusts behavior
based on remaining energy:
  🟢 >70% — full power (experiments, long posts, analysis)
  🟡 30-70% — balanced (selective engagement)
  🔴 <30% — survival mode (short replies, high-value only)
"""
import json
import os
from config import ANTHROPIC_API_KEY, get_data_path
import datetime

ENERGY_LOG_PATH = get_data_path("energy_log.json")

# Claude Sonnet 4 pricing (per token)
CLAUDE_PRICING = {
    "input": 3.0 / 1_000_000,    # $3 per 1M input tokens
    "output": 15.0 / 1_000_000,  # $15 per 1M output tokens
}


class EnergyManager:
    def __init__(self, daily_budget_usd: float = 0.50):
        self.daily_budget = daily_budget_usd
        self.spent_today = 0.0
        self.calls_today = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._reset_date = datetime.date.today()
        self._load_state()

    def _state_path(self) -> str:
        return ENERGY_LOG_PATH

    def _load_state(self):
        """Load today's state from disk."""
        if not os.path.exists(self._state_path()):
            return
        try:
            with open(self._state_path(), "r") as f:
                data = json.load(f)
            saved_date = data.get("date", "")
            if saved_date == str(datetime.date.today()):
                self.spent_today = data.get("spent_today", 0.0)
                self.calls_today = data.get("calls_today", 0)
                self.total_input_tokens = data.get("total_input_tokens", 0)
                self.total_output_tokens = data.get("total_output_tokens", 0)
        except (json.JSONDecodeError, IOError):
            pass

    def _save_state(self):
        """Persist today's state to disk."""
        data = {
            "date": str(datetime.date.today()),
            "spent_today": round(self.spent_today, 6),
            "calls_today": self.calls_today,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "energy_left": round(self.energy_left(), 6),
            "energy_ratio": round(self.energy_ratio(), 4),
        }
        os.makedirs(os.path.dirname(self._state_path()), exist_ok=True)
        with open(self._state_path(), "w") as f:
            json.dump(data, f, indent=2)

    def _check_daily_reset(self):
        """Reset at midnight."""
        today = datetime.date.today()
        if today > self._reset_date:
            self.spent_today = 0.0
            self.calls_today = 0
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self._reset_date = today

    def add_usage(self, input_tokens: int, output_tokens: int):
        """Log a Claude API call's token usage."""
        self._check_daily_reset()
        cost = (
            input_tokens * CLAUDE_PRICING["input"] +
            output_tokens * CLAUDE_PRICING["output"]
        )
        self.spent_today += cost
        self.calls_today += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self._save_state()
        return cost

    def energy_left(self) -> float:
        """Remaining budget in USD."""
        self._check_daily_reset()
        return max(self.daily_budget - self.spent_today, 0)

    def energy_ratio(self) -> float:
        """Energy as 0.0 to 1.0 ratio."""
        return self.energy_left() / self.daily_budget if self.daily_budget > 0 else 0

    def energy_level(self) -> str:
        """Human-readable energy level."""
        ratio = self.energy_ratio()
        if ratio > 0.7:
            return "high"
        elif ratio > 0.3:
            return "medium"
        else:
            return "low"

    def energy_emoji(self) -> str:
        level = self.energy_level()
        return {"high": "🟢", "medium": "🟡", "low": "🔴"}[level]

    def should_skip_heavy(self) -> bool:
        """Returns True if energy is too low for heavy operations."""
        return self.energy_ratio() < 0.3

    def should_conserve(self) -> bool:
        """Returns True if agent should be selective."""
        return self.energy_ratio() < 0.7

    def get_prompt_injection(self) -> str:
        """Generate energy-aware prompt section."""
        ratio = self.energy_ratio()
        level = self.energy_level()
        emoji = self.energy_emoji()

        base = f"""

## ENERGY STATUS: {emoji} {level.upper()} ({ratio:.0%} remaining)
Cost so far: ${self.spent_today:.4f} / ${self.daily_budget:.2f} budget
API calls today: {self.calls_today}
"""
        if level == "high":
            base += """
You have plenty of energy. You can:
- Write detailed, thoughtful original posts
- Analyze multiple casts in depth
- Run experiments and take creative risks
- Engage broadly with the feed
"""
        elif level == "medium":
            base += """
Energy is moderate. Be selective:
- Focus on high-quality engagement only
- Keep replies concise but meaningful
- Skip low-value threads
- Prioritize actions that advance your goals
"""
        else:
            base += """
⚠️ ENERGY IS LOW. Survival mode:
- Only respond to direct mentions/replies
- Keep all responses SHORT (1-2 sentences max)
- Skip the trending feed entirely
- No experiments, no long analysis
- Focus ONLY on high-reward actions
"""
        return base

    def status_line(self) -> str:
        """One-line status for dashboard."""
        ratio = self.energy_ratio()
        emoji = self.energy_emoji()
        bar = "█" * int(ratio * 20) + "░" * (20 - int(ratio * 20))
        return f"{emoji} Energy: {bar} {ratio:.0%} (${self.spent_today:.4f}/${self.daily_budget:.2f})"


# Global singleton
_instance = None

def get_energy_manager() -> EnergyManager:
    global _instance
    if _instance is None:
        _instance = EnergyManager()
    return _instance
