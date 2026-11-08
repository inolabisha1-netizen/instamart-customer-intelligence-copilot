
"""Verify that Part B customer segments are used correctly in Part C routing."""

import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"


class TestPartBCIntegration(unittest.TestCase):

    def test_customer_segments_and_ticket_routing(self):
        segments_path = OUTPUTS / "customer_segments.csv"
        tickets_path = OUTPUTS / "triage_results.csv"

        self.assertTrue(
            segments_path.is_file(),
            "Missing customer_segments.csv. Run the project pipeline first."
        )
        self.assertTrue(
            tickets_path.is_file(),
            "Missing triage_results.csv. Run the Part C triage pipeline first."
        )

        segments = pd.read_csv(segments_path)
        tickets = pd.read_csv(tickets_path, keep_default_na=False)

        # Validate required columns and customer identifiers.
        self.assertTrue(
            {"customer_id", "segment_name", "is_premium"}.issubset(segments.columns)
        )
        self.assertTrue(
            {
                "ticket_id", "customer_id", "status", "category",
                "segment_name", "priority", "route", "tokens_used"
            }.issubset(tickets.columns)
        )

        self.assertEqual(len(tickets), 164)
        self.assertTrue(tickets["ticket_id"].is_unique)
        self.assertTrue(segments["customer_id"].is_unique)

        # Identify Premium customers from the actual Part B output.
        premium = set(
            segments.loc[
                segments["is_premium"].astype(str).str.lower() == "true",
                "customer_id"
            ]
        )

        segment_names = segments.set_index("customer_id")["segment_name"].to_dict()

        human_statuses = {
            "skipped_empty",
            "flagged_long",
            "flagged_invalid_output",
            "budget_exhausted"
        }

        valid_statuses = {"classified_json", "classified_keyword"}

        for _, ticket in tickets.iterrows():
            customer_id = ticket["customer_id"]
            status = ticket["status"]
            category = ticket["category"]
            ticket_id = ticket["ticket_id"]

            # Verify that the segment label came from Part B.
            expected_segment = segment_names.get(customer_id, "")
            self.assertEqual(
                ticket["segment_name"],
                expected_segment,
                f"Segment mismatch: {ticket_id}"
            )

            # Independently calculate expected route and priority.
            if status in human_statuses:
                expected_route = "human_review"
                expected_priority = "NORMAL"

            elif status in valid_statuses and category == "fraud":
                expected_route = "security_team"
                expected_priority = "HIGH"

            elif status in valid_statuses and customer_id in premium:
                expected_route = "premium_desk"
                expected_priority = "HIGH"

            elif status in valid_statuses:
                expected_route = "support_queue"
                expected_priority = "NORMAL"

            else:
                self.fail(f"Unexpected status: {ticket_id} - {status}")

            self.assertEqual(
                ticket["route"],
                expected_route,
                f"Incorrect route: {ticket_id}"
            )

            self.assertEqual(
                ticket["priority"],
                expected_priority,
                f"Incorrect priority: {ticket_id}"
            )

        print("\nPART B -> PART C INTEGRATION PASSED")
        print("Tickets verified:", len(tickets))
        print("Premium customers in Part B:", len(premium))
        print(
            "Premium desk tickets:",
            (tickets["route"] == "premium_desk").sum()
        )
        print(
            "Fraud tickets routed to security:",
            (tickets["route"] == "security_team").sum()
        )
        print(
            "Human review tickets:",
            (tickets["route"] == "human_review").sum()
        )


if __name__ == "__main__":
    unittest.main()
