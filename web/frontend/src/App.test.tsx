import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

describe("Unmix workspace", () => {
  it("renders Track Lab and exposes a variable-source Mix Lab workflow", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: /see inside the mix/i }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(/pretrained stem estimation/i),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getAllByRole("button", { name: /mix lab/i })[0],
    );

    const sourceInput = screen.getByLabelText("Source files");

    fireEvent.change(sourceInput, {
      target: {
        files: [
          new File(["a"], "one.wav", { type: "audio/wav" }),
          new File(["b"], "two.wav", { type: "audio/wav" }),
          new File(["c"], "three.wav", { type: "audio/wav" }),
        ],
      },
    });

    fireEvent.click(
      screen.getByRole("button", { name: /set up mix lab/i }),
    );

    const matrixInput = screen.getByLabelText(
      "Mixing matrix JSON",
    ) as HTMLTextAreaElement;

    const matrix = JSON.parse(matrixInput.value) as number[][];
    expect(matrix).toHaveLength(3);
    expect(matrix.every((row) => row.length === 3)).toBe(true);
    expect(matrix[0]).toEqual([1, 0.35, 0.35]);
    expect(
      screen.getByRole("button", { name: /run ica recovery/i }),
    ).toBeEnabled();
  });

  it("disables Track Lab uploads when health reports that the hosted model runtime is missing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        api_contract_version: 2,
        track_lab_optional: true,
        track_lab_dependencies_installed: false,
        ffmpeg_available: true,
      }),
    }));
    try {
      render(<App />);
      expect(await screen.findByText(/this api does not have the optional pretrained model runtime installed/i)).toBeInTheDocument();
      expect(screen.getByLabelText("Track file")).toBeDisabled();
      expect(screen.getByRole("button", { name: /estimate stems/i })).toBeDisabled();
    } finally {
      cleanup();
      vi.unstubAllGlobals();
    }
  });

  it("explains how to start the API when a Track Lab upload cannot connect", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    try {
      render(<App />);
      fireEvent.change(screen.getByLabelText("Track file"), {
        target: { files: [new File(["audio"], "song.wav", { type: "audio/wav" })] },
      });
      fireEvent.click(screen.getByRole("button", { name: /estimate stems/i }));
      expect(await screen.findByRole("alert")).toHaveTextContent(/start the backend and frontend/i);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
