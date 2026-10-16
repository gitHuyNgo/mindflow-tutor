import React from "react";
import {
  Mic, Video, VideoOff, Volume2, VolumeX,
  ScreenShare, ScreenShareOff, LogOut, ExternalLink,
} from "lucide-react";

interface MediaControlsBarProps {
  camOn: boolean;
  audioOn: boolean;
  screenOn: boolean;
  isPiP?: boolean;
  supportsDocPiP?: boolean;
  onToggleCam: () => void;
  onToggleAudio: () => void;
  onToggleScreen: () => void;
  onTogglePiP?: () => void;
  onEndSession: () => void;
  className?: string;
}

export const MediaControlsBar: React.FC<MediaControlsBarProps> = ({
  camOn,
  audioOn,
  screenOn,
  isPiP = false,
  supportsDocPiP = false,
  onToggleCam,
  onToggleAudio,
  onToggleScreen,
  onTogglePiP,
  onEndSession,
  className = "",
}) => {
  return (
    <div
      className={`flex items-center gap-2 p-2 rounded-2xl bg-card/60 backdrop-blur-xl border border-border/50 shadow-lg ${className}`}
    >
      <button
        type="button"
        onClick={onToggleCam}
        title={camOn ? "Turn off camera" : "Turn on camera"}
        className={`p-2.5 rounded-xl transition-all duration-200 ${
          camOn
            ? "bg-primary text-primary-foreground shadow-sm shadow-primary/25"
            : "bg-muted text-muted-foreground hover:bg-muted/80"
        }`}
      >
        {camOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
      </button>

      <button
        type="button"
        onClick={onToggleAudio}
        title={audioOn ? "Mute audio response" : "Unmute audio response"}
        className={`p-2.5 rounded-xl transition-all duration-200 ${
          audioOn
            ? "bg-primary text-primary-foreground shadow-sm shadow-primary/25"
            : "bg-muted text-muted-foreground hover:bg-muted/80"
        }`}
      >
        {audioOn ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
      </button>

      <button
        type="button"
        onClick={onToggleScreen}
        title={screenOn ? "Stop screen sharing" : "Share screen"}
        className={`p-2.5 rounded-xl transition-all duration-200 ${
          screenOn
            ? "bg-primary text-primary-foreground shadow-sm shadow-primary/25"
            : "bg-muted text-muted-foreground hover:bg-muted/80"
        }`}
      >
        {screenOn ? <ScreenShare className="w-4 h-4" /> : <ScreenShareOff className="w-4 h-4" />}
      </button>

      {supportsDocPiP && onTogglePiP && (
        <button
          type="button"
          onClick={onTogglePiP}
          title={isPiP ? "Close floating window" : "Open floating window (Picture-in-Picture)"}
          className={`p-2.5 rounded-xl transition-all duration-200 ${
            isPiP
              ? "bg-primary/20 text-primary border border-primary/30"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          <ExternalLink className="w-4 h-4" />
        </button>
      )}

      <div className="h-5 w-px bg-border/60 mx-1" />

      <button
        type="button"
        onClick={onEndSession}
        title="End study session"
        className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30 hover:bg-rose-500/25 transition-all duration-200 flex items-center gap-1.5"
      >
        <LogOut className="w-3.5 h-3.5" />
        <span>End Session</span>
      </button>
    </div>
  );
};

export default MediaControlsBar;
