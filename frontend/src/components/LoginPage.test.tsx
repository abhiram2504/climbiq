import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LoginPage } from "./LoginPage";

describe("LoginPage", () => {
  it("links to the server-side Google sign-in flow when configured", () => {
    render(<LoginPage configured />);

    expect(screen.getByRole("link", { name: /continue with google/i })).toHaveAttribute(
      "href",
      "/api/auth/google/login",
    );
    expect(screen.getByText(/imported without sharing provider passwords/i)).toBeInTheDocument();
  });

  it("shows setup guidance when Google OAuth is not configured", () => {
    render(<LoginPage configured={false} />);

    expect(screen.getByText(/needs server credentials/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continue with google/i })).toBeDisabled();
  });

  it("offers a retry when the API cannot be reached", () => {
    render(<LoginPage configured={false} serverUnavailable error="Request failed" />);

    expect(screen.getByRole("heading", { name: /workspace unavailable/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    expect(screen.queryByText(/needs server credentials/i)).not.toBeInTheDocument();
  });
});
