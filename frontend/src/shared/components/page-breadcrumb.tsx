import { useLocation, Link } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { useIssue } from "@/features/issues/hooks";
import { cn } from "@/shared/lib/utils";
import { Fragment } from "react";

/**
 * Static labels for known route segments (non-dynamic).
 */
const SEGMENT_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  issues: "Issues",
  pipelines: "Pipelines",
  plugins: "Plugins",
  memories: "Memories",
  files: "Uploaded Files",
  commands: "Commands",
  variables: "Variables",
  activity: "Activity",
  health: "Health",
  ask: "Ask AI",
  library: "Library",
  new: "New Project",
  archived: "Archived",
  queue: "Issue Queue",
  settings: "Settings",
  providers: "Providers",
  agents: "Agents",
  terminals: "Terminals",
  questions: "Questions",
};

/**
 * Segments whose URL path parts are NOT rendered as breadcrumb items.
 * They are structural (e.g. "projects" is always followed by an ID).
 */
const STRUCTURAL_PARTS = new Set(["projects"]);

/**
 * Matches UUID-like or hash-like segment values (project IDs, issue IDs).
 */
function isIdLike(s: string): boolean {
  return /^[0-9a-f]{8,}(-[0-9a-f]{4,}){3,}/i.test(s) || s.length >= 20;
}

/**
 * Capitalise the first letter of a string.
 */
function capitalise(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1);
}

interface CrumbSegment {
  /** Human-readable label. */
  label: string;
  /** Route path this segment links to. */
  href: string;
  /** Whether this is the last (current-page) segment. */
  isLast: boolean;
}

export function PageBreadcrumb() {
  const { pathname } = useLocation();

  // Don't render on the root projects page (no meaningful breadcrumb there)
  if (pathname === "/") return null;

  const rawParts = pathname.split("/").filter(Boolean);

  // Extract dynamic IDs from the path
  let projectId: string | null = null;
  let issueId: string | null = null;
  for (let i = 0; i < rawParts.length; i++) {
    if (rawParts[i] === "projects" && i + 1 < rawParts.length) {
      projectId = rawParts[i + 1];
    }
    if (rawParts[i] === "issues" && i + 1 < rawParts.length) {
      issueId = rawParts[i + 1];
    }
  }

  // Fetch dynamic names when we have IDs
  const { data: project, isLoading: projectLoading } = useProject(projectId ?? "");
  const { data: issue, isLoading: issueLoading } = useIssue(
    projectId ?? "",
    issueId ?? "",
  );

  // Build the breadcrumb segments by walking the path parts
  const segments: CrumbSegment[] = [];
  let accumulated = "";

  for (let i = 0; i < rawParts.length; i++) {
    const part = rawParts[i];
    const prevPart = i > 0 ? rawParts[i - 1] : null;

    // Skip structural URL parts (e.g. "projects")
    if (STRUCTURAL_PARTS.has(part)) continue;

    // Accumulate the href
    if (accumulated === "") {
      accumulated = "/" + part;
    } else {
      accumulated += "/" + part;
    }

    // Determine the human label for this segment
    let label: string;

    if (isIdLike(part)) {
      // Dynamic resource ID — resolve via hooks
      if (prevPart === "issues" && issueId === part) {
        if (issueLoading) label = "...";
        else label = issue?.name ?? issue?.description?.slice(0, 60) ?? part.slice(0, 8);
      } else {
        // project ID
        if (projectLoading) label = "...";
        else label = project?.name ?? part.slice(0, 8);
      }
    } else if (SEGMENT_LABELS[part] !== undefined) {
      label = SEGMENT_LABELS[part];
    } else {
      label = capitalise(part.replace(/[-_]/g, " "));
    }

    segments.push({
      label,
      href: accumulated,
      isLast: i === rawParts.length - 1 || (i + 1 < rawParts.length && STRUCTURAL_PARTS.has(rawParts[i + 1]) && i + 1 === rawParts.length - 1),
    });
  }

  // Re-evaluate isLast — the last segment in the array is the current page
  if (segments.length > 0) {
    segments[segments.length - 1].isLast = true;
    // All others are NOT last
    for (let i = 0; i < segments.length - 1; i++) {
      segments[i].isLast = false;
    }
  }

  if (segments.length === 0) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className="hidden md:flex items-center gap-1 px-6 py-2 text-sm border-b bg-background/50 overflow-hidden"
    >
      {/* Root: always Projects */}
      <Link
        to="/"
        className="text-muted-foreground hover:text-foreground transition-colors shrink-0"
      >
        Projects
      </Link>

      {segments.map((seg, idx) => (
        <Fragment key={seg.href}>
          <span className="text-muted-foreground/40 shrink-0 select-none" aria-hidden="true">
            /
          </span>
          {seg.isLast ? (
            <span
              className={cn(
                "font-semibold text-foreground truncate max-w-[240px]",
              )}
              aria-current="page"
            >
              {seg.label}
            </span>
          ) : (
            <Link
              to={seg.href}
              className="text-muted-foreground hover:text-foreground transition-colors truncate max-w-[200px] shrink min-w-0"
            >
              {seg.label}
            </Link>
          )}
        </Fragment>
      ))}
    </nav>
  );
}
