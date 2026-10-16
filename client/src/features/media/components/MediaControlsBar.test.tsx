import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { MediaControlsBar } from "./MediaControlsBar";

describe("MediaControlsBar", () => {
  it("renders buttons and triggers callbacks when clicked", () => {
    const onToggleCam = vi.fn();
    const onToggleAudio = vi.fn();
    const onToggleScreen = vi.fn();
    const onEndSession = vi.fn();

    render(
      <MediaControlsBar
        camOn={false}
        audioOn={true}
        screenOn={false}
        onToggleCam={onToggleCam}
        onToggleAudio={onToggleAudio}
        onToggleScreen={onToggleScreen}
        onEndSession={onEndSession}
      />
    );

    const camBtn = screen.getByTitle("Turn on camera");
    fireEvent.click(camBtn);
    expect(onToggleCam).toHaveBeenCalledTimes(1);

    const audioBtn = screen.getByTitle("Mute audio response");
    fireEvent.click(audioBtn);
    expect(onToggleAudio).toHaveBeenCalledTimes(1);

    const endBtn = screen.getByRole("button", { name: /end session/i });
    fireEvent.click(endBtn);
    expect(onEndSession).toHaveBeenCalledTimes(1);
  });
});
