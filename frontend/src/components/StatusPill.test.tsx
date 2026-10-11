import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusPill } from "./StatusPill";

describe("StatusPill", () => {
  it("translates the uploaded state into a user-facing label", () => {
    render(<StatusPill status="uploaded" />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });
});
