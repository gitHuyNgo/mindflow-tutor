/**
 * Capture a JPEG frame from a MediaStream by mounting a temporary
 * full-size video element (not the hidden 1×1 one) and waiting for
 * the first decoded frame before drawing.
 *
 * Returns base64-encoded JPEG string, or null if stream is unavailable.
 */
export async function captureScreenFrame(
  stream: MediaStream,
  quality = 0.7,
): Promise<string | null> {
  return new Promise((resolve) => {
    const track = stream.getVideoTracks()[0];
    if (!track || track.readyState !== "live") {
      resolve(null);
      return;
    }

    const settings = track.getSettings();
    const w = settings.width  ?? 1280;
    const h = settings.height ?? 720;

    // Temporary video — off-screen but correctly sized so browser decodes it
    const video = document.createElement("video");
    video.srcObject = stream;
    video.muted     = true;
    video.playsInline = true;
    video.width  = w;
    video.height = h;
    // Position off-screen (not display:none — that blocks decoding)
    video.style.cssText = "position:fixed;top:-9999px;left:-9999px;width:1px;height:1px;pointer-events:none;";
    document.body.appendChild(video);

    const cleanup = () => {
      video.pause();
      video.srcObject = null;
      document.body.removeChild(video);
    };

    const draw = () => {
      if (video.videoWidth === 0) {
        cleanup();
        resolve(null);
        return;
      }
      const canvas = document.createElement("canvas");
      canvas.width  = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d")!.drawImage(video, 0, 0);
      const base64 = canvas.toDataURL("image/jpeg", quality).split(",")[1];
      cleanup();
      resolve(base64);
    };

    // Use requestVideoFrameCallback if available, else fall back to canplay
    if ("requestVideoFrameCallback" in video) {
      video.play().catch(() => {});
      (video as any).requestVideoFrameCallback(draw);
    } else {
      video.oncanplay = () => {
        video.play()
          .then(draw)
          .catch(() => { cleanup(); resolve(null); });
      };
      video.play().catch(() => { cleanup(); resolve(null); });
    }

    // Timeout safety — 3 s
    setTimeout(() => { cleanup(); resolve(null); }, 3000);
  });
}
