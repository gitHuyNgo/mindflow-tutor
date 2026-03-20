import numpy as np
import logging
import base64
import io
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handles audio processing including VAD"""
    
    def __init__(self, sample_rate: int = 16000, vad_threshold: float = 0.3):
        self.sample_rate = sample_rate
        self.vad_threshold = vad_threshold
        self.audio_buffer = []
        self.silence_frames = 0
        self.speech_frames = 0
    
    def detect_voice_activity(self, audio_data: bytes) -> Tuple[bool, float]:
        """
        Detect voice activity using energy-based approach.
        Returns: (has_speech, confidence)
        """
        try:
            # Convert bytes to numpy array (assuming PCM 16-bit format)
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            if len(audio_np) == 0:
                return False, 0.0
            
            # Normalize to [-1, 1]
            audio_np = audio_np / 32768.0
            
            # Calculate RMS energy
            rms_energy = np.sqrt(np.mean(audio_np ** 2))
            
            # Calculate zero-crossing rate
            zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_np)))) / 2
            zcr = zero_crossings / len(audio_np) if len(audio_np) > 0 else 0
            
            # Combined confidence score
            energy_score = min(rms_energy * 3, 1.0)
            zcr_score = min(zcr * 50, 1.0)
            
            confidence = (energy_score * 0.7) + (zcr_score * 0.3)
            has_speech = confidence > self.vad_threshold
            
            # Track speech/silence frames for end-of-speech detection
            if has_speech:
                self.speech_frames += 1
                self.silence_frames = 0
            else:
                self.silence_frames += 1
            
            return has_speech, confidence
            
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False, 0.0
    
    def is_end_of_speech(self, silence_threshold: int = 10) -> bool:
        """Check if user has stopped speaking (based on consecutive silence frames)"""
        return self.speech_frames > 5 and self.silence_frames >= silence_threshold
    
    def reset(self):
        """Reset speech detection state"""
        self.speech_frames = 0
        self.silence_frames = 0
        self.audio_buffer = []
    
    def add_to_buffer(self, audio_data: bytes):
        """Add audio chunk to buffer"""
        self.audio_buffer.append(audio_data)
    
    def get_buffered_audio(self) -> bytes:
        """Get all buffered audio and clear buffer"""
        if not self.audio_buffer:
            return b''
        combined = b''.join(self.audio_buffer)
        return combined
    
    def pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM data to WAV format"""
        import struct
        
        # WAV header parameters
        num_channels = 1
        sample_width = 2  # 16-bit
        
        # Create WAV header
        data_size = len(pcm_data)
        file_size = data_size + 36
        
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            file_size,
            b'WAVE',
            b'fmt ',
            16,  # Subchunk1Size
            1,   # AudioFormat (PCM)
            num_channels,
            self.sample_rate,
            self.sample_rate * num_channels * sample_width,  # ByteRate
            num_channels * sample_width,  # BlockAlign
            sample_width * 8,  # BitsPerSample
            b'data',
            data_size
        )
        
        return header + pcm_data