from typing import List, Optional, Dict
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

from src.database.models import CalendarEvent
from src.services.calendar.client import CalendarClient
from src.ui.styles.theme import Theme, Symbols, Colors


class CalendarList:
    def __init__(self, console: Console):
        self._console = console

    def render(
        self,
        events: List[CalendarEvent],
        title: str = "Upcoming Events",
        show_index: bool = True,
        group_by_date: bool = True,
    ) -> None:
        header_text = Text()
        header_text.append(f"{Symbols.CALENDAR} ", style="primary")
        header_text.append(title, style="header.title")
        
        if events:
            header_text.append(f" ({len(events)} events)", style="text.muted")

        self._console.print()
        self._console.print(header_text)
        self._console.print(Theme.create_divider(70))

        if not events:
            empty_text = Text()
            empty_text.append("\n  No upcoming events\n", style="text.muted")
            self._console.print(empty_text)
            return

        if group_by_date:
            self._render_grouped(events, show_index)
        else:
            self._render_flat(events, show_index)

    def _render_grouped(self, events: List[CalendarEvent], show_index: bool) -> None:
        grouped: Dict[str, List[tuple]] = {}
        
        for i, event in enumerate(events):
            if event.start_time:
                date_key = event.start_time.strftime("%Y-%m-%d")
                date_label = CalendarClient.format_event_date(event)
            else:
                date_key = "unknown"
                date_label = "Unknown Date"
            
            if date_key not in grouped:
                grouped[date_key] = []
            
            grouped[date_key].append((i, event, date_label))

        global_index = 0
        
        for date_key in sorted(grouped.keys()):
            items = grouped[date_key]
            date_label = items[0][2]
            
            self._console.print()
            
            date_text = Text()
            
            if date_label == "Today":
                date_text.append(f"  {Symbols.BULLET} ", style="calendar.today")
                date_text.append(date_label, style="calendar.today")
            elif date_label == "Tomorrow":
                date_text.append(f"  {Symbols.BULLET} ", style="primary")
                date_text.append(date_label, style="primary")
            else:
                date_text.append(f"  {Symbols.BULLET} ", style="text.dim")
                date_text.append(date_label, style="text")
            
            self._console.print(date_text)
            self._console.print()

            for _, event, _ in items:
                global_index += 1
                self._render_event_row(event, global_index if show_index else None)

    def _render_flat(self, events: List[CalendarEvent], show_index: bool) -> None:
        for i, event in enumerate(events):
            self._render_event_row(event, i + 1 if show_index else None)

    def _render_event_row(self, event: CalendarEvent, index: Optional[int] = None) -> None:
        row_text = Text()
        
        if index is not None:
            row_text.append(f"    [{index:2}] ", style="menu.shortcut")
        else:
            row_text.append("    ", style="text")

        time_str = CalendarClient.format_event_time_short(event)
        row_text.append(f"{time_str:15}", style="calendar.time")

        if event.meeting_link:
            row_text.append(f"{Symbols.MEETING} ", style="calendar.meeting")
        else:
            row_text.append(f"{Symbols.EVENT} ", style="calendar.event")

        title = event.title
        if len(title) > 35:
            title = title[:32] + "..."
        row_text.append(title, style="text")

        self._console.print(row_text)

        if event.location:
            location_text = Text()
            location_text.append("         ", style="text")
            if index is not None:
                location_text.append("      ", style="text")
            location_text.append(f"{Symbols.LOCATION} ", style="text.muted")
            
            location = event.location
            if len(location) > 40:
                location = location[:37] + "..."
            location_text.append(location, style="calendar.location")
            
            self._console.print(location_text)

    def render_compact(
        self,
        events: List[CalendarEvent],
        max_items: int = 5,
    ) -> None:
        if not events:
            empty_text = Text()
            empty_text.append("  No upcoming events", style="text.muted")
            self._console.print(empty_text)
            return

        display_events = events[:max_items]

        for event in display_events:
            row_text = Text()
            row_text.append("  ", style="text")

            if event.meeting_link:
                row_text.append(f"{Symbols.MEETING} ", style="calendar.meeting")
            else:
                row_text.append(f"{Symbols.EVENT} ", style="calendar.event")

            time_str = CalendarClient.format_event_time_short(event)
            row_text.append(f"{time_str} ", style="calendar.time")

            title = event.title
            if len(title) > 30:
                title = title[:27] + "..."
            row_text.append(title, style="text")

            self._console.print(row_text)

        if len(events) > max_items:
            more_text = Text()
            more_text.append(f"  ... and {len(events) - max_items} more", style="text.muted")
            self._console.print(more_text)

    def render_single(self, event: CalendarEvent) -> None:
        panel_content = []

        title_text = Text()
        title_text.append(event.title, style="header.title")
        panel_content.append(title_text)

        panel_content.append(Text())

        time_text = Text()
        time_text.append(f"{Symbols.TIME} ", style="primary")
        time_text.append(CalendarClient.format_event_time(event), style="text")
        panel_content.append(time_text)

        if event.location:
            location_text = Text()
            location_text.append(f"{Symbols.LOCATION} ", style="primary")
            location_text.append(event.location, style="text")
            panel_content.append(location_text)

        if event.meeting_link:
            link_text = Text()
            link_text.append(f"{Symbols.LINK} ", style="primary")
            link_text.append(event.meeting_link, style="link")
            panel_content.append(link_text)

        if event.attendees:
            panel_content.append(Text())
            attendees_header = Text()
            attendees_header.append(f"{Symbols.MEETING} Attendees:", style="text.dim")
            panel_content.append(attendees_header)
            
            for attendee in event.attendees[:10]:
                attendee_text = Text()
                attendee_text.append(f"  {Symbols.BULLET} ", style="text.muted")
                attendee_text.append(attendee, style="text")
                panel_content.append(attendee_text)
            
            if len(event.attendees) > 10:
                more_text = Text()
                more_text.append(
                    f"  ... and {len(event.attendees) - 10} more",
                    style="text.muted"
                )
                panel_content.append(more_text)

        if event.description:
            panel_content.append(Text())
            desc_header = Text()
            desc_header.append("Description:", style="text.dim")
            panel_content.append(desc_header)
            
            desc_text = Text()
            description = event.description
            if len(description) > 500:
                description = description[:497] + "..."
            desc_text.append(description, style="text")
            panel_content.append(desc_text)

        content = Text("\n").join(panel_content)

        self._console.print()
        self._console.print(Panel(
            content,
            border_style="calendar.event",
            title=f"{Symbols.CALENDAR} Event Details",
            title_align="left",
        ))

    def render_today_summary(self, events: List[CalendarEvent]) -> None:
        header_text = Text()
        header_text.append(f"{Symbols.CALENDAR} ", style="calendar.today")
        header_text.append("Today's Schedule", style="calendar.today")

        self._console.print()
        self._console.print(header_text)
        self._console.print(Theme.create_divider(50))

        if not events:
            empty_text = Text()
            empty_text.append("\n  No events scheduled for today\n", style="text.muted")
            self._console.print(empty_text)
            return

        now = datetime.now()

        for event in events:
            row_text = Text()
            row_text.append("  ", style="text")

            is_current = False
            if event.start_time and event.end_time:
                is_current = event.start_time <= now <= event.end_time

            if is_current:
                row_text.append(f"{Symbols.ARROW_RIGHT} ", style="calendar.today")
            elif event.meeting_link:
                row_text.append(f"{Symbols.MEETING} ", style="calendar.meeting")
            else:
                row_text.append(f"{Symbols.EVENT} ", style="calendar.event")

            time_str = CalendarClient.format_event_time_short(event)
            
            if is_current:
                row_text.append(f"{time_str:15}", style="calendar.today")
                row_text.append(event.title, style="calendar.today")
                row_text.append(" (NOW)", style="highlight")
            else:
                row_text.append(f"{time_str:15}", style="calendar.time")
                row_text.append(event.title, style="text")

            self._console.print(row_text)

        self._console.print()
