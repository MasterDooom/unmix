import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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
        ],
      },
    });

    fireEvent.click(
      screen.getByRole("button", { name: /set up mix lab/i }),
    );

    const matrixInput = screen.getByLabelText(
      "Mixing matrix JSON",
    ) as HTMLTextAreaElement;

    expect(matrixInput.value).toContain("[");
    expect(
      screen.getByRole("button", { name: /run ica recovery/i }),
    ).toBeEnabled();
  });
});