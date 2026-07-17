"""Small, shared building blocks for consistent wizard pages."""

from PyQt5.QtWidgets import QLabel, QVBoxLayout


def add_page_header(
    layout: QVBoxLayout,
    step_label: str,
    title: str,
    description: str,
) -> tuple[QLabel, QLabel, QLabel]:
    """Add the standard eyebrow, title, and supporting copy to a page."""
    eyebrow = QLabel(step_label.upper())
    eyebrow.setProperty("role", "eyebrow")

    title_label = QLabel(title)
    title_label.setProperty("role", "page-title")
    title_label.setWordWrap(True)

    description_label = QLabel(description)
    description_label.setProperty("role", "page-description")
    description_label.setWordWrap(True)

    layout.addWidget(eyebrow)
    layout.addWidget(title_label)
    layout.addWidget(description_label)
    layout.addSpacing(8)
    return eyebrow, title_label, description_label
