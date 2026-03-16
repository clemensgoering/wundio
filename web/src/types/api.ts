export interface User {
  id:                    number;
  name:                  string;
  display_name:          string;
  avatar_emoji:          string;
  volume:                number;
  is_active:             boolean;
  spotify_playlist_id:   string | null;
  spotify_playlist_name: string | null;
  created_at:            string;
}

export interface RfidTag {
  id:          number;
  uid:         string;
  label:       string;
  tag_type:    "user" | "playlist" | "action";
  user_id:     number | null;
  spotify_uri: string | null;
  action:      string | null;
  created_at:  string;
}

export interface PlaybackState {
  playing:     boolean;
  track:       string;
  artist:      string;
  album:       string;
  volume:      number;
  position_ms: number;
  duration_ms: number;
  uri:         string;
}

export interface SystemStatus {
  app_name:       string;
  version:        string;
  setup_complete: boolean;
  hotspot_active: boolean;
  hardware?: {
    model:          string;
    ram_mb:         number;
    pi_generation:  number;
  };
  features: {
    spotify:         boolean;
    rfid:            boolean;
    display_oled:    boolean;
    buttons:         boolean;
    ai_local:        boolean;
    ai_cloud:        boolean;
    games_advanced:  boolean;
  };
}