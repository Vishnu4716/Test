1. Team & Use Case

Use Case: Intelligent Meeting-Room Booking Assistant

Problem: Employees spend time manually searching for suitable meeting rooms and may select rooms that are too far away, lack required equipment, or are already booked.

Solution: An agentic meeting-room assistant that understands natural-language meeting requests, searches room/employee/booking data, ranks suitable rooms, and books the selected room while preventing booking conflicts.

⸻

2. Solution Flow

Put your actual Langflow canvas screenshot here.

Under the screenshot:

Flow:

User → Agent → Meeting Room Search → Room/Employee/Booking Data → Ranked Recommendations → Book Meeting Room → Confirmation

* Agent interprets the user’s meeting requirements.
* SEARCH_ROOMS filters rooms using capacity, equipment and availability.
* Employee desk information is used for location-based ranking.
* Suitable rooms are ranked using deterministic scoring.
* BOOK_ROOM validates the selected room against existing bookings before confirming the booking.


Criterion

Logic

Capacity

Room must accommodate all attendees

Required equipment

Hard filter — requested equipment must be available

Availability

Hard filter — room must be free for the complete requested time

Distance

Rooms closer to the employee’s floor/wing receive a higher score

Capacity fit

Better-sized rooms receive a higher score

Final score

Distance score + capacity score

Ranking

Eligible rooms are sorted by final score and top rooms are recommended

Key design principle: Hard constraints are applied before scoring, so the agent does not recommend unavailable or unsuitable rooms

4. Arize Phoenix / Observability Metrics

Since Phoenix isn’t actually connected, don’t claim that these are Phoenix-generated metrics.

Use this wording:

Observability: Langflow Flow Activity was used for execution tracing and validation. The system captured 82 flow runs with trace IDs, latency, token usage, inputs/outputs and individual tool/component spans.

Observed metrics from functional testing:

Metric

Result

Flow runs captured

82

End-to-end latency observed

2.92–11.04 sec

Example full agent trace

11.04 sec

Example token usage

38,052 tokens

Tool calls traced

search_rooms, book_room

Successful booking tests

Passed

Booking conflict detection

Passed

Capacity constraint

Passed

Automatic room selection

Passed

5. Target Metrics Achieved

   Target

Result

Average booking/search time ≤ 10 sec

~6.2 sec observed average across representative tests

Reduce double bookings ≥ 90%

Conflict prevention validated through functional tests; percentage reduction not measured against a historical baseline

Appropriate-room success ≥ 90%

100% in tested eligible scenarios

