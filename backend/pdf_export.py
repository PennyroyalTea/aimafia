"""Generate a PDF report from game analysis data using fpdf2."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fpdf import FPDF

from backend.models import GameAnalysis, PersonalAdvice

FONT_PATH = Path(__file__).parent / "fonts" / "Roboto.ttf"

# A4 dimensions in mm
PAGE_W = 210
PAGE_H = 297
MARGIN = 15
CONTENT_W = PAGE_W - 2 * MARGIN


class GamePdf(FPDF):
    def __init__(self, analysis: GameAnalysis) -> None:
        super().__init__()
        self.analysis = analysis
        self.set_auto_page_break(auto=True, margin=MARGIN)
        self.add_font("Roboto", "", str(FONT_PATH))
        self.set_font("Roboto", "", 10)

    def header(self) -> None:
        pass

    def footer(self) -> None:
        self.set_y(-10)
        self.set_font("Roboto", "", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"{self.page_no()}/{{nb}}", align="R")

    def build(self) -> None:
        self.alias_nb_pages()
        self._render_summary_page()
        self.add_page()
        self._render_advice_pages()

    def _render_summary_page(self) -> None:
        s = self.analysis.summary
        self.add_page()

        # Title
        if s.title:
            self.set_font("Roboto", "", 16)
            self.set_text_color(26, 26, 26)
            self.multi_cell(CONTENT_W, 7, s.title)
            self.ln(2)

        # Winner badge
        badge_colors = {
            "mafia": ((198, 40, 40), (252, 228, 228)),
            "citizens": ((46, 125, 50), (232, 245, 233)),
        }
        text_color, bg_color = badge_colors.get(
            s.winner, ((97, 97, 97), (245, 245, 245))
        )
        badge_text = {
            "mafia": "Mafia wins",
            "citizens": "Citizens win",
        }.get(s.winner, "Unknown outcome")

        self.set_fill_color(*bg_color)
        self.set_text_color(*text_color)
        self.set_font("Roboto", "", 11)
        badge_w = self.get_string_width(badge_text) + 8
        self.cell(badge_w, 7, badge_text, fill=True)
        self.ln(10)

        # Summary text
        self.set_text_color(26, 26, 26)
        self.set_font("Roboto", "", 10)
        self.multi_cell(CONTENT_W, 5, s.summary)
        self.ln(4)

        # Key moments
        if s.key_moments:
            self._section_heading("Key moments")
            self.set_font("Roboto", "", 9)
            self.set_text_color(50, 50, 50)
            for moment in s.key_moments:
                x = self.get_x()
                self.cell(5, 4.5, chr(0x2022) + " ")
                self.multi_cell(CONTENT_W - 5, 4.5, moment)
                self.set_x(x)
            self.ln(4)

        # Players (2-column)
        if s.players:
            self._section_heading("Players")
            col_w = (CONTENT_W - 6) / 2
            for i in range(0, len(s.players), 2):
                left = s.players[i]
                right = s.players[i + 1] if i + 1 < len(s.players) else None
                y_start = self.get_y()

                # Left column
                self._render_player_summary(left, MARGIN, y_start, col_w)
                y_after_left = self.get_y()

                # Right column
                if right:
                    self._render_player_summary(
                        right, MARGIN + col_w + 6, y_start, col_w
                    )
                y_after_right = self.get_y()

                # Move to the bottom of the taller column
                self.set_y(max(y_after_left, y_after_right) + 1)

                # Divider line
                self.set_draw_color(220, 220, 220)
                self.line(
                    MARGIN, self.get_y(), MARGIN + CONTENT_W, self.get_y()
                )
                self.ln(1)

    def _render_player_summary(
        self, player: "PlayerSummary", x: float, y: float, w: float  # noqa: F821
    ) -> None:
        self.set_xy(x, y)
        self.set_font("Roboto", "", 9)
        self.set_text_color(26, 26, 26)
        name = player.player_name
        if player.role:
            name += f" ({player.role})"
        self.multi_cell(w, 4, name)
        self.set_x(x)
        self.set_font("Roboto", "", 8)
        self.set_text_color(80, 80, 80)
        self.multi_cell(w, 3.5, player.summary)

    def _render_advice_pages(self) -> None:
        advice = self.analysis.advice
        if not advice:
            return

        self.set_font("Roboto", "", 14)
        self.set_text_color(26, 26, 26)
        self.cell(CONTENT_W, 7, "Personal coaching")
        self.ln(8)

        col_w = (CONTENT_W - 6) / 2
        for i in range(0, len(advice), 2):
            left = advice[i]
            right = advice[i + 1] if i + 1 < len(advice) else None

            left_h = self._estimate_card_height(left, col_w)
            right_h = self._estimate_card_height(right, col_w) if right else 0
            row_h = max(left_h, right_h)

            # Check if we need a page break
            if self.get_y() + row_h > PAGE_H - MARGIN:
                self.add_page()

            y_start = self.get_y()

            self._render_advice_card(left, MARGIN, y_start, col_w)
            if right:
                self._render_advice_card(
                    right, MARGIN + col_w + 6, y_start, col_w
                )

            self.set_y(y_start + row_h + 4)

    def _estimate_card_height(
        self, advice: PersonalAdvice, w: float
    ) -> float:
        """Rough estimate of card height for page break decisions."""
        h = 12.0  # header + padding
        inner = w - 6  # card padding
        self.set_font("Roboto", "", 8)
        for plays in (advice.good_plays, advice.mistakes):
            if plays:
                h += 6  # section title
                for item in plays:
                    lines = self.multi_cell(
                        inner, 3.5, chr(0x2022) + " " + item, dry_run=True, output="LINES"
                    )
                    h += len(lines) * 3.5
        # Coaching
        h += 6
        self.set_font("Roboto", "", 8)
        lines = self.multi_cell(
            inner, 3.5, advice.advice, dry_run=True, output="LINES"
        )
        h += len(lines) * 3.5
        h += 4  # bottom padding
        return h

    def _render_advice_card(
        self, advice: PersonalAdvice, x: float, y: float, w: float
    ) -> None:
        # Calculate card height for the border
        card_h = self._estimate_card_height(advice, w)

        # Card border
        self.set_draw_color(200, 200, 200)
        self.rect(x, y, w, card_h, style="D")

        pad = 3
        inner = w - 2 * pad
        cx = x + pad
        cy = y + pad

        # Player name
        self.set_xy(cx, cy)
        self.set_font("Roboto", "", 10)
        self.set_text_color(26, 26, 26)
        name = advice.player_name
        if advice.role:
            name += f" ({advice.role})"
        self.multi_cell(inner, 4.5, name)
        cy = self.get_y() + 1

        # Good plays
        if advice.good_plays:
            cy = self._render_card_section(
                cx, cy, inner, "Good plays", (46, 125, 50), advice.good_plays
            )

        # Mistakes
        if advice.mistakes:
            cy = self._render_card_section(
                cx, cy, inner, "Mistakes", (198, 40, 40), advice.mistakes
            )

        # Coaching
        self.set_xy(cx, cy)
        self.set_font("Roboto", "", 7)
        self.set_text_color(74, 80, 200)
        self.cell(inner, 4, "COACHING")
        self.ln(4)
        self.set_x(cx)
        self.set_font("Roboto", "", 8)
        self.set_text_color(50, 50, 50)
        self.multi_cell(inner, 3.5, advice.advice)

    def _render_card_section(
        self,
        x: float,
        y: float,
        w: float,
        title: str,
        color: tuple[int, int, int],
        items: list[str],
    ) -> float:
        self.set_xy(x, y)
        self.set_font("Roboto", "", 7)
        self.set_text_color(*color)
        self.cell(w, 4, title.upper())
        self.ln(4)

        self.set_font("Roboto", "", 8)
        self.set_text_color(50, 50, 50)
        for item in items:
            self.set_x(x)
            self.multi_cell(w, 3.5, chr(0x2022) + " " + item)

        return self.get_y() + 1

    def _section_heading(self, text: str) -> None:
        self.set_font("Roboto", "", 12)
        self.set_text_color(26, 26, 26)
        self.cell(CONTENT_W, 6, text)
        self.ln(2)
        self.set_draw_color(220, 220, 220)
        self.line(MARGIN, self.get_y(), MARGIN + CONTENT_W, self.get_y())
        self.ln(3)


def generate_pdf(analysis: GameAnalysis) -> bytes:
    """Generate a PDF report and return it as bytes."""
    pdf = GamePdf(analysis)
    pdf.build()
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
