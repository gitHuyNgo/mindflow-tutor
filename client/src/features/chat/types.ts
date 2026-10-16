export type MessageRole = "user" | "ai";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  imageBase64?: string;
  audioUrl?: string;
  timestamp?: string;
}

export type FileStatus = "uploading" | "processing" | "ready" | "error";

export interface DocFile {
  id: string;
  docId?: string;
  name: string;
  size: number;
  status: FileStatus;
  error?: string;
}

export type DetectorState = null | "confused" | "distracted";

export interface PipBridge {
  updateMessages: (msgs: Message[], loading: boolean) => void;
  updateControls: (cam: boolean) => void;
  updateAudio: (on: boolean) => void;
  updateScreen: (on: boolean) => void;
  updateRecording: (rec: boolean) => void;
}
