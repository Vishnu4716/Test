from lfx.custom import Component
from lfx.io import MessageTextInput, DataFrameInput, Output
from lfx.schema import Data

import json
from datetime import datetime


class BookMeetingRoom(Component):
    display_name = "Book Meeting Room"
    description = "Validates a selected room against existing bookings and confirms the booking."
    icon = "CalendarCheck"
    name = "BookMeetingRoom"

    inputs = [
        MessageTextInput(
            name="booking_request",
            display_name="Booking Request",
            info=(
                "Booking details in JSON format. "
                "Include room_id, date, start_time, end_time, "
                "attendees, employee_id, and meeting_title."
            ),
            tool_mode=True,
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
            display_name="Booking Result",
            method="book_room",
        )
    ]

    def _time_to_minutes(self, value):
        text = str(value).strip()

        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt)
                return dt.hour * 60 + dt.minute
            except ValueError:
                pass

        return None

    def book_room(self) -> Data:
        try:
            request = self.booking_request

            if isinstance(request, dict):
                booking = request
            else:
                booking = json.loads(str(request))

            required_fields = [
                "room_id",
                "date",
                "start_time",
                "end_time",
                "attendees",
            ]

            missing = [
                field for field in required_fields
                if field not in booking or booking[field] in ("", None)
            ]

            if missing:
                return Data(
                    value={
                        "success": False,
                        "message": (
                            "Missing required booking information: "
                            + ", ".join(missing)
                        ),
                    }
                )

            room_id = str(booking["room_id"]).strip()
            date = str(booking["date"]).strip()
            start_time = str(booking["start_time"]).strip()
            end_time = str(booking["end_time"]).strip()

            requested_start = self._time_to_minutes(start_time)
            requested_end = self._time_to_minutes(end_time)

            if requested_start is None or requested_end is None:
                return Data(
                    value={
                        "success": False,
                        "message": "Invalid time format. Use HH:MM.",
                    }
                )

            if requested_end <= requested_start:
                return Data(
                    value={
                        "success": False,
                        "message": "End time must be after start time.",
                    }
                )

            bookings_df = self.bookings_data

            if bookings_df is None:
                return Data(
                    value={
                        "success": False,
                        "message": "Existing booking data is not available.",
                    }
                )

            # Check existing bookings for the same room and date.
            conflicts = []

            for _, row in bookings_df.iterrows():
                existing_room = str(row.get("room_id", "")).strip()
                existing_date = str(row.get("date", "")).strip()
                status = str(row.get("status", "")).strip().lower()

                if existing_room != room_id:
                    continue

                if existing_date != date:
                    continue

                # Confirmed and tentative bookings block the room.
                if status not in ("confirmed", "tentative"):
                    continue

                existing_start = self._time_to_minutes(
                    row.get("start_time", "")
                )
                existing_end = self._time_to_minutes(
                    row.get("end_time", "")
                )

                if existing_start is None or existing_end is None:
                    continue

                # Standard interval-overlap check.
                if (
                    requested_start < existing_end
                    and requested_end > existing_start
                ):
                    conflicts.append(
                        {
                            "start_time": str(row.get("start_time", "")),
                            "end_time": str(row.get("end_time", "")),
                            "status": str(row.get("status", "")),
                            "meeting_title": str(
                                row.get("meeting_title", "")
                            ),
                        }
                    )

            if conflicts:
                return Data(
                    value={
                        "success": False,
                        "booking_status": "REJECTED",
                        "room_id": room_id,
                        "date": date,
                        "start_time": start_time,
                        "end_time": end_time,
                        "message": (
                            f"Room {room_id} is not available for the "
                            f"requested time because it has an overlapping "
                            f"booking."
                        ),
                        "conflicts": conflicts,
                    }
                )

            # No conflict found.
            confirmation = {
                "success": True,
                "booking_status": "CONFIRMED",
                "room_id": room_id,
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "attendees": booking["attendees"],
                "employee_id": booking.get("employee_id", ""),
                "meeting_title": booking.get(
                    "meeting_title",
                    "Meeting Room Booking"
                ),
                "message": (
                    f"Room {room_id} is available and the booking "
                    f"can be confirmed."
                ),
            }

            self.status = confirmation

            return Data(value=confirmation)

        except json.JSONDecodeError:
            return Data(
                value={
                    "success": False,
                    "message": (
                        "Booking request must be valid JSON."
                    ),
                }
            )

        except Exception as exc:
            return Data(
                value={
                    "success": False,
                    "message": f"Booking validation failed: {str(exc)}",
                }
            )
