import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { ChatMessageItem } from "./ChatMessageItem";
import type { Message } from "../types";

describe("ChatMessageItem", () => {
  it("renders user message correctly", () => {
    const userMsg: Message = {
      id: "msg-1",
      role: "user",
      content: "Can you help me solve this physics equation?",
    };

    render(<ChatMessageItem message={userMsg} />);
    expect(screen.getByText("Can you help me solve this physics equation?")).toBeInTheDocument();
  });

  it("renders AI message with audio listen action", () => {
    const aiMsg: Message = {
      id: "msg-2",
      role: "ai",
      content: "Sure! Let's break down Newton's second law.",
    };
    const onPlay = vi.fn();

    render(<ChatMessageItem message={aiMsg} onPlayAudio={onPlay} />);
    expect(screen.getByText("Sure! Let's break down Newton's second law.")).toBeInTheDocument();

    const listenBtn = screen.getByRole("button", { name: /listen/i });
    expect(listenBtn).toBeInTheDocument();
    fireEvent.click(listenBtn);
    expect(onPlay).toHaveBeenCalledWith("Sure! Let's break down Newton's second law.");
  });

  it("renders attached image snapshot when present", () => {
    const msgWithImage: Message = {
      id: "msg-3",
      role: "user",
      content: "What is this graph showing?",
      imageBase64: "base64encodedimagecontent",
    };

    render(<ChatMessageItem message={msgWithImage} />);
    const img = screen.getByRole("img", { name: /screen snapshot attached/i });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "data:image/jpeg;base64,base64encodedimagecontent");
  });
});
