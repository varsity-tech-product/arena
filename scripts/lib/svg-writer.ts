// Converts layout result to SVG string — hand-drawn sketch style

import type { LayoutResult, LayoutNode, LayoutSubgraph, MermaidEdge } from "./types.js";

// Seeded PRNG for deterministic wobble
function prng(seed: number): number {
  const x = Math.sin(seed * 9301 + 49297) * 49297;
  return x - Math.floor(x);
}

function jitter(seed: number, range: number): number {
  return (prng(seed) - 0.5) * range;
}

function fillColor(node: LayoutNode): string {
  const label = node.label.toLowerCase();
  if (node.shape === "diamond") return "#ffec99";
  if (/\b(hold|close_position|open_long|open_short)\b/.test(label)) return "#b2f2bb";
  if (/\b(error|report error|fail)\b/.test(label)) return "#ffc9c9";
  return "#a5d8ff";
}

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Generate a wobbly path for a rectangle (hand-drawn effect)
function sketchRect(x: number, y: number, w: number, h: number, seed: number): string {
  const r = 6; // corner radius
  const wobble = 1.5;
  const j = (i: number) => jitter(seed + i, wobble);

  // Slightly wobbly rounded rectangle using path
  return `M ${x + r + j(1)},${y + j(2)}
    L ${x + w - r + j(3)},${y + j(4)}
    Q ${x + w + j(5)},${y + j(6)} ${x + w + j(7)},${y + r + j(8)}
    L ${x + w + j(9)},${y + h - r + j(10)}
    Q ${x + w + j(11)},${y + h + j(12)} ${x + w - r + j(13)},${y + h + j(14)}
    L ${x + r + j(15)},${y + h + j(16)}
    Q ${x + j(17)},${y + h + j(18)} ${x + j(19)},${y + h - r + j(20)}
    L ${x + j(21)},${y + r + j(22)}
    Q ${x + j(23)},${y + j(24)} ${x + r + j(25)},${y + j(26)}
    Z`;
}

// Generate wobbly diamond path
function sketchDiamond(cx: number, cy: number, hw: number, hh: number, seed: number): string {
  const wobble = 2;
  const j = (i: number) => jitter(seed + i, wobble);
  return `M ${cx + j(1)},${cy - hh + j(2)}
    L ${cx + hw + j(3)},${cy + j(4)}
    L ${cx + j(5)},${cy + hh + j(6)}
    L ${cx - hw + j(7)},${cy + j(8)}
    Z`;
}

// Hachure fill pattern for a bounding box
function hachureFill(x: number, y: number, w: number, h: number, color: string, seed: number): string {
  const gap = 8;
  const lines: string[] = [];
  const angle = -0.4; // slight tilt
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);

  for (let offset = -h; offset < w + h; offset += gap) {
    const x1 = x + offset;
    const y1 = y;
    const x2 = x + offset - h * (sin / cos);
    const y2 = y + h;

    // Clip to bounding box
    const clipX1 = Math.max(x, Math.min(x + w, x1));
    const clipX2 = Math.max(x, Math.min(x + w, x2));
    const t1 = w > 0 ? (clipX1 - x1) / (x2 - x1 || 1) : 0;
    const t2 = w > 0 ? (clipX2 - x1) / (x2 - x1 || 1) : 1;

    const startX = x1 + t1 * (x2 - x1) + jitter(seed + offset, 1);
    const startY = y1 + t1 * (y2 - y1) + jitter(seed + offset + 1, 1);
    const endX = x1 + t2 * (x2 - x1) + jitter(seed + offset + 2, 1);
    const endY = y1 + t2 * (y2 - y1) + jitter(seed + offset + 3, 1);

    if (Math.abs(endX - startX) > 2 || Math.abs(endY - startY) > 2) {
      lines.push(`<line x1="${startX}" y1="${startY}" x2="${endX}" y2="${endY}" stroke="${color}" stroke-width="0.8" opacity="0.35" />`);
    }
  }
  return lines.join("\n");
}

const FONT = `'Virgil', 'Segoe Print', 'Comic Sans MS', 'Patrick Hand', cursive`;

function renderNode(node: LayoutNode, idx: number): string {
  const cx = node.x + node.width / 2;
  const cy = node.y + node.height / 2;
  const fill = fillColor(node);
  const lines = node.label.split("\n");
  const fontSize = 14;
  const lineHeight = fontSize * 1.4;
  const shapeSeed = idx * 100;

  let shape: string;
  let hachure: string;

  if (node.shape === "diamond") {
    const hw = node.width / 2;
    const hh = node.height / 2;
    const path = sketchDiamond(cx, cy, hw, hh, shapeSeed);
    shape = `<path d="${path}" fill="${fill}" stroke="#000000" stroke-width="1.5" />`;
    hachure = hachureFill(node.x, node.y, node.width, node.height, "#000000", shapeSeed + 50);
  } else {
    const path = sketchRect(node.x, node.y, node.width, node.height, shapeSeed);
    shape = `<path d="${path}" fill="${fill}" stroke="#000000" stroke-width="1.5" />`;
    hachure = hachureFill(node.x, node.y, node.width, node.height, "#000000", shapeSeed + 50);
  }

  const textStartY = cy - ((lines.length - 1) * lineHeight) / 2;
  const textEls = lines
    .map((line, i) => `<tspan x="${cx}" dy="${i === 0 ? 0 : lineHeight}">${escapeXml(line)}</tspan>`)
    .join("");

  const text = `<text x="${cx}" y="${textStartY}" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-size="${fontSize}" fill="#000000">${textEls}</text>`;

  return `<g>${shape}\n${hachure}\n${text}</g>`;
}

function renderSubgraph(sg: LayoutSubgraph): string {
  const path = sketchRect(sg.x, sg.y, sg.width, sg.height, 9999);
  const rect = `<path d="${path}" fill="#f8f9fa" stroke="#868e96" stroke-width="1" stroke-dasharray="8,5" />`;
  const label = `<text x="${sg.x + 12}" y="${sg.y + 20}" font-family="${FONT}" font-size="13" fill="#868e96" font-weight="600">${escapeXml(sg.label)}</text>`;
  return rect + "\n" + label;
}

function edgePoint(node: LayoutNode, targetCx: number, targetCy: number): { x: number; y: number } {
  const cx = node.x + node.width / 2;
  const cy = node.y + node.height / 2;
  const dx = targetCx - cx;
  const dy = targetCy - cy;

  if (dx === 0 && dy === 0) return { x: cx, y: cy };

  if (node.shape === "diamond") {
    const hw = node.width / 2;
    const hh = node.height / 2;
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);
    const t = Math.min(hw / (absDx || 1), hh / (absDy || 1));
    return { x: cx + dx * t * 0.9, y: cy + dy * t * 0.9 };
  }

  const hw = node.width / 2;
  const hh = node.height / 2;
  const scaleX = Math.abs(dx) > 0 ? hw / Math.abs(dx) : Infinity;
  const scaleY = Math.abs(dy) > 0 ? hh / Math.abs(dy) : Infinity;
  const scale = Math.min(scaleX, scaleY);
  return { x: cx + dx * scale, y: cy + dy * scale };
}

function renderArrow(edge: MermaidEdge, from: LayoutNode, to: LayoutNode, idx: number): string {
  const fromCx = from.x + from.width / 2;
  const fromCy = from.y + from.height / 2;
  const toCx = to.x + to.width / 2;
  const toCy = to.y + to.height / 2;

  const start = edgePoint(from, toCx, toCy);
  const end = edgePoint(to, fromCx, fromCy);

  // Wobbly line using quadratic curve through a slightly offset midpoint
  const midX = (start.x + end.x) / 2 + jitter(idx * 13, 4);
  const midY = (start.y + end.y) / 2 + jitter(idx * 13 + 1, 4);
  const line = `<path d="M ${start.x},${start.y} Q ${midX},${midY} ${end.x},${end.y}" fill="none" stroke="#000000" stroke-width="1.5" marker-end="url(#arrowhead)" />`;

  let label = "";
  if (edge.label) {
    const labelMidX = (start.x + end.x) / 2;
    const labelMidY = (start.y + end.y) / 2;
    const pad = 4;
    const textWidth = edge.label.length * 7.5 + 14;
    const textHeight = 18;
    label = `<rect x="${labelMidX - textWidth / 2 - pad}" y="${labelMidY - textHeight / 2 - pad - 2}" width="${textWidth + pad * 2}" height="${textHeight + pad * 2}" rx="4" fill="white" stroke="none" />`;
    label += `\n<text x="${labelMidX}" y="${labelMidY - 1}" text-anchor="middle" dominant-baseline="central" font-family="${FONT}" font-size="12" fill="#495057" font-style="italic">${escapeXml(edge.label)}</text>`;
  }

  return line + "\n" + label;
}

export function toSvg(layout: LayoutResult): string {
  const pad = 40;

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const n of layout.nodes) {
    minX = Math.min(minX, n.x);
    minY = Math.min(minY, n.y);
    maxX = Math.max(maxX, n.x + n.width);
    maxY = Math.max(maxY, n.y + n.height);
  }
  for (const sg of layout.subgraphs) {
    minX = Math.min(minX, sg.x);
    minY = Math.min(minY, sg.y);
    maxX = Math.max(maxX, sg.x + sg.width);
    maxY = Math.max(maxY, sg.y + sg.height);
  }

  const width = maxX - minX + pad * 2;
  const height = maxY - minY + pad * 2;
  const offsetX = -minX + pad;
  const offsetY = -minY + pad;

  const parts: string[] = [];

  parts.push(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">`);
  parts.push(`<rect width="${width}" height="${height}" fill="#ffffff" />`);
  parts.push(`<defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#000000" /></marker></defs>`);
  parts.push(`<g transform="translate(${offsetX}, ${offsetY})">`);

  // Subgraphs (background)
  for (const sg of layout.subgraphs) {
    parts.push(renderSubgraph(sg));
  }

  // Arrows (behind nodes)
  const nodeMap = new Map(layout.nodes.map((n) => [n.id, n]));
  let arrowIdx = 0;
  for (const edge of layout.edges) {
    const from = nodeMap.get(edge.from);
    const to = nodeMap.get(edge.to);
    if (from && to) parts.push(renderArrow(edge, from, to, arrowIdx++));
  }

  // Nodes (on top)
  layout.nodes.forEach((node, idx) => {
    parts.push(renderNode(node, idx));
  });

  parts.push("</g>");
  parts.push("</svg>");

  return parts.join("\n");
}
