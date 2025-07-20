#!/usr/bin/env python3

import curses
import dbus
import time
import logging
import signal
import sys
from datetime import datetime
from lrclib import LrcLibAPI
from wcwidth import wcswidth
from config_handler import Config

debug = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('lyrics_player.log')] if debug
    else [logging.FileHandler('/tmp/lyrics_player.log')]
)

# Priority list of player names (higher priority first)
PLAYER_PRIORITY = ['vlc', 'spotify', 'rhythmbox', 'clementine']


class LyricsPlayer:
    __slots__ = [
        'stdscr', 'config', 'current_lyrics', 'current_player',
        'last_update', 'current_position', 'song_duration',
        'metadata', 'shutdown_flag', 'lrc_client', 'color_map',
        'attr_map', 'color_pairs', 'hex_cache'
    ]

    def __init__(self, stdscr, debug=False):
        self.stdscr = stdscr
        self.config = Config(debug=debug)
        self.current_lyrics = []
        self.current_player = None
        self.last_update = 0
        self.current_position = 0
        self.song_duration = 0
        self.metadata = {}
        self.hex_cache = {}
        self.shutdown_flag = False
        self.lrc_client = LrcLibAPI(
            user_agent=self.config.config.get('user_agent', 'LyricsTerminalPlayer/1.0'))

        self.color_map = {
            'default': -1,
            'black': curses.COLOR_BLACK,
            'red': curses.COLOR_RED,
            'green': curses.COLOR_GREEN,
            'yellow': curses.COLOR_YELLOW,
            'blue': curses.COLOR_BLUE,
            'magenta': curses.COLOR_MAGENTA,
            'cyan': curses.COLOR_CYAN,
            'white': curses.COLOR_WHITE,
        }

        # Attribute mapping
        self.attr_map = {
            'bold': curses.A_BOLD,
            'underline': curses.A_UNDERLINE,
            'italic': curses.A_ITALIC,
            'standout': curses.A_STANDOUT
        }

        # Initialize colors
        curses.use_default_colors()
        self.init_colors()
        self.setup_mpris()

    def hex_to_256color(self, hex_color: str) -> int:
        """Convert #RRGGBB to nearest 256-color index"""
        if hex_color in self.hex_cache:
            return self.hex_cache[hex_color]
        try:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) != 6:
                return -1

            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)

            if r == g == b:
                # Grayscale matching
                gray_index = round((r - 8) / 10)
                gray_index = max(0, min(23, gray_index))
                return 232 + gray_index

            # RGB cube matching
            r_idx = min(5, max(0, round(r / 51)))
            g_idx = min(5, max(0, round(g / 51)))
            b_idx = min(5, max(0, round(b / 51)))
            result = 16 + 36 * r_idx + 6 * g_idx + b_idx
        except:
            result = -1
        self.hex_cache[hex_color] = result
        return result

    def init_colors(self):
        """Initialize color pairs with hex color support"""
        curses.start_color()
        curses.use_default_colors()
        self.color_pairs = {}
        pair_number = 1

        for color_key, config in self.config.colors.items():
            fg = config['fg']
            color_number = -1

            # Handle hex colors
            if isinstance(fg, str) and fg.startswith('#'):
                color_number = self.hex_to_256color(fg)
            elif isinstance(fg, int):
                color_number = fg
            elif fg in self.color_map:
                color_number = self.color_map[fg]
            else:
                try:
                    color_number = int(fg)
                except:
                    pass

            # Validate color number
            max_colors = curses.COLORS if curses.has_colors() else 0
            if color_number >= max_colors:
                color_number = -1

            # Initialize color pair
            try:
                curses.init_pair(pair_number, color_number, -1)
            except:
                color_number = -1

            # Combine attributes
            attrs = 0
            for attr in config.get('attrs', []):
                attrs |= self.attr_map.get(attr, 0)

            self.color_pairs[color_key] = curses.color_pair(
                pair_number) | attrs
            pair_number += 1

    # def create_color_pair(self, config):
    #     fg = self.color_map.get(config['fg'], curses.COLOR_WHITE)
    #     attrs = 0
    #     for attr in config.get('attrs', []):
    #         attrs |= self.attr_map.get(attr, 0)
    #     return curses.color_pair(fg) | attrs

    def setup_mpris(self):
        bus = dbus.SessionBus()
        try:
            players = [name for name in bus.list_names()
                       if name.startswith('org.mpris.MediaPlayer2.')]

            # Use configurable player priority
            sorted_players = sorted(
                players,
                key=lambda x: next(
                    (i for i, p in enumerate(self.config.player_priority)
                     if p in x.lower()),
                    # Default to lowest priority
                    len(self.config.player_priority)
                )
            )
            for player in sorted_players:
                proxy = bus.get_object(player, '/org/mpris/MediaPlayer2')
                properties = dbus.Interface(
                    proxy, 'org.freedesktop.DBus.Properties')
                status = properties.Get(
                    'org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
                if status != 'Stopped':
                    self.current_player = (player, proxy, properties)
                    break
        except Exception as e:
            pass

    def get_metadata(self):
        if not self.current_player:
            return {}

        try:
            metadata = self.current_player[2].Get(
                'org.mpris.MediaPlayer2.Player', 'Metadata')
            pos = self.current_player[2].Get(
                'org.mpris.MediaPlayer2.Player', 'Position') / 1e6
            duration = metadata.get('mpris:length', 0) / 1e6

            # Handle different metadata formats
            artist = metadata.get('xesam:artist', ['Unknown Artist'])
            if isinstance(artist, dbus.Array):
                artist = list(artist)

            return {
                'title': str(metadata.get('xesam:title', 'Unknown Track')),
                'artist': ', '.join(artist) if artist else 'Unknown Artist',
                'album': str(metadata.get('xesam:album', 'Unknown Album')),
                'duration': duration,
                'position': pos
            }
        except Exception as e:
            logging.error(f"Metadata error: {str(e)}")
            self.current_player = None
            return {}

    def fetch_lyrics(self, artist, title, album, duration):
        try:
            logging.info(
                f"Searching lyrics for: {artist} - {title} ({duration}s)")

            # First try exact match with get_lyrics
            try:
                lyrics = self.lrc_client.get_lyrics(
                    track_name=title,
                    artist_name=artist,
                    album_name=album,
                    duration=int(duration)
                )
                logging.debug(f"GetLyrics response: {lyrics}")
                if lyrics and (lyrics.synced_lyrics or lyrics.plain_lyrics):
                    logging.info("Found direct match using get_lyrics")
                    return self.parse_lyrics(lyrics.synced_lyrics or lyrics.plain_lyrics)
            except Exception as e:
                logging.warning(f"Direct lookup failed: {str(e)}")

            # Fallback to search if direct match fails
            results = self.lrc_client.search_lyrics(
                track_name=title,
                artist_name=artist
            )

            if not results:
                logging.warning("No lyrics found in search results")
                return []

            # Find best match from search results
            best_match = None
            for result in results:
                if (result.track_name.lower() == title.lower() and
                    result.artist_name.lower() == artist.lower() and
                        abs(result.duration - duration) < 2):
                    best_match = result
                    break

            if not best_match:
                best_match = results[0]

            logging.info(
                f"Using lyrics: {best_match.artist_name} - {best_match.track_name}")
            return self.parse_lyrics(best_match.synced_lyrics or best_match.plain_lyrics)

        except Exception as e:
            logging.error(f"Lyrics fetch error: {str(e)}")
            return []

    def parse_lyrics(self, lyrics_text):
        lyrics = []
        if not lyrics_text:
            return lyrics

        for line in lyrics_text.split('\n'):
            line = line.strip()
            if line and ']' in line:
                time_part, text = line.split(']', 1)
                time_str = time_part[1:].strip()
                try:
                    # Handle both [mm:ss.xx] and [mm:ss] formats
                    if ':' in time_str:
                        mins, rest = time_str.split(':', 1)
                        # Convert to float to handle milliseconds
                        total_secs = float(mins) * 60 + float(rest)
                        lyrics.append((total_secs, text.strip()))
                except Exception as e:
                    logging.warning(f"Failed to parse line: {line} - {str(e)}")
        return lyrics

    def format_time(self, seconds: float) -> str:
        """Convert seconds to configured format"""
        fmt = self.config.ui['song_duration_format']
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return fmt.format(minutes=minutes, seconds=seconds)

    def draw_centered(self, y: int, text: str, color_pair=None):
        if not text:
            return
        display_width = wcswidth(text)
        x = max(0, (curses.COLS - display_width) // 2)
        if color_pair is None:
            self.stdscr.addstr(y, x, text)
        else:
            self.stdscr.addstr(y, x, text, color_pair)

    def draw_progress_bar(self, y: int, progress: float):
        """Draw progress bar with configured characters"""
        ui_config = self.config.ui
        width = curses.COLS - 4
        filled = int(width * progress)
        bar = '[' + (ui_config['progress_bar_filled'] * filled) + \
              (ui_config['progress_bar_unfilled'] * (width - filled)) + ']'
        self.draw_centered(y, bar, self.color_pairs['progress_bar'])

        # Draw time information
        time_str = f"{self.format_time(self.current_position)} / {self.format_time(self.song_duration)}"
        self.draw_centered(y + 1, time_str, self.color_pairs['progress_bar'])

    def draw_lyrics(self):
        if not self.current_lyrics:
            self.draw_centered(curses.LINES//2, "No lyrics available",
                               self.color_pairs['future_lyrics'])
            return

        current_line = 0
        for i, (t, _) in enumerate(self.current_lyrics):
            if t <= self.current_position:
                current_line = i
            else:
                break

        start_line = max(0, current_line - (curses.LINES // 3))

        y = 0
        for i in range(start_line, len(self.current_lyrics)):
            t, line = self.current_lyrics[i]
            if y >= curses.LINES - 6:
                break

            if i < current_line:
                color = self.color_pairs['past_lyrics']
            elif i == current_line:
                color = self.color_pairs['current_lyric']
            else:
                color = self.color_pairs['future_lyrics']

            self.draw_centered(y + 4, line, color)
            y += 1

    def update(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()

        # Draw clock
        current_time = datetime.now().strftime('%H:%M:%S')
        self.draw_centered(0, current_time, 2)

        # Get metadata and position
        metadata = self.get_metadata()
        if metadata:
            self.current_position = metadata.get('position', 0)
            self.song_duration = metadata.get('duration', 0)
            artist = metadata.get('artist', '')
            title = metadata.get('title', '')
            album = metadata.get('album', '')

            # Check if song changed
            if (artist != self.metadata.get('artist') or
                title != self.metadata.get('title') or
                    time.time() - self.last_update > 30):
                self.metadata = metadata
                self.current_lyrics = self.fetch_lyrics(
                    artist, title, album, self.song_duration)
                self.last_update = time.time()

            # Draw song info
            self.draw_centered(1, f"{artist} - {title}", 2)

            # Draw progress bar and time
            if self.song_duration > 0:
                progress = self.current_position / self.song_duration
                self.draw_progress_bar(2, progress)

        # Draw lyrics
        self.draw_lyrics()

        self.stdscr.refresh()

    def signal_handler(self, signum, frame):
        self.shutdown_flag = True


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(100)
    player = LyricsPlayer(stdscr, debug=debug)

    # Register signal handlers
    signal.signal(signal.SIGINT, player.signal_handler)
    signal.signal(signal.SIGTERM, player.signal_handler)

    while not player.shutdown_flag:
        c = stdscr.getch()
        if c == curses.KEY_RESIZE:
            curses.resizeterm(*stdscr.getmaxyx())
            stdscr.clear()
            player.update()
        elif c == ord('q'):
            break
        player.update()
        time.sleep(0.05)


if __name__ == '__main__':
    curses.wrapper(main)
