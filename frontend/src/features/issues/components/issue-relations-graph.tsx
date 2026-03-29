import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  NodeMouseHandler,
  useNodesState,
  useEdgesState,
} from "reactflow";
import dagre from "@dagrejs/dagre";
import "reactflow/dist/style.css";
import type { Issue, IssueRelation } from "@/shared/types";

const NODE_WIDTH = 180;
const NODE_HEIGHT = 60;

function getLayoutedElements(nodes: Node[], edges: Edge[]) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 70, ranksep: 60 });
  nodes.forEach((node) => g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((edge) => g.setEdge(edge.source, edge.target));
  dagre.layout(g);
  return {
    nodes: nodes.map((node) => {
      const pos = g.node(node.id);
      return { ...node, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 } };
    }),
    edges,
  };
}

interface Props {
  currentIssue: Issue;
  relations: IssueRelation[];
  allIssues: Issue[];
  onNavigate: (issueId: string) => void;
}

export function IssueRelationsGraph({ currentIssue, relations, allIssues, onNavigate }: Props) {
  const issueMap = useMemo(() => new Map(allIssues.map((i) => [i.id, i])), [allIssues]);

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const nodeIds = new Set<string>([currentIssue.id]);
    relations.forEach((r) => { nodeIds.add(r.source_id); nodeIds.add(r.target_id); });

    const rawNodes: Node[] = Array.from(nodeIds).map((id) => {
      const issue = issueMap.get(id);
      const isCurrent = id === currentIssue.id;
      return {
        id,
        position: { x: 0, y: 0 },
        data: { label: issue?.name || issue?.description?.slice(0, 30) || id },
        style: {
          background: isCurrent ? "hsl(var(--primary))" : "hsl(var(--card))",
          color: isCurrent ? "hsl(var(--primary-foreground))" : "hsl(var(--foreground))",
          border: "1px solid hsl(var(--border))",
          borderRadius: 8,
          fontSize: 12,
          width: NODE_WIDTH,
          cursor: isCurrent ? "default" : "pointer",
        },
      };
    });

    const rawEdges: Edge[] = relations.map((r) => ({
      id: String(r.id),
      source: r.source_id,
      target: r.target_id,
      animated: r.relation_type === "blocks",
      style: { stroke: r.relation_type === "blocks" ? "hsl(var(--destructive))" : "hsl(var(--muted-foreground))" },
      markerEnd: r.relation_type === "blocks" ? { type: "arrowclosed" as any } : undefined,
    }));

    return getLayoutedElements(rawNodes, rawEdges);
  }, [currentIssue, relations, issueMap]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick: NodeMouseHandler = useCallback((_, node) => {
    if (node.id !== currentIssue.id) onNavigate(node.id);
  }, [currentIssue.id, onNavigate]);

  if (relations.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">Nessuna relazione. Aggiungine una qui sotto.</p>;
  }

  return (
    <div style={{ height: 300 }} className="rounded-lg border overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
