# Test
Test purpose

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, DataFrameInput, Output
from lfx.schema.message import Message

import pandas as pd
import json
import re


class MeetingRoomSearch(Component):
    display_name = "Meeting Room Search"
    description = (
        "Finds and ranks suitable meeting rooms using room, "
        "employee desk, and booking data."
    )
    icon = "Search"
    name = "MeetingRoomSearch"

    inputs = [
        MessageTextInput(
            name="meeting_request",
            display_name="Meeting Request",
            info=(
                "Meeting requirements in JSON format. "
                "Can include attendees, date, start_time, end_time, "
                "required_equipment, employee_id, floor, and wing."
            ),
            tool_mode=True,
        ),

        DataFrameInput(
            name="rooms_data",
            display_name="Rooms Data",
            info="Room inventory from Rooms.csv.",
        ),

        DataFrameInput(
            name="employees_data",
            display_name="Employee Desks",
            info="Employee desk-location data from Employees_Desks.csv.",
        ),

        DataFrameInput(
            name="bookings_data",
            display_name="Room Bookings",
            info="Existing room bookings from Room_Bookings.csv.",
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name="Room Recommendations",
            method="search_rooms",
        )
    ]

    # ---------------------------------------------------------
    # Helper: normalize time
    # ---------------------------------------------------------
    def normalize_time(self, value):
        if value is None:
            return ""

        text = str(value).strip()

        # Handle values such as 10:30
        if ":" in text:
            parts = text.split(":")
            hour = parts[0].zfill(2)
            minute = parts[1][:2].zfill(2)
            return f"{hour}:{minute}"

        # Handle values such as 1030
        digits = re.sub(r"[^0-9]", "", text)

        if len(digits) == 4:
            return f"{digits[:2]}:{digits[2:]}"

        if len(digits) == 3:
            return f"0{digits[0]}:{digits[1:]}"

        return text

    # ---------------------------------------------------------
    # Helper: normalize date
    # ---------------------------------------------------------
    def normalize_date(self, value):
        try:
            return pd.to_datetime(value).strftime("%Y-%m-%d")
        except Exception:
            return str(value).strip()

    # ---------------------------------------------------------
    # Helper: equipment aliases
    # ---------------------------------------------------------
    def equipment_column(self, equipment):
        text = str(equipment).lower().strip()

        text = text.replace("-", " ")
        text = text.replace("_", " ")

        if (
            "video" in text
            or text in ["vc", "video conference", "video conferencing"]
        ):
            return "video_conf_equipped"

        if "projector" in text:
            return "projector"

        if "whiteboard" in text or "white board" in text:
            return "whiteboard"

        return None

    # ---------------------------------------------------------
    # Main search
    # ---------------------------------------------------------
    def search_rooms(self) -> Message:

        try:
            rooms_df = self.rooms_data
            employees_df = self.employees_data
            bookings_df = self.bookings_data

            # -------------------------------------------------
            # Validate data
            # -------------------------------------------------
            if rooms_df is None or rooms_df.empty:
                return Message(
                    text=json.dumps({
                        "error": "Rooms data is empty."
                    }, indent=2)
                )

            if bookings_df is None or bookings_df.empty:
                return Message(
                    text=json.dumps({
                        "error": "Room bookings data is empty."
                    }, indent=2)
                )

            # -------------------------------------------------
            # Parse request
            # -------------------------------------------------
            request_text = str(self.meeting_request).strip()

            try:
                request = json.loads(request_text)
            except Exception:
                return Message(
                    text=json.dumps({
                        "error": (
                            "Meeting request must be valid JSON."
                        ),
                        "received": request_text
                    }, indent=2)
                )

            attendees = int(request.get("attendees", 0))

            meeting_date = self.normalize_date(
                request.get("date", "")
            )

            start_time = self.normalize_time(
                request.get("start_time", "")
            )

            end_time = self.normalize_time(
                request.get("end_time", "")
            )

            required_equipment = request.get(
                "required_equipment", []
            )

            if isinstance(required_equipment, str):
                required_equipment = [required_equipment]

            employee_id = str(
                request.get("employee_id", "")
            ).strip()

            preferred_floor = str(
                request.get("floor", "")
            ).strip()

            preferred_wing = str(
                request.get("wing", "")
            ).strip()

            # -------------------------------------------------
            # Basic validation
            # -------------------------------------------------
            if attendees <= 0:
                return Message(
                    text=json.dumps({
                        "error": "Attendee count must be greater than 0."
                    }, indent=2)
                )

            if not meeting_date or not start_time or not end_time:
                return Message(
                    text=json.dumps({
                        "error": (
                            "Date, start_time and end_time "
                            "are required."
                        )
                    }, indent=2)
                )

            # -------------------------------------------------
            # Determine employee location
            # -------------------------------------------------
            employee_floor = preferred_floor
            employee_wing = preferred_wing

            if employee_id and employees_df is not None:

                employee_rows = employees_df[
                    employees_df["employee_id"]
                    .astype(str)
                    .str.strip()
                    == employee_id
                ]

                if not employee_rows.empty:

                    employee = employee_rows.iloc[0]

                    employee_floor = str(
                        employee["floor"]
                    ).strip()

                    employee_wing = str(
                        employee["wing"]
                    ).strip()

            # -------------------------------------------------
            # Filter rooms by capacity + equipment
            # -------------------------------------------------
            candidate_rooms = []

            for _, room in rooms_df.iterrows():

                try:
                    capacity = int(room["capacity_seats"])
                except Exception:
                    continue

                # Capacity check
                if capacity < attendees:
                    continue

                equipment_ok = True

                # Equipment checks
                for required in required_equipment:

                    column = self.equipment_column(required)

                    if column is None:
                        equipment_ok = False
                        break

                    value = str(
                        room.get(column, "")
                    ).strip().upper()

                    if value not in ["Y", "YES", "TRUE", "1"]:
                        equipment_ok = False
                        break

                if not equipment_ok:
                    continue

                candidate_rooms.append(room)

            # -------------------------------------------------
            # Availability check
            # -------------------------------------------------
            available_rooms = []

            for room in candidate_rooms:

                room_id = str(
                    room["room_id"]
                ).strip()

                room_bookings = bookings_df[
                    bookings_df["room_id"]
                    .astype(str)
                    .str.strip()
                    == room_id
                ]

                available = True

                for _, booking in room_bookings.iterrows():

                    booking_date = self.normalize_date(
                        booking["date"]
                    )

                    if booking_date != meeting_date:
                        continue

                    status = str(
                        booking["status"]
                    ).strip().lower()

                    if status not in [
                        "confirmed",
                        "tentative"
                    ]:
                        continue

                    booking_start = self.normalize_time(
                        booking["start_time"]
                    )

                    booking_end = self.normalize_time(
                        booking["end_time"]
                    )

                    # Time overlap:
                    # requested_start < existing_end
                    # AND requested_end > existing_start
                    if (
                        start_time < booking_end
                        and end_time > booking_start
                    ):
                        available = False
                        break

                if available:
                    available_rooms.append(room)

            # -------------------------------------------------
            # Rank rooms
            # -------------------------------------------------
            ranked_rooms = []

            for room in available_rooms:

                room_floor = str(
                    room["floor"]
                ).strip()

                room_wing = str(
                    room["wing"]
                ).strip()

                capacity = int(
                    room["capacity_seats"]
                )

                # ---------------------------------------------
                # Distance score
                # ---------------------------------------------
                distance_score = 0
                floor_difference = 0

                if employee_floor:

                    try:
                        floor_difference = abs(
                            int(room_floor)
                            - int(employee_floor)
                        )
                    except Exception:
                        floor_difference = 99

                    if (
                        room_floor == employee_floor
                        and room_wing.lower()
                        == employee_wing.lower()
                    ):
                        distance_score = 100

                    elif room_floor == employee_floor:
                        distance_score = 70

                    else:
                        distance_score = max(
                            20,
                            50 - (floor_difference * 10)
                        )

                else:
                    distance_score = 50

                # ---------------------------------------------
                # Capacity efficiency
                # ---------------------------------------------
                extra_seats = capacity - attendees

                if extra_seats == 0:
                    capacity_score = 30
                elif extra_seats <= 2:
                    capacity_score = 25
                elif extra_seats <= 5:
                    capacity_score = 20
                else:
                    capacity_score = 10

                # ---------------------------------------------
                # Final score
                # ---------------------------------------------
                final_score = (
                    distance_score
                    + capacity_score
                )

                ranked_rooms.append({
                    "room_id": str(room["room_id"]),
                    "room_name": str(room["room_name"]),
                    "floor": room_floor,
                    "wing": room_wing,
                    "capacity": capacity,
                    "equipment": {
                        "video_conference": str(
                            room.get(
                                "video_conf_equipped",
                                ""
                            )
                        ),
                        "projector": str(
                            room.get(
                                "projector",
                                ""
                            )
                        ),
                        "whiteboard": str(
                            room.get(
                                "whiteboard",
                                ""
                            )
                        )
                    },
                    "room_type": str(
                        room.get("room_type", "")
                    ),
                    "building": str(
                        room.get("building", "")
                    ),
                    "distance_score": distance_score,
                    "capacity_score": capacity_score,
                    "final_score": final_score,
                    "reason": (
                        "Suitable capacity and equipment; "
                        "available for requested time."
                    )
                })

            # -------------------------------------------------
            # Sort by score
            # -------------------------------------------------
            ranked_rooms.sort(
                key=lambda x: (
                    -x["final_score"],
                    x["capacity"] - attendees
                )
            )

            # Top 5
            ranked_rooms = ranked_rooms[:5]

            # -------------------------------------------------
            # Final response
            # -------------------------------------------------
            response = {
                "meeting_request": request,
                "employee_location": {
                    "employee_id": employee_id,
                    "floor": employee_floor,
                    "wing": employee_wing
                },
                "matching_rooms": ranked_rooms,
                "count": len(ranked_rooms),
                "message": (
                    "Available rooms found and ranked."
                    if ranked_rooms
                    else "No suitable available rooms found."
                )
            }

            self.status = (
                f"Found {len(ranked_rooms)} "
                "suitable available rooms."
            )

            return Message(
                text=json.dumps(
                    response,
                    indent=2
                )
            )

        except Exception as e:

            self.status = "Error while searching rooms."

            return Message(
                text=json.dumps({
                    "error": str(e)
                }, indent=2)
            )
