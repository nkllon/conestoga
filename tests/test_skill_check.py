import unittest

# Adjust path if needed or rely on PYTHONPATH
from conestoga.game.events import EventResolution, Outcome
from conestoga.game.state import GameState


class TestSkillCheck(unittest.TestCase):
    def test_random_skill_check_logic(self):
        """Test that random checks use pure d20 and ignore skills"""
        game_state = GameState()
        member = game_state.party[0]
        # Set a fake skill to try and cheat the check
        # If the bug is present, this skill_None=100 would make the check pass easily
        object.__setattr__(member, "skill_None", 100)

        # Outcome that uses random check
        outcome = Outcome(
            text="Outcome",
            success_required={"random": True, "dc": 50},  # Impossible with d20 (max 20)
            success_text="Success",
            failure_text="Failure",
        )

        resolution = EventResolution(choice_id="test", outcome=outcome)

        # Apply resolution
        # Should fail because max roll is 20 < 50
        # If bug is present, 20 + 100 >= 50 -> Success
        result = resolution.apply(game_state)

        self.assertEqual(
            result, "Failure", "Random check should fail against high DC regardless of fake skills"
        )

    def test_normal_skill_check_logic(self):
        """Test that normal skill checks still work"""
        game_state = GameState()
        member = game_state.party[0]
        # Give a real skill
        member.skill_hunter = 10

        outcome = Outcome(
            text="Outcome",
            success_required={
                "skill": "hunter",
                "dc": 10,
            },  # 10 + roll(1-20) >= 10 -> Always success
            success_text="Success",
            failure_text="Failure",
        )

        resolution = EventResolution(choice_id="test", outcome=outcome)
        result = resolution.apply(game_state)

        self.assertEqual(result, "Success", "Normal skill check should succeed with high skill")


if __name__ == "__main__":
    unittest.main()
