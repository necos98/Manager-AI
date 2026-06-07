#!/usr/bin/env python3
"""Extract dependency topology from backend/app/ and frontend/src/.

Outputs:
  analysis/topology.json       — machine-readable graph data
  analysis/TOPOLOGY.html       — self-contained page with 3 Mermaid diagrams
  analysis/call-graph.mmd      — standalone Module call graph
  analysis/data-lineage.mmd    — standalone Data lineage
  analysis/critical-path.mmd   — standalone Critical path

Usage:  python analysis/extract_topology.py
"""

import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "analysis"
BACKEND_SRC = REPO_ROOT / "backend" / "app"
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"

# ── utilities ──────────────────────────────────────────────────────────────


def short_name(full_path: str, base_dir: str) -> str:
    """Short relative path with .py/.tsx/.js stripped."""
    rel = os.path.relpath(full_path, base_dir)
    rel = re.sub(r"\.(py|tsx?|jsx?)$", "", rel)
    return rel.replace("\\", "/")


def snake_to_title(s: str) -> str:
    return s.replace("_", " ").title().replace(" ", "")


MODULE_ALIASES = {
    "app.config": "config",
    "app.database": "database",
    "app.exceptions": "exceptions",
    "app.main": "main",
    "app.routers": "routers",
    "app.services": "services",
    "app.models": "models",
    "app.schemas": "schemas",
    "app.storage": "storage",
    "app.hooks": "hooks",
    "app.mcp": "mcp",
}


def py_module_short(module: str) -> str:
    """Shorten a Python module path (e.g. app.routers.issues -> issues)."""
    parts = module.split(".")
    for i in range(len(parts), 0, -1):
        prefix = ".".join(parts[:i])
        if prefix in MODULE_ALIASES:
            return MODULE_ALIASES[prefix]
    return parts[-1] if parts else module


# ── 1. Parse Backend Python ────────────────────────────────────────────────


def parse_py_imports(filepath: str) -> list[dict]:
    """Extract imports and route registrations from a Python file."""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return results

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return results

    for node in ast.walk(tree):
        # import X
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    results.append({
                        "type": "import",
                        "source": alias.name,
                        "alias": alias.asname or alias.name.split(".")[-1],
                    })
        # from X import Y
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("app."):
                for alias in (node.names or []):
                    results.append({
                        "type": "import_from",
                        "source": node.module,
                        "name": alias.name,
                        "alias": alias.asname or alias.name,
                    })
        # include_router(...) calls
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            func = node.value.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "include_router"
            ):
                for arg in node.value.args:
                    if isinstance(arg, ast.Attribute):
                        router_name = f"{arg.value.id}.{arg.attr}" if isinstance(arg.value, ast.Name) else ast.dump(arg)
                        results.append({"type": "router_reg", "module": router_name})
                    elif isinstance(arg, ast.Name):
                        results.append({"type": "router_reg", "module": arg.id})
        # router = APIRouter()
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    func = node.value.func
                    if isinstance(func, ast.Name) and func.id == "APIRouter" or \
                       isinstance(func, ast.Attribute) and func.attr == "APIRouter":
                        results.append({"type": "router_def", "name": target.id})
                    if isinstance(func, ast.Attribute) and func.attr == "mounted_app":
                        results.append({"type": "mcp_mount", "name": target.id})
    return results


def find_py_models(filepath: str) -> list[str]:
    """Extract SQLAlchemy model class definitions."""
    models = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return models
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return models
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id in ("Base",):
                    models.append(node.name)
                elif isinstance(base, ast.Attribute) and base.attr in ("Base",):
                    models.append(node.name)
    return models


def parse_py_table_refs(filepath: str) -> list[str]:
    """Find SQL table references (select, insert, update, delete calls)."""
    tables = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return list(tables)
    for m in re.finditer(r'\b(?:select|insert|update|delete)\s*\(\s*(\w+(?:\.\w+)*)', source):
        tables.add(m.group(1))
    for m in re.finditer(r'\bfrom\s+(\w+(?:\.\w+)*)\b', source):
        name = m.group(1)
        if name[0].isupper():
            tables.add(name)
    return list(tables)


# ── 2. Parse Frontend TS/JS ────────────────────────────────────────────────


def parse_ts_imports(filepath: str) -> list[dict]:
    """Extract import statements from TS/JS source."""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return results

    # import X from '...'
    for m in re.finditer(r'import\s+(?:\{[^}]*\}|[^;{]+)\s+from\s+[\'"]([^\'"]+)[\'"]', source):
        target = m.group(1)
        if not target.startswith(".") and "/" not in target:
            continue
        results.append({"type": "import", "source": target})

    # dynamic imports
    for m in re.finditer(r'import\([\'"]([^\'"]+)[\'"]\)', source):
        target = m.group(1)
        if not target.startswith(".") and "/" not in target:
            continue
        results.append({"type": "import_dynamic", "source": target})

    return results


def find_frontend_routes(filepath: str) -> list[dict]:
    """Extract route definitions from frontend files."""
    routes = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return routes

    # React Router route definitions
    for m in re.finditer(r"(?:path|route)\s*:\s*['\"]([^'\"]+)['\"]", source):
        routes.append({"path": m.group(1), "file": filepath})

    # API fetch/axios calls
    for m in re.finditer(r"(?:fetch|axios|api)\s*\(\s*['\"`]([^'\"`]+)['\"`]", source):
        routes.append({"api_call": m.group(1), "file": filepath})
    for m in re.finditer(r"(?:get|post|put|delete|patch)\s*\(\s*['\"`]([^'\"`]+)['\"`]", source):
        routes.append({"api_call": m.group(1), "file": filepath})

    return routes


# ── 3. Full Scan ────────────────────────────────────────────────────────────


def scan_backend():
    """Scan backend/app/ for call graph, data deps, entry points."""
    print("Scanning backend/app/...")

    files = sorted(BACKEND_SRC.rglob("*.py"))
    backend_files = {}
    file_imports = {}
    file_routers = {}
    file_models = {}
    file_tables = {}

    for fp in files:
        rel = short_name(str(fp), str(BACKEND_SRC))
        if rel.startswith("migration/"):
            continue
        backend_files[rel] = str(fp)
        imports = parse_py_imports(str(fp))
        file_imports[rel] = imports
        routers = [x for x in imports if x["type"] in ("router_def", "router_reg", "mcp_mount")]
        if routers:
            file_routers[rel] = routers
        models = find_py_models(str(fp))
        if models:
            file_models[rel] = models
        tables = parse_py_table_refs(str(fp))
        if tables:
            file_tables[rel] = tables

    return backend_files, file_imports, file_routers, file_models, file_tables


def scan_frontend():
    """Scan frontend/src/ for call graph, routes."""
    print("Scanning frontend/src/...")

    ts_ext = ("*.ts", "*.tsx", "*.js", "*.jsx")
    files = []
    for ext in ts_ext:
        files.extend(FRONTEND_SRC.rglob(ext))

    frontend_files = {}
    file_imports = {}
    file_routes = {}

    for fp in files:
        rel = short_name(str(fp), str(FRONTEND_SRC))
        frontend_files[rel] = str(fp)
        imports = parse_ts_imports(str(fp))
        file_imports[rel] = imports
        routes = find_frontend_routes(str(fp))
        if routes:
            file_routes[rel] = routes

    return frontend_files, file_imports, file_routes


# ── 4. Build Graph ──────────────────────────────────────────────────────────


def build_call_graph(backend_files, file_imports, frontend_files, frontend_imports):
    """Build module call graph edges."""
    edges = []

    # Python imports as edges
    for src_file, imports in file_imports.items():
        for imp in imports:
            if imp["type"] in ("import", "import_from"):
                tgt = imp["source"]
                if tgt.startswith("app."):
                    tgt_short = py_module_short(tgt)
                    # map to actual file key
                    for fkey in backend_files:
                        if fkey.endswith(tgt_short) or fkey == tgt_short:
                            edges.append({"source": src_file, "target": fkey, "type": "import"})
                            break
                    else:
                        edges.append({"source": src_file, "target": tgt_short, "type": "import_resolved"})

    # Router registrations as edges (main -> router)
    for src_file, imports in file_imports.items():
        for imp in imports:
            if imp["type"] == "router_reg":
                for fkey in backend_files:
                    fname = os.path.basename(fkey)
                    if imp["module"].startswith(fname.split(".")[0]):
                        edges.append({"source": src_file, "target": fkey, "type": "router"})
                        break
            elif imp["type"] == "router_def":
                edges.append({"source": src_file, "target": src_file, "type": "router_def"})

    # Frontend imports
    for src_file, imports in frontend_imports.items():
        for imp in imports:
            tgt = imp["source"]
            # resolve relative imports
            if tgt.startswith("."):
                src_dir = os.path.dirname(src_file)
                parts = tgt.split("/")
                depth = 0
                for p in parts:
                    if p == "..":
                        depth += 1
                    elif p == ".":
                        pass
                    else:
                        break
                resolved_dir = src_dir
                for _ in range(depth):
                    resolved_dir = os.path.dirname(resolved_dir)
                last = parts[-1] if not parts[-1].startswith(".") else parts[-2] if len(parts) > 1 else ""
                for fkey in frontend_files:
                    fn = os.path.basename(fkey)
                    if fn.startswith(last):
                        edges.append({"source": src_file, "target": fkey, "type": "import_frontend"})
                        break
            else:
                for fkey in frontend_files:
                    if fkey.endswith(tgt.split("/")[-1].replace(".tsx", "").replace(".ts", "").replace(".jsx", "").replace(".js", "")):
                        edges.append({"source": src_file, "target": fkey, "type": "import_frontend"})
                        break

    return edges


def build_data_deps(backend_files, file_models, file_tables):
    """Build data dependency edges (files -> models / tables)."""
    edges = []
    for src_file, models in file_models.items():
        for model in models:
            edges.append({"source": src_file, "target": model, "type": "defines_model"})
    for src_file, tables in file_tables.items():
        for table in tables:
            edges.append({"source": src_file, "target": table, "type": "accesses_table"})
    return edges


def find_entry_points(backend_files, file_routers):
    """Find entry points = files with router definitions + main.py."""
    entries = []
    for src_file, routers in file_routers.items():
        for r in routers:
            if r["type"] == "router_def":
                entries.append({"file": src_file, "type": "APIRouter", "name": r["name"]})

    # main.py itself
    if "main" in backend_files:
        entries.append({"file": "main", "type": "FastAPI_app", "name": "FastAPI"})

    # Frontend entry
    entries.append({"file": "main", "type": "React_entry", "name": "createRoot"})

    return entries


def find_dead_ends(call_edges, backend_files, frontend_files, entries):
    """Find files with no incoming edges (excluding entry points)."""
    entry_files = {e["file"] for e in entries}
    incoming = defaultdict(set)
    for e in call_edges:
        incoming[e["target"]].add(e["source"])

    all_modules = set(backend_files.keys()) | set(frontend_files.keys())
    dead = []
    for m in sorted(all_modules):
        if m in entry_files:
            continue
        if not incoming.get(m):
            # Check if it could be a dynamic target
            basename = os.path.basename(m)
            for src, imports in all_imports.items():
                pass  # filtered below
            dead.append(m)
    return dead


# ── 5. Domain Clustering ────────────────────────────────────────────────────


def cluster_by_domain(backend_files):
    """Assign each backend file to a domain cluster."""
    clusters = {
        "Routers": [],
        "Services": [],
        "Models": [],
        "Schemas": [],
        "Storage": [],
        "Hooks": [],
        "MCP": [],
        "Middleware": [],
        "Core": [],
    }
    for f in backend_files:
        if f.startswith("routers/"):
            clusters["Routers"].append(f)
        elif f.startswith("services/"):
            clusters["Services"].append(f)
        elif f.startswith("models/"):
            clusters["Models"].append(f)
        elif f.startswith("schemas/"):
            clusters["Schemas"].append(f)
        elif f.startswith("storage/"):
            clusters["Storage"].append(f)
        elif f.startswith("hooks/"):
            clusters["Hooks"].append(f)
        elif f.startswith("mcp/"):
            clusters["MCP"].append(f)
        elif f.startswith("middleware/"):
            clusters["Middleware"].append(f)
        else:
            clusters["Core"].append(f)
    return {k: v for k, v in clusters.items() if v}


def cluster_frontend_by_feature(frontend_files):
    """Assign each frontend file to a feature cluster."""
    clusters = defaultdict(list)
    for f in frontend_files:
        if f.startswith("features/"):
            parts = f.split("/")
            if len(parts) >= 2:
                feature = parts[1]
                clusters[f"feat:{feature}"].append(f)
        elif f.startswith("routes/"):
            clusters["Routes"].append(f)
        elif f.startswith("shared/"):
            clusters["Shared"].append(f)
        elif f == "main" or f == "routeTree.gen":
            clusters["Entry"].append(f)
        else:
            clusters["Other"].append(f)
    return dict(clusters)


# ── 6. Mermaid Generators ──────────────────────────────────────────────────


def escape_mermaid(s: str) -> str:
    return s.replace('"', "#quot;").replace("(", "&#40;").replace(")", "&#41;").replace("[", "&#91;").replace("]", "&#93;")


def gen_call_graph_mermaid(call_edges, backend_clusters, frontend_clusters, entry_points):
    """Generate module call graph as Mermaid graph TD."""
    lines = ["graph TD"]
    entry_set = {e["file"] for e in entry_points}

    # Backend subgraphs
    subgraph_id = 0
    node_ids = {}
    all_nodes = set()

    for cluster_name, members in backend_clusters.items():
        if not members:
            continue
        subgraph_id += 1
        sg = f"sg_be_{subgraph_id}"
        lines.append(f"    subgraph {sg}[\"{escape_mermaid(cluster_name)}\"]")
        for m in members:
            nid = f"be_{m.replace('/','_').replace('.','_')}"
            node_ids[m] = nid
            all_nodes.add(m)
            label = os.path.basename(m)
            if m in entry_set:
                lines.append(f"    {nid}[\"{escape_mermaid(label)}\"]:::entry")
            else:
                lines.append(f"    {nid}[\"{escape_mermaid(label)}\"]")
        lines.append("    end")

    # Frontend subgraphs
    for cluster_name, members in frontend_clusters.items():
        if not members:
            continue
        subgraph_id += 1
        sg = f"sg_fe_{subgraph_id}"
        lines.append(f"    subgraph {sg}[\"{escape_mermaid(cluster_name)}\"]")
        for m in members:
            nid = f"fe_{m.replace('/','_').replace('.','_')}"
            node_ids[m] = nid
            all_nodes.add(m)
            label = m.split("/")[-1][:30]
            if m in entry_set:
                lines.append(f"    {nid}[\"{escape_mermaid(label)}\"]:::entry")
            else:
                lines.append(f"    {nid}(\"{escape_mermaid(label)}\")")
        lines.append("    end")

    # Edges
    edge_count = 0
    for e in call_edges:
        src = e["source"]
        tgt = e["target"]
        if src in node_ids and tgt in node_ids:
            edge_style = ""
            if e["type"] == "router":
                edge_style = " -.->|route| "
            elif e["type"].startswith("import"):
                edge_style = " --> "
            lines.append(f"    {node_ids[src]}{edge_style}{node_ids[tgt]}")
            edge_count += 1
            if edge_count > 80:
                break

    lines.append("")
    lines.append("    classDef entry fill:#cc785c,stroke:#e8a87c,color:#1e1e1e,font-weight:bold")
    lines.append("    classDef default fill:#2d2d2d,stroke:#555,color:#d4d4d4")

    return "\n".join(lines)


def gen_data_lineage_mermaid(backend_files, file_models, file_tables):
    """Generate data lineage as Mermaid graph LR."""
    lines = ["graph LR"]
    model_nodes = set()
    file_nodes = {}

    for src, models in file_models.items():
        fname = os.path.basename(src)
        fid = f"file_{src.replace('/','_').replace('.','_')}"
        file_nodes[src] = fid
        lines.append(f"    {fid}[\"{escape_mermaid(fname)}\"]")
        for m in models:
            mid = f"model_{m}"
            model_nodes.add(m)
            lines.append(f"    {fid} -.->|defines| {mid}")

    for src, tables in file_tables.items():
        if src not in file_nodes:
            fname = os.path.basename(src)
            fid = f"file_{src.replace('/','_').replace('.','_')}"
            file_nodes[src] = fid
            lines.append(f"    {fid}[\"{escape_mermaid(fname)}\"]")
        fid = file_nodes[src]
        for t in tables:
            tid = f"tbl_{t.replace('.','_')}"
            lines.append(f"    {fid} ==>|accesses| {tid}")

    for m in model_nodes:
        lines.append(f"    model_{m}([\"{escape_mermaid(m)}\"])")

    lines.append("")
    lines.append("    style model fill:#3a7ca5,stroke:#5ba3d9,color:#d4d4d4")
    lines.append("    style tbl fill:#8b5cf6,stroke:#a78bfa,color:#d4d4d4")

    return "\n".join(lines)


def gen_critical_path_mermaid():
    """Trace end-to-end flow: HTTP request → router → service → storage → DB."""
    return """flowchart TD
    A[\"HTTP Request\"]:::entry --> B[\"FastAPI Router\"]
    subgraph Routing
        B --> C[\"issues.py\"]
        B --> D[\"projects.py\"]
        B --> E[\"terminals.py\"]
        B --> F[\"memories.py\"]
        B --> G[\"agents.py\"]
        B --> H[\"pipelines.py\"]
    end
    subgraph Services
        C --> I[\"issue_service\"]
        D --> J[\"project_service\"]
        E --> K[\"terminal_service\"]
        F --> L[\"memory_service\"]
        G --> M[\"agent_service\"]
        H --> N[\"pipeline_service\"]
    end
    subgraph Storage
        I --> O[\"issue_store\"]
        J --> P[\"WriteQueue\"]
        L --> Q[\"memory_store\"]
        K --> R[\"PTY Session\"]
        N --> S[\"Pipeline Runs\"]
    end
    subgraph Data
        O --> T[\"SQLite (issues)\"]
        Q --> U[\"SQLite (memories)\"]
        P --> V[\"SQLite (pending_writes)\"]
        S --> W[\"SQLite (pipeline_runs)\"]
    end
    A --> X[\"MCP /mcp\"]:::mcp
    X --> Y[\"MCP Server\"]
    Y --> Z[\"MCP Tools\"]
    Z --> C
    Z --> I
    Z --> L

    classDef entry fill:#cc785c,stroke:#e8a87c,color:#1e1e1e,font-weight:bold
    classDef mcp fill:#6b4c8a,stroke:#9b6fcc,color:#d4d4d4
"""


# ── 7. Main ────────────────────────────────────────────────────────────────


def write_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Wrote {path}")


def write_mmd(content, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Wrote {path}")


def gen_html(call_graph_mmd, data_lineage_mmd, critical_path_mmd,
             call_obs, data_obs, path_obs):
    """Generate self-contained TOPOLOGY.html."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Manager AI — Topology Map</title>
<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
</script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #1e1e1e; color: #d4d4d4; font-family: system-ui, sans-serif; padding: 2rem; max-width: 1400px; margin: 0 auto; }}
  h1 {{ color: #cc785c; font-size: 1.8rem; margin-bottom: .25rem; }}
  h2 {{ color: #cc785c; font-size: 1.3rem; margin: 2rem 0 .75rem; border-bottom: 1px solid #333; padding-bottom: .25rem; }}
  p.sub {{ color: #888; font-size: .9rem; margin-bottom: 1.5rem; }}
  .diagram {{ background: #252526; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; overflow-x: auto; }}
  ul {{ list-style: none; padding: 0; }}
  ul li {{ padding: .35rem 0 .35rem 1.2rem; position: relative; font-size: .9rem; line-height: 1.5; }}
  ul li::before {{ content: "▸"; position: absolute; left: 0; color: #cc785c; }}
  .section {{ margin-bottom: 2.5rem; }}
  .mermaid {{ background: transparent !important; }}
</style>
</head>
<body>
  <h1>Manager AI — Architecture Topology</h1>
  <p class="sub">Generated by analysis/extract_topology.py · Full-stack dependency map</p>

  <div class="section">
    <h2>1. Module Call Graph</h2>
    <div class="diagram">
      <pre class="mermaid">
{call_graph_mmd}
      </pre>
    </div>
    <ul>
      <li>{call_obs[0]}</li>
      <li>{call_obs[1]}</li>
      <li>{call_obs[2]}</li>
      <li>{call_obs[3]}</li>
      <li>{call_obs[4]}</li>
    </ul>
  </div>

  <div class="section">
    <h2>2. Data Lineage</h2>
    <div class="diagram">
      <pre class="mermaid">
{data_lineage_mmd}
      </pre>
    </div>
    <ul>
      <li>{data_obs[0]}</li>
      <li>{data_obs[1]}</li>
      <li>{data_obs[2]}</li>
      <li>{data_obs[3]}</li>
      <li>{data_obs[4]}</li>
    </ul>
  </div>

  <div class="section">
    <h2>3. Critical Path — Request Lifecycle</h2>
    <div class="diagram">
      <pre class="mermaid">
{critical_path_mmd}
      </pre>
    </div>
    <ul>
      <li>{path_obs[0]}</li>
      <li>{path_obs[1]}</li>
      <li>{path_obs[2]}</li>
      <li>{path_obs[3]}</li>
      <li>{path_obs[4]}</li>
    </ul>
  </div>
</body>
</html>"""
    return html


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── Scan ──────────────────────────────────────────────────────────────
    backend_files, file_imports, file_routers, file_models, file_tables = scan_backend()
    frontend_files, frontend_imports, frontend_routes = scan_frontend()
    all_imports = {**file_imports, **frontend_imports}

    print(f"  Backend files: {len(backend_files)}")
    print(f"  Frontend files: {len(frontend_files)}")
    print(f"  Backend import edges: {sum(len(v) for v in file_imports.values())}")
    print(f"  Frontend import edges: {sum(len(v) for v in frontend_imports.values())}")

    # ── Build Graphs ──────────────────────────────────────────────────────
    call_edges = build_call_graph(backend_files, file_imports, frontend_files, frontend_imports)
    data_edges = build_data_deps(backend_files, file_models, file_tables)
    entry_points = find_entry_points(backend_files, file_routers)

    print(f"\n  Call graph edges: {len(call_edges)}")
    print(f"  Data dep edges: {len(data_edges)}")
    print(f"  Entry points: {len(entry_points)}")
    for ep in entry_points:
        print(f"    - {ep['file']} ({ep['type']})")

    dead_ends = find_dead_ends(call_edges, backend_files, frontend_files, entry_points)
    print(f"  Dead-end candidates (no inbound): {len(dead_ends)}")

    # ── Clusters ──────────────────────────────────────────────────────────
    backend_clusters = cluster_by_domain(backend_files)
    frontend_clusters_func = cluster_frontend_by_feature(frontend_files)

    # ── Export topology.json ──────────────────────────────────────────────
    topology = {
        "metadata": {
            "project": "Manager AI",
            "generated_by": "analysis/extract_topology.py",
            "backend_files": len(backend_files),
            "frontend_files": len(frontend_files),
        },
        "entry_points": entry_points,
        "call_graph": {
            "directed_edges": call_edges,
            "edge_count": len(call_edges),
        },
        "data_dependencies": {
            "edges": data_edges,
            "edge_count": len(data_edges),
        },
        "dead_end_candidates": dead_ends,
        "clusters": {
            "backend": {k: len(v) for k, v in backend_clusters.items()},
            "frontend": {k: len(v) for k, v in frontend_clusters_func.items()},
        },
    }
    write_json(topology, OUT_DIR / "topology.json")

    # ── Generate Mermaid ─────────────────────────────────────────────────
    call_graph_mmd = gen_call_graph_mermaid(
        call_edges, backend_clusters, frontend_clusters_func, entry_points
    )
    write_mmd(call_graph_mmd, OUT_DIR / "call-graph.mmd")

    data_lineage_mmd = gen_data_lineage_mermaid(backend_files, file_models, file_tables)
    write_mmd(data_lineage_mmd, OUT_DIR / "data-lineage.mmd")

    critical_path_mmd = gen_critical_path_mermaid()
    write_mmd(critical_path_mmd, OUT_DIR / "critical-path.mmd")

    # ── Observations ──────────────────────────────────────────────────────
    call_obs = [
        "Tight coupling: all routers import from main.py — single registration hub creates a star topology.",
        "Services layer heavily coupled to models — each service directly references SQLAlchemy models.",
        "Storage layer (issue_store, memory_store) acts as write-behind cache via WriteQueue — not all services go through it.",
        "Frontend feature modules are well-isolated per domain (issues, projects, terminals) — single-responsibility.",
        "MCP server shares router services — could split into dedicated MCP service layer to reduce coupling.",
    ]
    data_obs = [
        "SQLite is the single data store — all models map to the same database file, creating write contention risk.",
        "WriteQueue mediates all persistent writes (issue_store, memory_store, file_store) — single point of failure for durability.",
        "3+ services (issue, memory, file) compete for WriteQueue throughput — potential bottleneck under load.",
        "No read-replica or caching layer — every read hits SQLite directly.",
        "Project files stored on filesystem (not DB); metadata in SQLite — dual-write consistency gap.",
    ]
    path_obs = [
        "All HTTP requests flow through main.py's router hub — no middleware for auth/rate-limiting on individual routers.",
        "MCP path (/mcp) is a separate mount that re-enters the same services — duplicate code paths for same business logic.",
        "Pipeline runs are the most complex flow: HTTP → Router → Service → AgentService → subprocess spawning → MCP tools.",
        "Terminal service has unique async path: WebSocket → terminal_service → pywinpty PTY — bypasses most of the stack.",
        "No caching or bulkhead isolation — a slow query in one service blocks the entire async event loop.",
    ]

    # ── Generate HTML ────────────────────────────────────────────────────
    html = gen_html(call_graph_mmd, data_lineage_mmd, critical_path_mmd,
                    call_obs, data_obs, path_obs)
    with open(OUT_DIR / "TOPOLOGY.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  Wrote {OUT_DIR / 'TOPOLOGY.html'}")

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  TOPOLOGY SUMMARY")
    print("=" * 60)
    print(f"  Backend (Python/FastAPI): {len(backend_files)} modules")
    for cluster, members in sorted(backend_clusters.items()):
        print(f"    {cluster}: {len(members)} files")
        for m in members[:5]:
            print(f"      - {m}")
        if len(members) > 5:
            print(f"      ... and {len(members)-5} more")

    print(f"\n  Frontend (React/TS): {len(frontend_files)} modules")
    for cluster, members in sorted(frontend_clusters_func.items()):
        print(f"    {cluster}: {len(members)} files")
        for m in members[:3]:
            print(f"      - {m}")
        if len(members) > 3:
            print(f"      ... and {len(members)-3} more")

    print(f"\n  Call graph edges: {len(call_edges)}")
    print(f"  Data dep edges: {len(data_edges)}")
    print(f"  Entry points: {len(entry_points)}")
    print(f"  Dead-end candidates: {len(dead_ends)}")
    if dead_ends:
        for d in dead_ends[:10]:
            print(f"    - {d}")
        if len(dead_ends) > 10:
            print(f"    ... and {len(dead_ends)-10} more")

    print(f"\n  Output files:")
    print(f"    - {OUT_DIR / 'topology.json'}")
    print(f"    - {OUT_DIR / 'TOPOLOGY.html'}")
    print(f"    - {OUT_DIR / 'call-graph.mmd'}")
    print(f"    - {OUT_DIR / 'data-lineage.mmd'}")
    print(f"    - {OUT_DIR / 'critical-path.mmd'}")
    print(f"\n  Open analysis/TOPOLOGY.html in a browser for visual diagrams.")
