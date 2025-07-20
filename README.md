# Lyrics On Terminal

A real-time lyrics display application for your terminal that syncs with media players via MPRIS2. Watch synchronized lyrics appear as your songs play, all from the comfort of your terminal.

## Features

- **Real-time synchronized lyrics** - Displays time-synced lyrics that follow along with your music
- **Multiple media player support** - Works with Spotify, VLC, Rhythmbox, Clementine, and other MPRIS2-compatible players
- **Configurable appearance** - Customize colors, fonts, and UI elements through YAML configuration
- **Automatic lyrics fetching** - Retrieves lyrics from LrcLib API with fallback search capabilities
- **Progress tracking** - Shows song progress with a visual progress bar and time indicators
- **Responsive design** - Adapts to terminal window resizing
- **Hex color support** - Supports both named colors and hex color codes for advanced theming

## Installation

### Prerequisites

- Python 3.7+
- Linux system with D-Bus support
- A media player that supports MPRIS2 (Spotify, VLC, etc.)

### Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

### Setup

1. Clone this repository:
```bash
git clone https://github.com/AakrishtSP/Lyrics-On-Terminal.git
cd Lyrics-On-Terminal
```

2. Run the application:
```bash
python main.py
```

## Usage

1. Start your preferred media player (Spotify, VLC, etc.)
2. Begin playing a song
3. Run the lyrics player:
   ```bash
   python main.py
   ```
4. The application will automatically detect your media player and display synchronized lyrics
5. Press `q` to quit the application

### Controls

- `q` - Quit the application
- Terminal resizing is automatically handled

## Configuration

The application uses a YAML configuration file located at:
- `~/.config/lyrics_player/config.yaml` (primary location)
- `./config.yaml` (local directory)

### Configuration Options

#### Player Priority
Set the priority order for media player detection:
```yaml
player_priority:
  - spotify
  - vlc
  - rhythmbox
  - clementine
```

#### Colors and Styling
Customize the appearance of different UI elements:
```yaml
colors:
  clock:
    fg: cyan
    attrs: [bold]
  song_info:
    fg: magenta
    attrs: [bold]
  progress_bar:
    fg: white
    attrs: []
  past_lyrics:
    fg: yellow
    attrs: []
  current_lyric:
    fg: blue
    attrs: [bold]
  future_lyrics:
    fg: white
    attrs: []
  progress_time:
    fg: white
    attrs: []
```

**Color Options:**
- Named colors: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `default`
- Hex colors: `#ff0000`, `#00ff00`, etc.
- 256-color codes: Integer values

**Attributes:**
- `bold` - Bold text
- `underline` - Underlined text
- `italic` - Italic text (if supported by terminal)
- `standout` - Standout mode

#### UI Customization
```yaml
ui:
  progress_bar_filled: "▓"
  progress_bar_unfilled: "░"
  time_format: "%H:%M:%S"
  song_duration_format: "{minutes:02d}:{seconds:02d}"
```

#### User Agent
Customize the user agent for API requests:
```yaml
user_agent: "LyricsTerminalPlayer/1.0 (https://github.com/yourusername/lyrics-player)"
```

## File Structure

- `main.py` - Main application entry point and lyrics display logic
- `config_handler.py` - Configuration management and default settings
- `config.yaml` - User configuration file
- `logging.conf` - Logging configuration for debugging
- `lyrics_player.log` - Application log file

## How It Works

1. **Media Player Detection**: Uses D-Bus to communicate with MPRIS2-compatible media players
2. **Metadata Extraction**: Retrieves song information (artist, title, album, duration, position)
3. **Lyrics Fetching**: Queries LrcLib API for synchronized lyrics using song metadata
4. **Synchronization**: Matches lyrics timestamps with current playback position
5. **Display**: Renders lyrics in terminal with highlighting for current line

## Troubleshooting

### No lyrics found
- Ensure your song metadata (artist, title) is accurate
- Some songs may not have synchronized lyrics available in the LrcLib database
- Check the log file for API errors: `cat lyrics_player.log`

### Media player not detected
- Verify your media player supports MPRIS2
- Check if the player is running and playing music
- Ensure D-Bus is properly configured on your system

### Configuration not loading
- Check file permissions for the config file
- Verify YAML syntax is correct
- Default configuration will be created if none exists

### Terminal display issues
- Ensure your terminal supports Unicode characters for progress bars
- Check terminal color support (256-color recommended)
- Resize terminal if text appears cut off

## Logging

Logging is configured via `logging.conf`. Logs are written to:
- `lyrics_player.log` (debug mode)
- `/tmp/lyrics_player.log` (normal mode)

Log levels can be adjusted in the configuration file for debugging purposes.

## Dependencies

- **dbus-python**: D-Bus communication with media players
- **lrclib**: Lyrics fetching from LrcLib API
- **PyYAML**: Configuration file parsing
- **wcwidth**: Unicode width calculation for proper text alignment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Please check the repository for license information.

## Credits

- Uses [LrcLib](https://lrclib.net/) for lyrics data
- Built with Python's curses library for terminal UI
- MPRIS2 integration for media player communication