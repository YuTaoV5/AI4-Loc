"""Build the current 16-page leadership/developer briefing."""
import pathlib,runpy
runpy.run_path(str(pathlib.Path(__file__).with_name("build_brief.py")),run_name="__main__")
