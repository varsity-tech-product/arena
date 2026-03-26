// Converts layout result to Excalidraw JSON — sketch style

import type { LayoutResult, LayoutNode, LayoutSubgraph, MermaidEdge } from "./types.js";

let _nextId = 1;
let _nextSeed = 100000;
function uid(prefix: string): string {
  return `${prefix}_${_nextId++}`;
}
function seed(): number {
  return _nextSeed++;
}

// Seeded PRNG for deterministic "imperfection"
function jitter(seed: number, range: number): number {
  const x = Math.sin(seed * 9301 + 49297) * 49297;
  return (x - Math.floor(x) - 0.5) * range;
}

// Color logic
function fillColor(node: LayoutNode): string {
  const label = node.label.toLowerCase();
  if (node.shape === "diamond") return "#ffec99"; // yellow
  if (/\b(hold|close_position|open_long|open_short)\b/.test(label)) return "#b2f2bb"; // green
  if (/\b(error|report error|fail)\b/.test(label)) return "#ffc9c9"; // red
  return "#a5d8ff"; // blue
}

interface ExcalidrawElement {
  [key: string]: unknown;
}

function baseProps(id: string, type: string, x: number, y: number, w: number, h: number): ExcalidrawElement {
  return {
    id,
    type,
    x,
    y,
    width: w,
    height: h,
    angle: 0,
    strokeColor: "#000000",
    backgroundColor: "transparent",
    fillStyle: "hachure",
    strokeWidth: 1.5,
    strokeStyle: "solid",
    roughness: 2,
    opacity: 100,
    groupIds: [],
    frameId: null,
    index: `a${_nextId}`,
    roundness: null,
    seed: seed(),
    version: 1,
    versionNonce: seed(),
    isDeleted: false,
    boundElements: null,
    updated: Date.now(),
    link: null,
    locked: false,
  };
}

function makeShape(node: LayoutNode, idx: number): { shape: ExcalidrawElement; text: ExcalidrawElement } {
  const shapeId = uid("shape");
  const textId = uid("text");
  const type = node.shape === "diamond" ? "diamond" : "rectangle";

  // Slight imperfection — nudge position by ±3px
  const nudgeX = jitter(idx * 7 + 1, 6);
  const nudgeY = jitter(idx * 7 + 2, 6);

  const shape: ExcalidrawElement = {
    ...baseProps(shapeId, type, node.x + nudgeX, node.y + nudgeY, node.width, node.height),
    backgroundColor: fillColor(node),
    roundness: type === "rectangle" ? { type: 3 } : { type: 2 },
    boundElements: [{ id: textId, type: "text" }],
  };

  const fontSize = 16;
  const lines = node.label.split("\n");
  const textHeight = lines.length * fontSize * 1.25;
  const textWidth = node.width - 20;

  const text: ExcalidrawElement = {
    ...baseProps(textId, "text",
      node.x + nudgeX + (node.width - textWidth) / 2,
      node.y + nudgeY + (node.height - textHeight) / 2,
      textWidth, textHeight),
    text: node.label,
    fontSize,
    fontFamily: 1, // Virgil (hand-drawn)
    textAlign: "center",
    verticalAlign: "middle",
    containerId: shapeId,
    originalText: node.label,
    autoResize: true,
    lineHeight: 1.25,
    roughness: 0, // text itself shouldn't be rough
  };

  return { shape, text };
}

function makeSubgraph(sg: LayoutSubgraph): { rect: ExcalidrawElement; label: ExcalidrawElement } {
  const rectId = uid("sg");
  const labelId = uid("sglabel");

  const rect: ExcalidrawElement = {
    ...baseProps(rectId, "rectangle", sg.x, sg.y, sg.width, sg.height),
    backgroundColor: "#f8f9fa",
    fillStyle: "solid",
    strokeStyle: "dashed",
    strokeWidth: 1,
    strokeColor: "#868e96",
    roughness: 2,
    roundness: { type: 3 },
    boundElements: [{ id: labelId, type: "text" }],
  };

  const fontSize = 14;
  const labelHeight = fontSize * 1.25;

  const label: ExcalidrawElement = {
    ...baseProps(labelId, "text", sg.x + 10, sg.y + 8, sg.width - 20, labelHeight),
    text: sg.label,
    fontSize,
    fontFamily: 1,
    textAlign: "left",
    verticalAlign: "top",
    containerId: rectId,
    originalText: sg.label,
    autoResize: true,
    lineHeight: 1.25,
    roughness: 0,
  };

  return { rect, label };
}

function makeArrow(
  edge: MermaidEdge,
  fromNode: LayoutNode,
  toNode: LayoutNode,
): { arrow: ExcalidrawElement; label?: ExcalidrawElement } {
  const arrowId = uid("arrow");

  const fromCx = fromNode.x + fromNode.width / 2;
  const fromCy = fromNode.y + fromNode.height / 2;
  const toCx = toNode.x + toNode.width / 2;
  const toCy = toNode.y + toNode.height / 2;

  const dx = toCx - fromCx;
  const dy = toCy - fromCy;

  const arrow: ExcalidrawElement = {
    ...baseProps(arrowId, "arrow", fromCx, fromCy, Math.abs(dx), Math.abs(dy)),
    backgroundColor: "transparent",
    fillStyle: "solid",
    roundness: { type: 2 },
    points: [[0, 0], [dx, dy]],
    lastCommittedPoint: null,
    startBinding: {
      elementId: "",
      focus: 0,
      gap: 8,
      fixedPoint: null,
    },
    endBinding: {
      elementId: "",
      focus: 0,
      gap: 8,
      fixedPoint: null,
    },
    startArrowhead: null,
    endArrowhead: "arrow",
    elbowed: false,
  };

  let labelEl: ExcalidrawElement | undefined;
  if (edge.label) {
    const labelId = uid("elabel");
    const fontSize = 14;
    const labelWidth = edge.label.length * 8 + 16;
    const labelHeight = fontSize * 1.25;
    const midX = fromCx + dx / 2 - labelWidth / 2;
    const midY = fromCy + dy / 2 - labelHeight / 2 - 12;

    labelEl = {
      ...baseProps(labelId, "text", midX, midY, labelWidth, labelHeight),
      text: edge.label,
      fontSize,
      fontFamily: 1,
      textAlign: "center",
      verticalAlign: "middle",
      containerId: arrowId,
      originalText: edge.label,
      autoResize: true,
      lineHeight: 1.25,
      roughness: 0,
    };

    (arrow.boundElements as unknown[]) = [{ id: labelId, type: "text" }];
  }

  return { arrow, label: labelEl };
}

export interface WriterOptions {
  title?: string;
}

export function toExcalidraw(layout: LayoutResult, _options?: WriterOptions): object {
  _nextId = 1;
  _nextSeed = 100000;

  const elements: ExcalidrawElement[] = [];
  const nodeToShapeId = new Map<string, string>();
  const nodeLayoutMap = new Map<string, LayoutNode>();

  for (const n of layout.nodes) {
    nodeLayoutMap.set(n.id, n);
  }

  // Subgraphs first (behind nodes)
  for (const sg of layout.subgraphs) {
    const { rect, label } = makeSubgraph(sg);
    elements.push(rect, label);
  }

  // Nodes
  layout.nodes.forEach((node, idx) => {
    const { shape, text } = makeShape(node, idx);
    nodeToShapeId.set(node.id, shape.id as string);
    elements.push(shape, text);
  });

  // Arrows
  const shapeArrows = new Map<string, { id: string; type: string }[]>();

  for (const edge of layout.edges) {
    const fromNode = nodeLayoutMap.get(edge.from);
    const toNode = nodeLayoutMap.get(edge.to);
    if (!fromNode || !toNode) continue;

    const { arrow, label } = makeArrow(edge, fromNode, toNode);

    const fromShapeId = nodeToShapeId.get(edge.from)!;
    const toShapeId = nodeToShapeId.get(edge.to)!;
    (arrow.startBinding as { elementId: string }).elementId = fromShapeId;
    (arrow.endBinding as { elementId: string }).elementId = toShapeId;

    if (!shapeArrows.has(fromShapeId)) shapeArrows.set(fromShapeId, []);
    if (!shapeArrows.has(toShapeId)) shapeArrows.set(toShapeId, []);
    shapeArrows.get(fromShapeId)!.push({ id: arrow.id as string, type: "arrow" });
    shapeArrows.get(toShapeId)!.push({ id: arrow.id as string, type: "arrow" });

    elements.push(arrow);
    if (label) elements.push(label);
  }

  // Patch shape boundElements to include arrows
  for (const el of elements) {
    if (el.type === "rectangle" || el.type === "diamond") {
      const arrows = shapeArrows.get(el.id as string) || [];
      const existing = (el.boundElements as { id: string; type: string }[]) || [];
      el.boundElements = [...existing, ...arrows];
    }
  }

  return {
    type: "excalidraw",
    version: 2,
    source: "arena-diagram-generator",
    elements,
    appState: {
      gridSize: null,
      viewBackgroundColor: "#ffffff",
    },
    files: {},
  };
}
