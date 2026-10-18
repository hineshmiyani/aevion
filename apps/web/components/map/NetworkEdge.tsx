import { BaseEdge, getStraightPath, type EdgeProps } from "@xyflow/react";
import type { CSSProperties } from "react";

const ARROW = 8;

/** Connect to each glyph boundary, including the small background nodes. The arrowhead is drawn
 * here rather than as an SVG marker, so it can wait for the line to finish drawing itself. */
export function NetworkEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY } = props;
  const length = Math.max(Math.hypot(targetX - sourceX, targetY - sourceY), 1);
  const dx = (targetX - sourceX) / length;
  const dy = (targetY - sourceY) / length;
  const sourceRadius = Number(props.data?.sourceRadius ?? 6);
  const targetRadius = Number(props.data?.targetRadius ?? 6);
  const delay = props.data?.delay as number | undefined;
  const tipX = targetX - dx * targetRadius;
  const tipY = targetY - dy * targetRadius;
  // The line stops inside the arrowhead, so its stroke never pokes past the tip.
  const [path, labelX, labelY] = getStraightPath({ sourceX: sourceX + dx * sourceRadius, sourceY: sourceY + dy * sourceRadius, targetX: tipX - dx * (ARROW - 2), targetY: tipY - dy * (ARROW - 2) });
  const baseX = tipX - dx * ARROW;
  const baseY = tipY - dy * ARROW;
  const arrow = `M ${tipX},${tipY} L ${baseX - dy * 3.6},${baseY + dx * 3.6} L ${baseX + dy * 3.6},${baseY - dx * 3.6} Z`;
  const stroke = props.style?.stroke;
  // A fixed path length lets the route draw itself at any length with one dash.
  return <>
    <BaseEdge id={props.id} path={path} pathLength={1000} style={{ ...props.style, animationDelay: delay === undefined ? undefined : `${delay}ms` }} label={props.label} labelX={labelX} labelY={labelY} labelStyle={props.labelStyle} labelBgStyle={props.labelBgStyle} labelBgPadding={props.labelBgPadding} labelBgBorderRadius={6} />
    <path className="network-arrow" d={arrow} style={{ fill: stroke, animationDelay: delay === undefined ? undefined : `calc(${delay}ms + var(--dur-route) * .8)` } as CSSProperties} />
  </>;
}
