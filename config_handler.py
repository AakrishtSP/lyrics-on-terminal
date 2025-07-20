import os
import logging
from pathlib import Path
from typing import Dict, Any
import yaml

class Config:
    _default_config = {
        'user_agent': 'LyricsTerminalPlayer/1.0 (+https://github.com/yourusername/lyrics-player)',
        'player_priority': ['spotify', 'vlc', 'rhythmbox', 'clementine'],
        'colors': {
            'clock': {'fg': '#00ffff', 'attrs': ['bold']},  # Cyan
            'song_info': {'fg': '#ff00ff', 'attrs': ['bold']},  # Magenta
            'progress_bar': {'fg': 'default', 'attrs': []},
            'past_lyrics': {'fg': '#ffff00', 'attrs': []},  # Yellow
            'current_lyric': {'fg': '#0000ff', 'attrs': ['bold']},  # Blue
            'future_lyrics': {'fg': 'default', 'attrs': []},
            'progress_time': {'fg': 'white', 'attrs': []} # White
        },
        'ui': {
            'progress_bar_filled': '■',
            'progress_bar_unfilled': '─',
            'time_format': '%H:%M:%S',
            'song_duration_format': '{minutes:02d}:{seconds:02d}'
        }
    }

    def __init__(self, debug=False):
        self.debug = debug
        self.config_paths = self._get_config_paths()
        self.config = self._load_config()
        
    def _get_config_paths(self):
        paths = []
        # First check local directory
        if self.debug:
            paths.append(Path('config.yaml'))
        
        # Then check standard config locations
        paths.extend([
            Path.home() / '.config' / 'lyrics_player' / 'config.yaml',
            Path.cwd() / 'config.yaml',
            Path('config.yaml')
        ])
        return paths

    def _load_config(self) -> Dict[str, Any]:
        for path in self.config_paths:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        return yaml.safe_load(f) or self._default_config
                except Exception as e:
                    logging.error(f"Error loading config {path}: {str(e)}")
        
        # Create default config if none found
        default_path = Path.home() / '.config' / 'lyrics_player' / 'config.yaml'
        default_path.parent.mkdir(parents=True, exist_ok=True)
        with open(default_path, 'w') as f:
            yaml.dump(self._default_config, f, default_flow_style=False)
        return self._default_config
    
    def _create_default_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self._default_config, f, default_flow_style=False)

    @property
    def colors(self) -> Dict[str, Any]:
        return self.config.get('colors', self._default_config['colors'])

    @property
    def ui(self) -> Dict[str, Any]:
        return self.config.get('ui', self._default_config['ui'])
    
    @property
    def player_priority(self):
        return self.config.get('player_priority', self._default_config['player_priority'])
    
    @property
    def user_agent(self):
        return self.config.get('user_agent', self._default_config['user_agent'])