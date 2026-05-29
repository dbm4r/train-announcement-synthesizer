import re
import sys
from pathlib import Path
from pydub import AudioSegment
from pydub.playback import play


class TrainAnnouncementsSynthesizer:
    def __init__(self, audio_base_path="Audio"):
        self.audio_base_path = Path(audio_base_path)

        # Polish character mapping
        self.polish_map = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
        }

        # Number words to digits
        self.number_words = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8'
        }

        self.loaded_audio = {}

    def normalize_for_filename(self, text):
        """Convert text to match audio filename"""
        if not text:
            return ""
        for pl, en in self.polish_map.items():
            text = text.replace(pl, en)
        text = text.lower().replace(' ', '_')
        text = re.sub(r'[^\w_]', '', text)
        return text

    def find_audio(self, phrase, category):
        """Find and load audio file"""
        if not phrase or phrase.strip() == '':
            return None

        filename = self.normalize_for_filename(phrase) + '.wav'

        if category == 'station':
            filepath = self.audio_base_path / 'stations' / filename
        elif category == 'track_platform':
            filepath = self.audio_base_path / 'platforms_and_tracks' / filename
        elif category == 'connector':
            filepath = self.audio_base_path / 'to_from' / filename
        else:
            return None

        if not filepath.exists():
            return None

        if str(filepath) not in self.loaded_audio:
            try:
                self.loaded_audio[str(filepath)] = AudioSegment.from_wav(filepath)
                print(f"  ✓ Loaded: {category}/{filename}")
            except Exception as e:
                print(f"  ❌ Error: {filename} - {e}")
                return None

        return self.loaded_audio[str(filepath)]

    def parse_announcement(self, text):
        """Parse announcement text"""
        result = {
            'type': None,
            'from_station': None,
            'to_station': None,
            'via_stations': [],
            'track': None,
            'platform': None,
            'terminates': False
        }

        if 'train terminates here' in text.lower():
            result['terminates'] = True

        if 'train from' in text.lower():
            result['type'] = 'from_to'
            match = re.search(r'Train from (.*?) to (.*?)(?: via (.*?))? will depart', text, re.IGNORECASE)
            if match:
                result['from_station'] = match.group(1).strip()
                result['to_station'] = match.group(2).strip()
                if match.group(3):
                    result['via_stations'] = [s.strip() for s in match.group(3).split(',') if s.strip()]

        elif 'train to' in text.lower():
            result['type'] = 'to'
            match = re.search(r'Train to (.*?) will depart', text, re.IGNORECASE)
            if match:
                result['to_station'] = match.group(1).strip()

        track_match = re.search(r'track (\d+|one|two|three|four|five|six|seven|eight)', text, re.IGNORECASE)
        if track_match:
            track = track_match.group(1).lower()
            result['track'] = self.number_words.get(track, track)

        platform_match = re.search(r'platform (\d+)', text, re.IGNORECASE)
        if platform_match:
            result['platform'] = platform_match.group(1)

        return result

    def synthesize_announcement(self, text):
        """Generate complete announcement"""
        print(f"\n📢 Processing: {text[:80]}...")

        parsed = self.parse_announcement(text)
        audio_parts = []

        # Build announcement
        if parsed['type'] == 'from_to':
            # "Train from"
            audio = self.find_audio('train_from', 'connector')
            if audio: audio_parts.append(audio)

            # From station
            if parsed['from_station']:
                audio = self.find_audio(parsed['from_station'], 'station')
                if audio: audio_parts.append(audio)

            # "to"
            audio = self.find_audio('to', 'connector')
            if audio: audio_parts.append(audio)

            # To station
            if parsed['to_station']:
                audio = self.find_audio(parsed['to_station'], 'station')
                if audio: audio_parts.append(audio)

            # "via" and stations
            if parsed['via_stations']:
                audio = self.find_audio('via', 'connector')
                if audio: audio_parts.append(audio)

                for i, station in enumerate(parsed['via_stations']):
                    audio = self.find_audio(station, 'station')
                    if audio: audio_parts.append(audio)

                    # Add short pause between stations
                    if i < len(parsed['via_stations']) - 1:
                        audio_parts.append(AudioSegment.silent(duration=200))

        elif parsed['type'] == 'to':
            # "Train to"
            audio = self.find_audio('train_to', 'connector')
            if audio: audio_parts.append(audio)

            # Destination station
            if parsed['to_station']:
                audio = self.find_audio(parsed['to_station'], 'station')
                if audio: audio_parts.append(audio)

        # "will depart from track"
        audio = self.find_audio('will_depart_from_track', 'connector')
        if audio:
            audio_parts.append(audio)
        else:
            # Fallback: try individual words
            for word in ['will', 'depart', 'from', 'track']:
                wav = self.find_audio(word, 'connector')
                if wav:
                    audio_parts.append(wav)

        # Track number
        if parsed['track']:
            audio = self.find_audio(parsed['track'], 'track_platform')
            if audio: audio_parts.append(audio)

        # "at platform"
        audio = self.find_audio('at_platform', 'connector')
        if audio:
            audio_parts.append(audio)
        else:
            # Fallback: try individual words
            for word in ['at', 'platform']:
                wav = self.find_audio(word, 'connector')
                if wav:
                    audio_parts.append(wav)

        # Platform number
        if parsed['platform']:
            audio = self.find_audio(parsed['platform'], 'track_platform')
            if audio: audio_parts.append(audio)

        # "Train terminates here"
        if parsed['terminates']:
            audio = self.find_audio('train_terminates_here', 'connector')
            if audio: audio_parts.append(audio)

        if not audio_parts:
            print("  ❌ No audio segments found!")
            return None

        # Remove None values
        audio_parts = [p for p in audio_parts if p is not None]

        print(f"  🔗 Concatenating {len(audio_parts)} segments...")

        # Combine all parts with small pauses
        result = audio_parts[0]
        for part in audio_parts[1:]:
            result += AudioSegment.silent(duration=100) + part

        return result

    def run(self, announcements_file=None):
        """Run synthesizer"""
        if announcements_file:
            try:
                with open(announcements_file, 'r', encoding='utf-8') as f:
                    announcements = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"❌ File not found: {announcements_file}")
                return
        else:
            announcements = [
                "Train from Warszawa Wschodnia to Poznan Głowny via Kutno, Konin, will depart from track 2 at platform 3.",
                "Train from Kraków Głowny to Warszawa Centralna will depart from track 8 at platform 4. Train terminates here.",
                "Train to Lublin Głowny will depart from track 1 at platform 2.",
                "Train to Białystok Zielone Wzgórza will depart from track three at platform two.",
            ]

        print(f"\n{'=' * 60}")
        print(f"🎤 Train Announcement Synthesizer")
        print(f"📁 Audio folder: {self.audio_base_path}")
        print(f"{'=' * 60}")

        for i, announcement in enumerate(announcements, 1):
            print(f"\n{'─' * 50}")
            print(f"📢 Announcement {i}:")
            print(f"   {announcement}")
            print(f"{'─' * 50}")

            audio = self.synthesize_announcement(announcement)

            if audio:
                output_file = f"announcement_{i}.wav"
                audio.export(output_file, format="wav")
                print(f"  💾 Saved to {output_file}")

                response = input(f"\n  ▶️ Play announcement {i}? (y/n): ").lower()
                if response == 'y':
                    print("  🔊 Playing...")
                    play(audio)
            else:
                print(f"  ❌ Failed to synthesize announcement {i}")


def main():
    print("\n🎤 Train Announcement Synthesizer")
    print("=" * 50)

    if len(sys.argv) > 1:
        synthesizer = TrainAnnouncementsSynthesizer()
        synthesizer.run(sys.argv[1])
    else:
        print("\n📝 Using example announcements...")
        synthesizer = TrainAnnouncementsSynthesizer()
        synthesizer.run()


if __name__ == "__main__":
    main()