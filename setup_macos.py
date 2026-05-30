from setuptools import setup
import sys

APP = ['launcher.py']
DATA_FILES = [
    'main.py',
    'config.py',
    'pipeline.py',
    'requirements.txt',
    'config.yaml',
    '.env.example',
    ('templates', ['templates/index.html', 'templates/setup_wizard.html']),
    ('static', ['static/style.css', 'static/app.js']),
    ('prompts', ['prompts/highlight_extraction.md', 'prompts/script_cleanup.md', 
                 'prompts/animation_plan.md', 'prompts/thumbnail_title.md', 
                 'prompts/metadata_gen.md']),
    ('helpers', ['helpers/__init__.py', 'helpers/llm_client.py', 
                 'helpers/stt_engine.py', 'helpers/timestamp_aligner.py',
                 'helpers/video_processor.py', 'helpers/animation_executor.py',
                 'helpers/file_watcher.py', 'helpers/uploader.py']),
]

OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'assets/icon.icns',
    'packages': ['fastapi', 'uvicorn', 'jinja2', 'requests', 
                 'faster_whisper', 'opencv_python', 'PIL', 'numpy', 
                 'scipy', 'watchdog', 'pydantic_settings', 'pyyaml', 
                 'python_dotenv', 'aiofiles', 'websockets'],
}

setup(
    name='VIDEOAI',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
