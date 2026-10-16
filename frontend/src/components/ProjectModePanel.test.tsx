import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ClimbingProject } from "../types/api";
import { ProjectModePanel } from "./ProjectModePanel";

const project: ClimbingProject = {
  id: "project-1",
  status: "active",
  demand_tags: ["crimp", "power endurance"],
  notes: "Link the upper crux.",
  created_at: "2026-10-15T12:00:00Z",
  updated_at: "2026-10-15T12:00:00Z",
  target_climb: {
    id: "climb-1",
    source: "manual",
    discipline: "outdoor",
    external_id: null,
    name: "The Long Game",
    grade: "5.12a",
    grade_system: "YDS",
    location: "Red River Gorge",
    route_type: "Sport",
    external_url: null,
    pitches: null,
    length_ft: null,
    board_name: null,
    board_angle: null,
    setter: null,
    is_benchmark: false,
  },
  drills: [],
  outdoor_attempts: 2,
  board_sessions: 3,
  drill_sends: 0,
  momentum_score: 60,
  next_action: "Add a MoonBoard problem that rehearses this route's crux demand.",
  last_activity: "2026-10-15",
};

const handlers = {
  onCreate: vi.fn(),
  onAddDrill: vi.fn(),
  onStatus: vi.fn(),
};

describe("ProjectModePanel", () => {
  it("shows the outdoor target and training signal", () => {
    render(<ProjectModePanel projects={[project]} loading={false} error={null} {...handlers} />);

    expect(screen.getByRole("heading", { name: "The Long Game" })).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(screen.getByText(/add a moonboard problem/i)).toBeInTheDocument();
  });

  it("opens project creation when there are no projects", () => {
    render(<ProjectModePanel projects={[]} loading={false} error={null} {...handlers} />);

    expect(screen.getByLabelText("Outdoor route")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create project/i })).toBeInTheDocument();
  });
});
