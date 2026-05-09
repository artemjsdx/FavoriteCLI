from ..ui.chat import print_step_block


def render_step(text: str) -> None:
    """Render a ≪STEP≫ block to the UI."""
    print_step_block(text)
